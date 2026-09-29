# Cluster 38 - Web UI / API / Remote control

Status: **IN PROGRESS** - 4 removed, 1 fixed/upgraded and moved to
`plugins-wip`, `handshaker.py` approved to be fixed/rebuilt next,
being worked through the remaining 3 in groups of 5 per the user's
request (group 1 now down to 2: `Pwny-Tailscale`, `httpserver.py`;
group 2 resolved - `pwnmenu.py`/`pwnmenucmd.py` removed, `handshaker.py`
approved for rebuild).

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, "## Web UI / API /
Remote control" section, Group 60 in the elimination log.

## Excluded from this cluster (already handled elsewhere)

- `cmd_server.py` / `webcfg_ng.py` - see Cluster 24
- `wpa-sec-list.py` / `wpa-sec_ng.py` - see Cluster 26

## Record-only, no action needed (not found anywhere in this environment)

- `pwmenu` - mobile-first field console for captures/cracking/exports/whitelists
- `pwnagotchi-http-module` - serves handshake pcaps via HTTP (targets the Bookworm image)
- `Pwny-WG` - WireGuard VPN + handshake sync over SSH; only a `README.md`
  exists in this environment (`wpa-2/pwnagotchi-plugins/Pwny-WG/`), no
  actual plugin script anywhere

## Removed at the user's request (4)

- **pwnwatch.py** - meant to receive commands from a companion
  "pwnagotchi-watch" app and report session stats. `on_webhook`
  references `self.ready`, which is never set anywhere in the class -
  a guaranteed `AttributeError` on the very first webhook call. Its one
  real response path (`Response(str(self.handshakes), ...)`) is built
  but the return value is discarded (no `return` statement) - execution
  falls through to `abort(404)` regardless, so even before the crash
  bug the plugin never actually served anything. `parseSessionStats`
  depends on an unrelated, unreviewed "session-stats" plugin's
  `save_directory` config key being present - an undeclared hard
  dependency. Despite the plugin's stated purpose ("receive commands
  from pwnagotchi-watch"), there is no command-parsing or dispatch
  logic anywhere in the file at all - only session-stats file reading.
- **pwnmothership.py** - pushes a JSON status snapshot (peers,
  handshake counts, uptime, etc.) to a remote host on every screen
  update. Unguarded `for peer in peers_response:` crashes with
  `TypeError` on every UI update whenever the local mesh-peers API
  call fails (`peers_response` stays `None` on failure); blocks the UI
  thread up to 30s per POST attempt (no background thread); disables
  TLS cert verification (`verify=False`) on the outbound POST. Near-
  identical code lineage to state-api.py (presented as a merge
  candidate) - the user chose to drop both rather than fix or merge.
- **state-api.py** - on-demand JSON status endpoint + optional HTML
  dashboard page for external tools/dashboards. Same unguarded
  `for peer in peers_response:` `TypeError` crash as pwnmothership.py;
  dashboard page needs template files manually copied into the
  installed `pwnagotchi` package directory on a hardcoded Python-3.7-
  specific path. Dropped alongside pwnmothership.py rather than
  fixed/merged.
- **pwnmenu.py** / **pwnmenucmd.py** - popup on-screen menu system
  triggered by physical buttons, plus a companion CLI trigger script.
  `on_loaded()` contains a `while self.running:` loop that blocks
  forever on a socket `.accept()` call - hangs the whole device at
  startup (same device-hanging bug class as httpserver.py and the
  original web2ssh.py before its fix). Also reads a hardcoded file
  (`/home/pi/scripts/pwnmenu.txt`) at **module import time** with no
  guard - a missing file crashes the whole plugin load before anything
  even runs. Only functions on `displayhatmini` hardware, not the
  user's actual MPI3501 touchscreen, so even fixed it would be a
  silent no-op on this device (Touch_UI/TouchUING from Cluster 34
  already covers on-screen menu interaction for the real hardware).
  Companion `pwnmenucmd.py` calls `logging.info(...)` without ever
  importing `logging`, crashing immediately on use. Dropped at the
  user's request rather than fixed.

## Fixed and moved to `plugins-wip` (1 plugin)

### web2ssh.py -> Web2SSHNG (`web2ssh-suite`, file `web2ssh_ng.py`)

The top security priority found in this whole audit. Runs a small web
server that executes shell commands as root when submitted through a
browser (one-click shutdown/reboot/pwnkill buttons plus an optional
free-text command box), behind HTTP Basic Auth.

**Bugs fixed:**

- `self.app.run(host='::', port=self.options["port"])` was called
  directly inside `on_loaded()` - `Flask.run()` is a blocking,
  `serve_forever()`-style call, so `on_loaded()` would never return,
  hanging the entire pwnagotchi plugin-loading process at startup the
  moment this plugin was enabled. Fixed: the Flask app now runs via
  `werkzeug.serving.make_server(...)` in a background daemon thread;
  `on_loaded()` starts the thread and returns immediately, and
  `on_unload(self, ui)` calls the server's `.shutdown()` to stop it
  cleanly.
- `self.config` was always `{}`: the constructor accepted an optional
  `config` argument that the real framework's loader never actually
  passes (it constructs every plugin with `cls()`, zero arguments), and
  even if it had been populated, the code read it with flat dotted-
  string keys (`"main.plugins.web2ssh.username"`) rather than the real
  nested config shape. Net effect: **the username/password/port a user
  set in `config.toml` were silently ignored - the plugin always ran
  with the hardcoded fallback `"changeme"`/`"changeme"`/`8082`,
  regardless of configuration.** Combined with `host='::'` (every
  interface) and root shell command execution by design, this amounted
  to an effectively unauthenticated root-shell backend reachable from
  the network. Fixed: config is now read through the real
  `self.options` the framework actually populates, via this repo's
  standard `DEFAULTS` + `_opt()` pattern, and (see "what's new" below)
  there is no code path that lets the server start with a default or
  guessable credential pair at all.
- Basic Auth credentials were compared with a straightforward
  equality check. Fixed: compared with `hmac.compare_digest` (constant
  time), removing a timing side-channel.
- Commands ran via untimed `subprocess.check_output` - a hung command
  would hang the request (and, since the original also blocked the
  whole server on one thread, potentially the entire plugin) forever.
  Fixed: `subprocess.run(..., timeout=<configurable, default 30s>)`,
  reporting a clear timeout message instead of hanging.

**All 3 approved upgrades built:**

1. **Mandatory real credentials, no default fallback of any kind.**
   `on_loaded()` validates the configured `username`/`password` via
   `validate_credentials()` and refuses to start the server at all
   (logs a clear error, no socket is ever bound) if either is missing,
   blank, or matches a curated `PLACEHOLDER_CREDENTIALS` set
   (`"changeme"`, `"admin"`, `"password"`, `"root"`, `"12345"`, and
   about 20 other common defaults, checked case-insensitively and
   trimmed). There is no code path anywhere in the file that assigns
   or compares against a working default credential value - confirmed
   by grep (see this session's build verification).
2. **An easy-to-use `bind_scope` option**, so restricting network
   exposure doesn't mean the user has to go hunting for interface
   names or IP addresses themselves:
   - `"auto"` (default) - detects a live Tailscale interface
     (`tailscale ip -4`, falling back to parsing `ip -4 addr show
     tailscale0`) and binds to that specific IP if found, logging and
     displaying the exact URL to visit; falls back to `127.0.0.1`
     only if Tailscale isn't detected, with a friendly explanation of
     the alternatives.
   - `"tailscale"` - requires a detected Tailscale interface; refuses
     to start (fail-safe) rather than silently falling back to
     something broader if none is found.
   - `"localhost"` - always `127.0.0.1` only.
   - `"lan"` - binds every interface (`0.0.0.0`), an explicit,
     deliberate opt-in that logs a loud, impossible-to-miss warning
     every time it starts this way.
   - Whichever scope is used, the reachable URL is always logged AND
     shown as a banner at the top of the rendered index page itself.
3. **A `command_mode` option defaulting to an allowlist.**
   `"shortcuts"` (default) only ever executes a command that exactly
   matches one of a configurable `[main.plugins.web2ssh_ng.shortcuts]`
   label->command table (pre-populated with the original's own 10
   shortcuts) - anything else is rejected without ever invoking a
   shell, and the rendered page shows only the shortcut buttons, no
   free-text box at all. `"free"` restores the original's free-text
   command box alongside the shortcuts, with a mandatory, clearly
   visible warning banner shown whenever it's active.

**Also added:** output-length truncation (configurable cap, default
20000 characters, with a visible "truncated" note) so a runaway
command can't produce an unusably huge page; both rendered pages still
use Jinja2's auto-escaping `render_template_string` throughout, so no
raw command output or user input is ever interpolated unescaped.

**Explicitly not built this round** (presented as options, not
approved): CSRF token protection on the command form, a persistent
command audit log file, and brute-force login lockout/rate-limiting.
Noted in the suite's own NOTES.md as available ideas for later.

**Testing:** all tests run against the real, installed Flask/Werkzeug
(not mocked) - actual HTTP round-trips against a real `make_server`
instance, including a real 401/401/200 Basic Auth sequence, real
shortcut execution and rejection, a real timeout via an actual `sleep`
command, and confirming `on_unload` genuinely closes the port. All
passing. **Not tested on real hardware** - Tailscale detection and
real multi-interface LAN behavior still need verification on the
actual device.

**Original preserved:** an exact copy of `web2ssh.py` is kept in
[`originals/`](originals/). No real upstream `config.toml`/
`config.yaml` was ever found for it, so there is no
`web2ssh.config.original.toml`.

**Naming note:** file `web2ssh_ng.py` (snake_case), config section
`[main.plugins.web2ssh_ng]` - matching the file's exact basename, per
the same verified framework fact used throughout this project. NOT
the class name (`Web2SSHNG`) and NOT the original's section name
(`web2ssh`).

## Approved to be fixed and rebuilt (1 plugin, in progress)

- **handshaker.py** -> planned `handshaker-suite` (rebuild not yet
  built as of this note). `on_loaded()` calls `self.load_data(...)`, a
  method that is never defined anywhere in the class - guaranteed
  `AttributeError` on every load; its webhook (the plugin's entire
  "access info without SSH" purpose) is a no-op that only logs and
  returns nothing; declares an unused `scapy` dependency. User
  approved fixing and rebuilding it, with a request for suggestions on
  making it as good as it can be. See suite's own NOTES.md once built
  for the final feature list.

## Still pending decisions - working through in groups of 5

Full findings for all 7 remaining plugins were presented to the user
in this session's findings table. Group 2 is now resolved
(`pwnmenu.py`/`pwnmenucmd.py` removed, `handshaker.py` approved for
rebuild). Only Group 1 remains, deferred at the user's request:

**Group 1 (2, deferred):** `Pwny-Tailscale` (`tailscale.py`),
`httpserver.py`.

Key findings, summarized (see this session's findings table for full
detail):

- **Pwny-Tailscale** (`tailscale.py`) - the best-engineered plugin in
  this batch (retry logic, config validation, a real webhook status
  page) but `self.last_sync_time` is only set if `on_loaded()`
  completes successfully; if it returns early (missing required
  option, missing `tailscale`/`rsync` binary), the webhook status page
  crashes with `AttributeError` - exactly when a misconfigured user
  would go looking for what's wrong. Connection retries also block the
  main loop for up to ~45-60s on failure.
- **httpserver.py** - `self.httpd.serve_forever()` called directly in
  `on_loaded()` - blocks forever, hangs the whole device at startup;
  its request-handler subclass also has a broken `__init__` signature
  that would crash on every request even if the hang were fixed; no
  auth, serves the handshakes folder to the whole network.

## Related

Not yet identified: whether any merges beyond
pwnmothership.py/state-api.py make sense across this cluster - the
deferred post-all-clusters review task will also revisit this.
