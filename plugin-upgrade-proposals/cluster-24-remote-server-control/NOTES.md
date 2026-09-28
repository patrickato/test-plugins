# Notes: remote/server control cluster

**Status: `fancyserver.py` REMOVED (2 real bugs). `cmd_server.py`,
`console.py`, `webcfg_ng.py` KEPT (findings-only, fixes documented).**

Sources: `fancyserver.py` and `webcfg_ng.py` from
`itsdarklikehell/pwnagotchi-plugins`; `cmd_server.py` and `console.py`
from `sniffleupagus/pwnagotchi_plugins`.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced. None of these four plugins are
rewrites of anything already on the list - each was reviewed
independently.

## 1. What each one is and does

1. **`fancyserver.py`** - a TCP listener on `localhost:3699` that accepts
   commands (shutdown, restart, reboot, plugin enable/disable) to
   remotely control the pwnagotchi.
2. **`cmd_server.py`** - a Unix-domain-socket command shell
   (`/tmp/pwny_cmd_socket`) with commands for reloading custom plugins,
   enabling/disabling plugins, and a UI "countdown" demo.
3. **`console.py`** - an on-screen scrolling log of recent status/event
   text, hooking into most framework events (handshakes, peers, AP
   sightings, epochs) to build a running feed.
4. **`webcfg_ng.py`** - a full web-based runtime config editor exposed
   through the web UI's webhook system - can view, save, or merge-save
   changes to `/etc/pwnagotchi/config.toml` and trigger a restart.

## 2. `fancyserver.py` - removed, two real bugs

**Bug 1 - `NameError` on the outer error-handling path:**
```python
except Exception as e:
    logging.warn(f"An unexpected error occurred: {e}")
    logging.warn(traceback.format_exc())   # BUG: `traceback` never imported
```
`traceback` is never imported anywhere in the file. If this outer
`except` block ever triggers, this second line raises its own
`NameError`, masking whatever the original exception actually was -
exactly the moment good diagnostics matter most.

**Bug 2 - `UnboundLocalError` risk:**
```python
msg = command[0]
if len(command) > 1:
    name = command[1]
    state = command[2]
...
elif msg == "plugin":
    logging.warn("plugin command " + name + " " + state)   # BUG: name/state may be undefined
```
`name`/`state` are only assigned inside the `if len(command) > 1:`
branch, but referenced unconditionally when `msg == "plugin"`. A
single-element `"plugin"` command (or any command with `len(command) <= 1`)
crashes here.

**Design note, not a bug:** the blocking `while self.running:` loop
directly inside `on_loaded` looks alarming at first (nothing else in
this file spawns a background thread for it), but this fork's own
plugin-loader source confirms this is the intended, supported pattern -
`on_loaded` is dispatched on its own dedicated thread specifically
because, per the framework's own code comment, "many plugins use
on_load as a main loop." Not a defect.

**Also worth knowing, not a bug per se:** listens unauthenticated on
`localhost:3699` - any local process can send shutdown/reboot/restart/
plugin-toggle commands. Limited to local access, but no auth token or
allowlist of any kind.

**Fix, documented for reference even though removed:**
```python
import traceback   # add this import

# and initialize before the branch:
name = None
state = None
if len(command) > 1:
    name = command[1]
    state = command[2]
```

**Removed rather than fixed** per the user's decision this round - both
bugs are real and would need fixing before this plugin could be trusted.

## 3. `cmd_server.py` - kept, two real bugs

**Bug 1 - `NameError` on a narrow cleanup-failure path:**
```python
try:
    os.unlink(socket_path)
except OSError:
    if os.path.exists(socket_path):
        logging.exception(e)   # BUG: `e` never bound - no `as e` on the except clause
        raise
```
Only fires if `os.unlink` fails with a *genuine* error (permissions,
etc.) - the common "socket file doesn't exist yet" case is handled
correctly (falls through silently, since `os.path.exists` would then be
`False`). But a real unlink failure crashes with a confusing
`NameError` instead of the intended, more useful exception.

**Fix:**
```python
except OSError as e:
    if os.path.exists(socket_path):
        logging.exception(e)
        raise
```

**Bug 2 - reply-misdirection with multiple simultaneous clients:**
```python
client_socket, address = server_socket.accept()   # sets client_socket, only on NEW connections
...
else:
    data = s.recv(1024)   # processing an EXISTING client's data
    ...
    client_socket.send(b'> ')   # BUG: sends to whichever client connected LAST, not necessarily `s`
```
`client_socket` is a single variable, only reassigned in the
accept-a-new-connection branch. When processing data from an
already-connected client `s` (the `else` branch), the trailing
`client_socket.send(b'> ')` at the end of command handling still refers
to whichever socket was accepted most recently - which, with more than
one client connected at once, is not necessarily `s`. A reply can be
sent to the wrong client.

**Fix:** reply via `s.send(...)` instead of `client_socket.send(...)`
inside the data-handling branch, since `s` is always the actual socket
that sent the command being processed.

**Also worth knowing:** same unauthenticated-local-socket design as
`fancyserver.py` - `/tmp/pwny_cmd_socket` accepts commands from any
local process with no auth check, including plugin enable/disable and a
UI-blocking "countdown" demo.

**Kept, findings-only** - neither bug is fatal (both are edge cases:
genuine unlink failure, or multiple concurrent clients), and the plugin
is otherwise a well-structured, genuinely useful command shell.

## 4. `console.py` - kept, one cosmetic bug, otherwise clean

```python
def on_loaded(self):
    logging.warning("Console options = " % self.options)   # cosmetic bug
    self.options['showLines'] = self.options.get('showLines', 15)
```
Verified directly: `"literal string with no %-specifiers" % some_dict`
does **not** raise in Python - it silently returns the literal string
unchanged, discarding the right-hand operand entirely. So this doesn't
crash, it just always logs `"Console options = "` with nothing appended
- the intended diagnostic content (the actual options dict) is lost.

**Fix:**
```python
logging.warning("Console options = %s" % self.options)
```

Otherwise a well-built plugin: every option read (`showLines`,
`position`, `color`, `font_size`) uses `.get()` with a sensible
fallback, correctly relies on `on_loaded` running before `on_ui_update`
(a safe assumption per this fork's event ordering), and its `on_ai_*`
hooks are inert-but-harmless dead code from the removed AI layer - same
pattern documented elsewhere in this project, not a defect specific to
this file.

## 5. `webcfg_ng.py` - kept, no bugs found, one design point flagged

Verified `save_config(config, target)` and `merge_config(user, default)`
calls directly against `pwnagotchi/utils.py`'s real signatures - both
match correctly, no "calls a function that doesn't exist" or
wrong-argument-order issue here.

**Design point, not confirmed as a bug:** the `save-config` webhook path
writes the POSTed JSON as the *entire* config file with no merge:
```python
elif path == "save-config":
    save_config(request.get_json(), "/etc/pwnagotchi/config.toml")
```
while `merge-save-config` correctly merges onto the existing config
first:
```python
elif path == "merge-save-config":
    self.config = merge_config(request.get_json(), self.config)
    ...
    save_config(request.get_json(), "/etc/pwnagotchi/config.toml")
```
If the browser-side JS behind the `save-config` endpoint always sends a
complete config snapshot, this is fine by design. If it can ever send a
partial config, this path would silently drop any settings not included
in that request. Not confirmed either way without the front-end
JavaScript (out of scope for this review) - flagged for awareness, not
asserted as a bug.

## 6. Dependencies (kept plugins)

`cmd_server.py`: no special dependencies beyond the standard library;
optional `prctl` (best-effort, wrapped in try/except if missing).
`console.py`: `PIL`/`Pillow` (for `ImageFont`, already a pwnagotchi core
dependency for its own display rendering). `webcfg_ng.py`: `toml` (pip,
imported but not directly used in the shown logic - the framework's own
`pwnagotchi.utils` handles the actual TOML serialization via
`tomlkit`), Flask (already a core pwnagotchi dependency for the web UI).
