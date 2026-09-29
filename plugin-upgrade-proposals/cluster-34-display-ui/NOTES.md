# Notes: Display / UI cluster

**Status: 5 of 19 REMOVED, 5 KEPT with a documented bug (decision
confirmed). 9 remain reviewed with real findings but no keep/fix
decision made yet (6 fix candidates, 3 kept as-is pending
confirmation) - left on the master list, decisions pending.**

All source read from `itsdarklikehell/pwnagotchi-plugins/` unless
otherwise noted, checked against the real cloned
`jayofelony/pwnagotchi` framework (`pwnagotchi/agent.py`,
`pwnagotchi/automata.py`, `pwnagotchi/plugins/__init__.py`,
`pwnagotchi/ui/view.py`, `pwnagotchi/ui/display.py`, `pwnagotchi/cli.py`).

## Removed this pass (5)

- **`printp.py`** - REMOVED. Explicitly an example/demo plugin per its
  own docstring. Has no `__defaults__` block at all and reads every UI
  coordinate via direct `self.options["t0_x_coord"]`-style indexing -
  `KeyError`-crashes on load unless a user's config.toml happens to set
  every coordinate key explicitly.
- **`PwnagotchiCharacterPlugin`**, **`Pwan-Girl`**, **`screen_color_invert`** -
  REMOVED, record only. No source code locatable anywhere in the
  cloned plugin archives after a real search (checked
  `pwnagotchi-unofficial/plugins_archive/*` by name and keyword, and
  the `reference-configs/MANIFEST.md`, which had already flagged all
  three the same way during the earlier config-harvest pass). Likely
  dead, renamed, or asset-only projects with nothing left to review or
  fix.
- **`Bat-Trinity`** (hannadiamond's Waveshare 3.7" e-paper driver) -
  REMOVED. `initialize()` imports from
  `pwnagotchi.ui.hw.libs.waveshare.v37inch.epd3in7` - a module path
  that does not exist on this fork. This fork's real waveshare
  e-paper drivers only include `v4in37g`; there is no `v37inch`
  driver. The display can never initialize - `ModuleNotFoundError`
  every time.

## Reviewed, fix candidates (decision deferred)

- **`crack_house.py`** (+ the V0r-T3x archive's "-dev" variant, which
  is functionally identical - same logic, just missing the
  itsdarklikehell version's extra logging/try-except/`__dependencies__`
  block) - reads `self.options["files"]`,
  `self.options["saving_path"]`, etc. via direct indexing with no
  fallback. This fork never merges a plugin's `__defaults__` dict into
  `self.options`, so any config.toml missing one of these keys
  `KeyError`-crashes the plugin on load. Also hardcodes `iwconfig
  wlan0` instead of reading the real interface from
  `pwnagotchi.config['main']['iface']`.
- **`wanmon.py`** (one of three independent internet-status
  implementations bundled under `internet-connection.py` on the master
  list) - same `__defaults__`-not-merged bug as `crack_house.py`:
  reads `self.options["position_x"]`, `["position_y"]`, `["testip"]`,
  `["testdns"]` directly with no `.get()`/`in` guard, `KeyError`-crashes
  on load unless every key is set explicitly.
- **`more_uptime.py`** - real indentation bug in `on_ui_setup`: the
  `ui.add_element("more_uptime", ...)` call is nested inside the branch
  that only runs when the user has NOT set a custom `position` option.
  Set `position` and the element is never created; every later
  `on_ui_update` call then fails against a UI element that doesn't
  exist.
- **`screen_refresh.py`** - calls `ui.init_display()`, but that method
  only exists on `Display` (`pwnagotchi/ui/display.py`) - the object
  actually passed to `on_ui_update` hooks is `View`
  (`pwnagotchi/ui/view.py`), which has no such method and no
  delegation to one. The plugin's entire purpose (forcing a periodic
  e-ink refresh) can never execute; always `AttributeError`.
- **`viz.py`** - `self.channel` is never initialized in `__init__`,
  only set inside `on_channel_hop`. Hitting the `/plugins/viz/update`
  webhook before the first channel-hop event fires (plausible right
  after boot) raises an unhandled `AttributeError` in
  `Viz.create_graph()`, 500ing the request. `on_webhook` has no
  try/except around the call.
- **`Touch_UI.py`** - the plugin backing the master-list's `Touch_UI`
  entry; relevant to this device since it has a real MPI3501 touchscreen.
  Two real bugs: (1) `Touch_Button.draw()`'s except handler calls
  `logging(repr(e))` - `logging` is the imported module, not callable,
  so any exception during button drawing throws a *new*, unhandled
  `TypeError` from inside the except block, which can kill the UI
  render thread; (2) `on_internet_available` does
  `check_output(["apt", "install", "-y"].extend(self.needsAptPackages))`
  - `list.extend()` mutates in place and returns `None`, so this always
  calls `check_output(None)` and crashes whenever connectivity comes
  up with `needsAptPackages` configured.

## Kept with a documented (low-priority) bug (decision confirmed)

- **`display-text.py`** - no bug, but it's a pure demo: always shows
  a hardcoded "Hello World!" string, not configurable.
- **`internet-conection.py`** (typo-named mirror, NeonLightning's) -
  makes a blocking `urllib.request.urlopen(..., timeout=0.5)` call
  synchronously inside `on_ui_update`, which fires on every UI refresh
  tick - visibly stutters the display when offline or slow to respond.
- **`timer.py`** - no framework-misuse bugs; writes to a hardcoded
  `/home/pi/data/...` path that may not exist on every setup, a
  deployment detail rather than a code bug.
- **`tweak_view.py`** - `self._tweaks` is loaded in `on_ready`, but
  `on_ui_setup` (which runs earlier, from `View.__init__`) tries to use
  it first. Caught by a broad try/except and logged as a warning -
  tweaks are simply delayed by one refresh cycle rather than applying
  immediately. Not fatal.
- **`sprite_faces.py`** - the author's own code comment admits it's
  broken (`# TODO: Something is wrong with this but I can't currently
  fix it`) at the face-lookup step. Left as a documented, self-flagged
  issue rather than independently diagnosed here.

## Reviewed, no bugs found (kept as-is)

- **`clock.py`**, **`darkmode.py`** (same source as
  `pwnagotchi_LCD_colorized_darkmode`), **`display-aircrack.py`**,
  **`display_version.py`**, **`internet-connection.py`** (the clean
  one of the three internet-status implementations - confirmed
  `internet_available` is a real hook via `pwnagotchi/cli.py`),
  **`themes.py`** (depends on external shell scripts existing, a
  deployment concern rather than a code bug), **`extras/facemod/faces.py`**
  (the shared source behind both `PWNAGOTCHI-CUSTOM-FACES-MOD` and
  `pwnagotchi-fallout-faces-mod` - a trivial constants module).

## Real vs. imagined hooks confirmed this cluster

Unlike Cluster 33, no plugin in this batch invented a fake hook name.
Every hook referenced across this cluster was confirmed real:
`internet_available` (`pwnagotchi/cli.py`), `display_setup`
(`pwnagotchi/ui/display.py`), `wifi_update`, `deauthentication`,
`handshake`, `channel_hop` (all `pwnagotchi/agent.py`), and
`ui_setup`/`ui_update` (`pwnagotchi/ui/view.py`).

## Dependencies

None of the removed plugins introduced any dependency beyond what's
already accounted for elsewhere in the audit.
