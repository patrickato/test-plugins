# Notes: Display / UI cluster

**Status: 7 of 19 REMOVED. 2 IN PROGRESS, moving to `plugins-wip`
(`internet-connection.py`'s three-way group -> `InternetConnectionNG`,
`tweak_view.py` -> `TweakViewNG`). 1 KEPT with a documented bug
(`timer.py`). 9 remain reviewed with real findings but no keep/fix
decision made yet (5 fix candidates, 4 kept-as-is pending
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
- **`display-text.py`** - REMOVED (revised from an earlier "kept with
  documented bug" call). No bug, but no real functionality either - a
  pure demo that always shows a hardcoded "Hello World!" string with
  no config option to change it. Nothing worth preserving.
- **`sprite_faces.py`** - REMOVED (revised from an earlier "kept with
  documented bug" call). The upstream author's own code left a
  `# TODO: Something is wrong with this but I can't currently fix it`
  at the sprite face-lookup step and never resolved it. Not worth
  inheriting an unfixed upstream bug for a non-essential feature
  (sprite-based faces) when nothing here was independently diagnosed
  as fixable.

## In progress - moving to `plugins-wip`

- **`internet-connection.py`** (its three-way group: itself, `wanmon.py`,
  `internet-conection.py`) - **-> `internet-connection-suite`
  (`InternetConnectionNG`)**. Consolidating all three into one plugin
  rather than keeping three competing implementations on the list:
  - Base behavior kept from `internet-connection.py`: hooks the real
    `internet_available` event (confirmed in `pwnagotchi/cli.py`) -
    event-driven, no polling, no blocking network calls of its own.
  - Fixes `wanmon.py`'s fatal bug: reads `position_x`/`position_y`/
    `testip`/`testdns` via `self.options.get(key, default)` with real
    defaults instead of direct indexing, so it can no longer
    `KeyError`-crash on load when a config.toml doesn't set every key.
  - Drops `internet-conection.py`'s design entirely: no synchronous
    `urllib.request.urlopen()` call inside a UI-refresh hook. If a
    manual connectivity re-check is ever wanted, it belongs on a
    background timer/thread or the periodic hook, never in the
    render path.
  - Suggested improvements (pending approval before building):
    (1) configurable position AND configurable icon/text style in one
    place, since `wanmon.py` had position options `internet-connection.py`
    lacked; (2) an optional "last checked" timestamp shown alongside
    the status icon, useful for confirming the plugin isn't stuck;
    (3) a small on/off debounce (e.g. require 2 consecutive
    `internet_available`/lost events before flipping the icon) so a
    flaky connection doesn't flicker the display constantly - purely
    optional via config, defaulting to off/immediate to match current
    behavior.
- **`tweak_view.py`** - **-> `tweak-view-suite` (`TweakViewNG`)**.
  Fixes the hook-ordering bug: `self._tweaks` will be loaded during
  `on_loaded` (which runs before `on_ui_setup` gets a chance to use
  it) instead of waiting for the later `on_ready` hook, so tweaks
  apply on the very first UI setup instead of being silently delayed
  by one refresh cycle.
  - Suggested improvements (pending approval before building):
    (1) validate the tweak JSON at load time and log a clear warning
    naming which element/key is malformed, instead of only failing
    silently inside the broad try/except; (2) an optional webhook page
    to preview/edit tweaks live without editing the JSON file and
    restarting the daemon - matches the low-friction webhook pattern
    already used in `WifiJammerNG` and `webcfg_ng.py`.

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

- **`timer.py`** - no framework-misuse bugs; correctly uses real hooks
  (`on_wifi_update`, `on_deauthentication`, `on_handshake`) to time
  deauth-to-handshake duration and log it to CSV. Writes to a
  hardcoded `/home/pi/data/...` path that may not exist on every setup
  - a deployment detail (check/create that directory) rather than a
  code bug worth fixing. Kept as-is: it's a small, working, genuinely
  useful piece of telemetry (how long a capture actually takes, per
  network) that nothing else on the list tracks, and the only issue is
  a path assumption you control on your own hardware.

## Reviewed, no bugs found (kept as-is)

- **`clock.py`**, **`darkmode.py`** (same source as
  `pwnagotchi_LCD_colorized_darkmode`), **`display-aircrack.py`**,
  **`display_version.py`**, **`themes.py`** (depends on external shell
  scripts existing, a deployment concern rather than a code bug),
  **`extras/facemod/faces.py`** (the shared source behind both
  `PWNAGOTCHI-CUSTOM-FACES-MOD` and `pwnagotchi-fallout-faces-mod` - a
  trivial constants module). `internet-connection.py` itself was also
  clean, but its whole three-way group is being consolidated and
  rebuilt anyway (see "In progress" above), so it's no longer tracked
  separately here.

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
