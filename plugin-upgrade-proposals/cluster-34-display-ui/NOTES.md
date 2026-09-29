# Notes: Display / UI cluster

**Status: 7 of 19 REMOVED. 3 fixed/extended and moved to `plugins-wip`
(`internet-connection.py`'s three-way group -> `InternetConnectionNG`,
`tweak_view.py` -> `TweakViewNG`, `timer.py` -> `TimerNG` - all three
built, documented, and sandbox-tested; not yet tested on real
hardware). 9 remain reviewed with real findings but no keep/fix
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

## Fixed and moved to `plugins-wip` (built, documented, sandbox-tested)

- **`internet-connection.py`** (its three-way group: itself, `wanmon.py`,
  `internet-conection.py`) - **-> `internet-connection-suite`
  (`InternetConnectionNG`)**. Consolidates all three into one plugin
  rather than keeping three competing implementations on the list:
  - Base behavior kept from `internet-connection.py`: hooks the real
    `internet_available` event (confirmed in `pwnagotchi/cli.py`) -
    event-driven, no polling, no blocking network calls of its own.
  - Fixes `wanmon.py`'s crash-on-load bug: reads `position_x`/
    `position_y`/`testip`/`testdns` via `self.options.get(key, default)`
    with real defaults instead of direct indexing. Also fixes a second,
    subtler `wanmon.py` bug found during the build: its
    `internet_available`/`dns_resolving` booleans were only ever set to
    `True` in `test_internet_connection()` and never reset to `False`
    on a failed check, so it was silently "stuck connected" too, just
    for a different reason than `internet-connection.py`.
  - Drops `internet-conection.py`'s design entirely: no synchronous
    `urllib.request.urlopen()` call inside `on_ui_update`.
  - **Approved addition (1 of the 3 originally proposed):**
    configurable position, label, and connected/disconnected display
    values. The other two proposed additions ("last checked" timestamp,
    on/off debounce) were not requested and were not built.
  - **Added beyond what was proposed, as part of the actual fix**: an
    `active_recheck` option (default on) - a plain `socket.create_connection()`
    TCP probe run once per epoch and once at startup (never from a
    render hook), so the status icon can now correctly flip back to
    "disconnected" if the connection drops - the one real capability
    gap shared by both `internet-connection.py` (no way to un-set
    "connected") and `wanmon.py` (tried to, but via the reset-forgetting
    bug above). Can be turned off to reproduce `internet-connection.py`'s
    original one-way behavior exactly.
  - 17 tests, all passing against the real framework. See
    `plugins-wip:internet-connection-suite/NOTES.md` for full detail.
- **`tweak_view.py`** - **-> `tweak-view-suite` (`TweakViewNG`)**.
  Fixes the hook-ordering bug: tweaks now load in `on_loaded` (confirmed
  to run before `on_ui_setup`, since plugin loading happens before the
  display/View is constructed at all) instead of the later `on_ready`,
  so saved tweaks apply on the very first UI setup instead of being
  silently delayed by one refresh cycle. Two further real bugs found
  and fixed during the build, in the plugin's own pre-existing webhook
  editor: (1) a `res += "...", json.dumps(...)` line in `dump_item()`
  that's actually a 2-tuple, raising a `TypeError` swallowed by its own
  broad `except` - meant a JSON-looking string value was never actually
  shown pretty-printed; (2) an `update_from_request()` error handler
  that referenced an undefined `ret` instead of the real `res` variable,
  a `NameError` (also swallowed by an outer `except`) that masked the
  intended "Unable to save settings" message behind a confusing,
  unrelated traceback whenever a save actually failed.
  - **Both approved additions built:** (1) load-time validation of the
    saved tweaks JSON - every entry is checked against the required
    `VSS.<element>.<attr>` shape, with a specific warning naming exactly
    which entry is malformed, instead of the original's all-or-nothing
    "the whole load failed" fallback; (2) the "webhook page to
    preview/edit tweaks live" turned out to already exist in the
    original (a full GET/POST editor was already there) - rather than
    build a redundant second one, this hardens the existing page: fixes
    both bugs above, adds a clear "not ready yet" message before the
    agent reports in, and consistently `html.escape()`s every value
    inserted into the page (the original escaped some fields but not
    others).
  - 27 tests, all passing against the real framework. See
    `plugins-wip:tweak-view-suite/NOTES.md` for full detail.
- **`timer.py`** - **-> `timer-suite` (`TimerNG`)**. Was initially
  confirmed as "keep with a documented bug" (see the original note
  below, kept for history), then revisited once the user deferred the
  choice of improvements to build. Fixes a dependency-declaration bug
  (declared an unused `scapy` pip dependency, never declared the
  `pandas` it actually imports and uses to write the CSV), the
  hardcoded `/home/pi/data/...` output path (now `output_path`,
  configurable), and an unbounded full-DataFrame rewrite on every
  single handshake (now bounded, stdlib-`csv`-based `max_rows`
  rotation). Also adds bare-MAC-string AP handling (the same
  `on_handshake` shape found earlier in `WifiJammerNG`), needed
  because the new per-network tracking below reads AP fields the
  original never touched.
  - **Three additions built, deferred to this project's judgment**:
    an optional on-screen time-to-handshake element (last value or
    rolling average), per-network best/worst capture-time tracking
    (the original had no per-network identity at all - every capture
    landed in the same flat, unlabeled 3-column log), and a real
    webhook summary page (the original's webhook did nothing but log
    that it was pressed).
  - 22 tests, all passing against the real framework. See
    `plugins-wip:timer-suite/NOTES.md` for full detail.

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

## Kept with a documented (low-priority) bug (superseded)

- **`timer.py`** - originally confirmed here as kept-as-is: no
  framework-misuse bugs, correctly uses real hooks
  (`on_wifi_update`, `on_deauthentication`, `on_handshake`) to time
  deauth-to-handshake duration and log it to CSV, with the only issue
  being a hardcoded `/home/pi/data/...` output path judged a
  deployment detail rather than a code bug. Later revisited and
  fixed/extended anyway once the user deferred a set of proposed
  improvements to this project's judgment - see "Fixed and moved to
  `plugins-wip`" above; this section is kept for history.

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
