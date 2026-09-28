# Notes: auto-hotspot/connect plugin cluster

**Status: all 5 KEPT (`auto-hotspot.py`, `away_base.py`, `home_base.py`,
`ext_wifi.py`, `extWifi.py`). Findings-only, no bullets changed.**

Sources: `auto-hotspot.py`, `away_base.py`, `home_base.py`, `ext_wifi.py`
from `itsdarklikehell/pwnagotchi-plugins`; `extWifi.py` (A1buS variant)
from `pwnagotchi-unofficial/plugins_archive/Levi-Michael/pwnagotchi-plugins`.

This cluster turned up several of the most severe bugs found anywhere in
this project - two files that cannot function at all as shipped
(`auto-hotspot.py`'s dead import, `away_base.py`/`home_base.py`'s
`_log()` `NameError`) and one active hazard (`extWifi.py`'s unconditional
reboot loop). All 5 are nonetheless assessed as fixable with mechanical,
non-redesign patches - see Section 6 for the fixability breakdown.

## 1. What each one is and does

1. **`auto-hotspot.py`** - monitors WiFi signal strength (RSSI) and
   automatically switches the Pi into hotspot mode when signal to a
   known network drops too low, switching back to normal
   monitor-mode/AI operation when signal recovers.
2. **`away_base.py`** - watches for a configured list of known networks
   and automatically connects when one becomes available, restarting
   monitor mode afterward.
3. **`home_base.py`** - the same connect-when-available logic as
   `away_base.py`, narrowed to target the user's home network
   specifically.
4. **`ext_wifi.py`** (itsdarklikehell) - renames which network interface
   bettercap looks for via a `sed` edit to bettercap's own config, so an
   external USB WiFi adapter is used instead of the onboard chip. The
   onboard chip itself stays active/untouched.
5. **`extWifi.py`** (A1buS) - a different approach to the same goal:
   actually disables the Pi's onboard WiFi chip via `/boot/config.txt`
   (`dtoverlay=disable-wifi`), freeing it entirely for an external
   adapter to take over.

Despite the similar names and the master list's shared one-line
description, `ext_wifi.py` and `extWifi.py` are functionally unrelated
implementations, not variants of the same code.

## 2. `auto-hotspot.py` - two independent, serious bugs

**Bug 1 - fatal, cannot import.** The file opens with:

```python
from pwnagotchi.ai.reward import RewardFunction
```

Confirmed via directory listing that no `pwnagotchi/ai/` module exists
anywhere in this jayofelony fork's source tree - the AI/RL layer was
fully removed. This raises `ModuleNotFoundError` the moment the plugin
loader tries to import the file, so the plugin never loads at all on
this fork, same failure category as `bluetooth_scanner.py` (Cluster 18)
though for a different underlying reason (dead framework module here,
vs. an imagined API there).

**Fix:** delete the import line and the `RewardFunction` usage entirely
- it's dead weight tied to the removed AI layer, not load-bearing for
this plugin's actual hotspot-switching logic.

**Bug 2 - infinite-loop hazard in `on_ui_update`.** Four blocks each use
`while` where an `if` was clearly intended:

```python
while STATUS == "rssi_low":
    ...
while STATUS == "internet_down":
    ...
while STATUS == "hotspot_up":
    ...
while STATUS == "connecting":
    ...
```

Nothing inside any of these loop bodies changes `STATUS`, so once
entered, each would spin forever - permanently hanging the UI-update
thread the next time `on_ui_update` fires while that status is active.
Masked today only because Bug 1 stops the plugin from loading in the
first place; would become live and reachable through ordinary operation
the moment Bug 1 is fixed.

**Fix:** change all four `while` to `if`.

**Additional issues, not yet fully catalogued (lower priority given Bugs
1-2 above already block operation):** bettercap credentials appear
hardcoded rather than sourced from config, and there's a `Popen(...).read()`
call pattern that isn't how subprocess output is normally captured in
this codebase (`communicate()` or `check_output()` would be the safer
equivalent) - flagged for whenever this plugin is actually fixed and
enabled, not fully bug-hunted line-by-line since Bugs 1-2 already make
the plugin non-functional regardless.

## 3. `away_base.py` / `home_base.py` - shared fatal bug, plus a second bug

**Bug 1 - fatal, `NameError` on nearly every call.** Both files define a
module-level helper:

```python
def _log(message):
    logging.info(f"[{self.__class__.__name__}] {message}")
```

`self` is referenced but never a parameter of this function - it's
defined at module scope, not inside a class or method, so there is no
`self` in scope at all. Every call to `_log(...)` raises `NameError:
name 'self' is not defined`, starting with `on_loaded()`'s very first
line in both files - this blocks nearly all of each plugin's real
functionality, not just logging.

**Fix:** either give `_log` a `self` parameter and call it as
`self._log(...)` from within the class's methods (turning it into a
proper instance method), or keep it module-level but pass an explicit
identifier instead of reaching for `self`:

```python
# Option A - make it a real instance method
def _log(self, message):
    logging.info(f"[{self.__class__.__name__}] {message}")
# ...call sites become self._log("...")

# Option B - keep it module-level, pass a name explicitly
def _log(message, source="AwayBase"):
    logging.info(f"[{source}] {message}")
```

**Bug 2 - independent `TypeError`, in `_restart_monitor_mode`.** Both
files end that method with:

```python
agent.next_epoch(self)
```

Confirmed via reading `pwnagotchi/automata.py` directly that the real
method signature is `def next_epoch(self):` - it takes no extra
arguments beyond the implicit `self` from being called as
`agent.next_epoch()`. Passing an extra positional argument raises
`TypeError: next_epoch() takes 1 positional argument but 2 were given`.
Independent of Bug 1 - fixing the `_log` crash would not fix this one,
and vice versa.

**Fix:** `agent.next_epoch(self)` -> `agent.next_epoch()`.

**Confirmed valid usage, not a bug:** both files also call
`agent.run(...)` elsewhere (e.g. to issue bettercap commands) - checked
directly against `pwnagotchi/bettercap.py`'s `def run(self, command,
verbose_errors=True):` and confirmed this call shape is correct on this
fork, unlike the `next_epoch` call above.

## 4. `ext_wifi.py` (itsdarklikehell) - milder, one real gap

**Gap - no interface validation, no restart after edit.** The plugin's
`sed`-based rename of bettercap's target interface runs without first
checking that the configured `interface` option is actually a
non-empty/valid value, and after making the edit it does not trigger
any service restart or reload - bettercap and the wifi stack keep using
the old interface name until the next manual reboot, silently. Not a
crash, but the plugin's effect doesn't actually take hold until the user
happens to reboot for an unrelated reason.

**Fix:** add a basic check that `self.options["interface"]` is set and
non-empty before running the `sed` edit, and call a restart/reload (or
prompt one) immediately after the edit succeeds so the change takes
effect without requiring a coincidental reboot.

## 5. `extWifi.py` (A1buS) - single worst bug found in the project to date

**Bug - unconditional reboot loop.** `on_loaded()` has two branches -
one for "the disable-wifi config line already exists," one for "the
line was just added" - and both fall through to the same unconditional
call at the end of the method:

```python
def on_loaded(self):
    ...
    if self.lineExist:
        logging.info("...")
    else:
        # add the line to /boot/config.txt
        ...
    self.restart_pi()   # BUG: runs unconditionally, regardless of branch
```

Since `on_loaded()` fires every time the plugin loads - which is every
boot, once enabled - and both branches reach the same unconditional
`restart_pi()` call, the device would reboot every single time it boots
and reaches this plugin's `on_loaded()`. Once enabled, the device would
never stay booted - assessed as the single worst bug found across the
entire project, worse than a plugin that merely fails to load, because
it actively prevents normal operation of the whole device rather than
just not working itself.

**Fix:** move the reboot call inside the "line was just added" branch
only - a reboot is only actually needed the first time the config
change is made, to apply the `dtoverlay` change; on every subsequent
boot the line already exists and no reboot is needed:

```python
def on_loaded(self):
    ...
    if self.lineExist:
        logging.info("...")
    else:
        # add the line to /boot/config.txt
        ...
        self.restart_pi()   # FIX: only reboot when the line was just added
```

One-line structural fix (moving one call inside one branch), not a
redesign.

## 6. Fixability assessment

All 5 files are fixable with mechanical patches - none require a full
rewrite or an unsupported/nonexistent API the way `bluetooth_scanner.py`
(Cluster 18) or `pwnassistant.py` (Cluster 13) did:

- **`away_base.py`** - two one-line-per-callsite fixes (`_log` signature,
  `next_epoch` extra arg). Least effort of the two fatal-bug files.
- **`home_base.py`** - identical two fixes, identical effort.
- **`extWifi.py`** - one-line structural fix (move `restart_pi()` inside
  the correct branch).
- **`ext_wifi.py`** - two small additions (a validation check, a
  restart/reload call). No existing logic needs to change, only
  augmenting.
- **`auto-hotspot.py`** - the most work of the five: delete a dead
  import, change four `while` to `if`, and (lower priority, not fully
  catalogued) address the hardcoded-credentials and `Popen().read()`
  concerns. Still all patches on top of the existing structure, not a
  redesign - the hotspot-switching logic itself doesn't need
  reimagining, just cleanup of dead AI-layer coupling and the loop typo.

None applied - documented for whenever any of these five plugins is
actually prioritized for use, consistent with the project's broad-scope,
keep-and-document-for-later philosophy.

## 7. Dependencies (all kept plugins)

`auto-hotspot.py`: bettercap (already required by pwnagotchi core), no
additional hardware beyond the onboard/external WiFi radio already in
use. `away_base.py`/`home_base.py`: bettercap, no additional hardware.
`ext_wifi.py`: an external USB WiFi adapter recommended for practical
use (the plugin only retargets bettercap's interface, it doesn't disable
the onboard chip, so without an external adapter there's nothing to
switch to). `extWifi.py`: an external USB WiFi adapter required - unlike
`ext_wifi.py`, this variant actually disables the onboard chip via
`/boot/config.txt`, so an external adapter must be present or the device
loses WiFi entirely.
