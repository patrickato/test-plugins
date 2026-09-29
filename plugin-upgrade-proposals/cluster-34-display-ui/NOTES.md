# Notes: Display / UI cluster

**Status: 10 fix/improvement candidates fixed/extended and moved to
`plugins-wip` (`internet-connection.py`'s three-way group ->
`InternetConnectionNG`, `tweak_view.py` -> `TweakViewNG`, `timer.py`
-> `TimerNG`, `crack_house.py` -> `CrackHouseNG`, `more_uptime.py` ->
`MoreUptimeNG`, `viz.py` -> `VizNG`, `Touch_UI.py` -> `TouchUING`,
`clock.py` -> `ClockNG`, `display-aircrack.py` -> `DisplayAircrackNG`,
`display_version.py` -> `DisplayVersionNG` - all ten built,
documented, and sandbox-tested; none tested on real hardware yet).
`screen_refresh.py`/`ScreenRefreshNG` was also fixed and briefly
moved, then removed at the user's request after reviewing the
build - not needed on a TFT/LCD screen (its whole purpose is clearing
e-ink ghosting). `darkmode.py`, `themes.py`, and
`extras/facemod/faces.py` were removed at the user's request after
real findings on a closer read (see below), rather than fixed. Plus
the earlier removal pass covering `printp.py`,
`PwnagotchiCharacterPlugin`/`Pwan-Girl`/`screen_color_invert`,
`Bat-Trinity`, `display-text.py`, and `sprite_faces.py` (see below).
`console.py` remains formally kept-as-is with its one documented
cosmetic bug (Cluster 24). `PWNAGOTCHI-CUSTOM-FACES-MOD`,
`pwnagotchi_LCD_colorized_darkmode`, and `pwnagotchi-fallout-faces-mod`
appear to be the same underlying sources as the now-removed
`faces.py`/`darkmode.py` (re-hosted as fuller hardware/theme mod
repos rather than single-file plugins) - not separately reconciled
against the master list's own dedup convention, left untouched
pending a scope decision.**

All source read from `itsdarklikehell/pwnagotchi-plugins/` unless
otherwise noted, checked against the real cloned
`jayofelony/pwnagotchi` framework (`pwnagotchi/agent.py`,
`pwnagotchi/automata.py`, `pwnagotchi/plugins/__init__.py`,
`pwnagotchi/ui/view.py`, `pwnagotchi/ui/display.py`, `pwnagotchi/cli.py`).

## Removed this pass (6)

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
- **`screen_refresh.py`** - REMOVED (revised after review - was
  fixed and briefly moved to `plugins-wip` as `ScreenRefreshNG` in the
  same pass that produced the other 4 fix-candidate suites below,
  then removed once the user reviewed it: not needed on a TFT/LCD
  screen, since its entire purpose is clearing e-ink ghosting. The
  underlying bug it fixed was real and confirmed - `ui.init_display()`
  only exists on `Display`, never on the plain `View` plugin hooks
  actually receive, so it crashed with `AttributeError` every
  `refresh_interval` ticks, on every display type - but the feature
  itself has no use case on the target hardware, so it's removed
  rather than kept around unused).

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
- **`crack_house.py`** (+ the V0r-T3x archive's "-dev" variant,
  functionally identical) - **-> `crack-house-suite` (`CrackHouseNG`)**.
  Originally flagged only for direct-`self.options[...]` indexing and a
  hardcoded `iwconfig wlan0` interface; reading the source in full for
  the rebuild surfaced something much bigger underneath: `on_ui_setup`
  called `ui.is_waveshare_v2()`, `ui.is_inky()`, `ui.is_lcdhat()`, and
  similar display-detection methods - confirmed these only exist on
  this fork's `Display` class, never on the plain `View` that plugin
  hooks actually receive (`View.__init__`/`View.update()` always call
  `plugins.on('ui_setup'/'ui_update', self)` with themselves). So this
  plugin crashed with `AttributeError` on the very first line of
  `on_ui_setup`, on every display type, on every load - it could never
  load at all on this fork, before even reaching the originally-known
  bug. A second `UnboundLocalError` (an `s_pos` variable only assigned
  in one unreachable branch) sat behind that. Also fixed: a crash on
  any missing configured potfile (the original's bare `open()` had no
  error handling), and an inconsistent "nothing nearby" fallback that
  shelled out to one hardcoded external file instead of the plugin's
  own configured/merged data.
  - Replaced the broken display-detection entirely with configurable
    `position_x`/`position_y` (defaulting to the original's own
    fallback values, so nothing changes for the common case).
  - **User-approved additions**: case-insensitive hostname matching in
    `on_wifi_update`, and cross-reboot persistence of the merged
    cracked list (`on_loaded` also seeds from its own previous
    `saving_path` output).
  - 20 tests, all passing against the real framework. See
    `plugins-wip:crack-house-suite/NOTES.md` for full detail.
- **`more_uptime.py`** - **-> `more-uptime-suite` (`MoreUptimeNG`)**.
  Fixes the indentation bug: `ui.add_element(...)` was nested inside
  the `else` branch of `if "position" in self.options`, so setting a
  custom position (the entire point of the option) meant the element
  was never created at all, while `on_ui_update` still unconditionally
  tried to update it. Also fixes a masked-error bug: the update
  handler's `except` block referenced `uiItems`, a variable only ever
  assigned inside one conditional branch of the try block above it -
  any exception raised earlier crashed the handler a second time with
  `NameError`, hiding the real problem.
  - **User-approved additions**: a configurable `cycle_interval` (was
    hardcoded to 5 seconds), and a configurable `states` list (subset/
    order of which of IN/PR/UP cycle - was a fixed hardcoded order).
  - 20 tests, all passing against the real framework. See
    `plugins-wip:more-uptime-suite/NOTES.md` for full detail.
- **`viz.py`** - **-> `viz-suite` (`VizNG`)**. Originally flagged only
  for an uninitialized `self.channel`; reading the source in full
  surfaced a bigger bug underneath: the file's import,
  `from pwnagotchi.wifi import freq_to_channel`, points at a module
  that does not exist anywhere on this fork (confirmed - there is no
  `pwnagotchi/wifi.py`; the real module is `pwnagotchi/mesh/wifi.py`).
  This plugin could never even be imported, let alone reach the
  originally-known bug. Both are fixed: the import now points at
  `pwnagotchi.mesh.wifi`, and `self.channel` is initialized to `None`
  in `__init__` (the graph-building code already tolerated a falsy
  channel gracefully - the bug was purely the missing attribute).
  - **User-approved additions**: a last-updated timestamp on the
    webhook page (a new `meta` endpoint); already-cracked networks
    cross-referenced against CrackHouseNG's `saving_path` file
    (case-insensitively) and marked with a star symbol and
    "[CRACKED]" label on the graph; and a configurable
    `poll_interval_ms` (was hardcoded to 5000ms).
  - 26 tests, all passing against the real framework except genuine
    `plotly` itself, which wasn't installable in this build's sandbox
    - a small local stand-in covers its public interface instead. See
    `plugins-wip:viz-suite/NOTES.md` for full detail.
- **`Touch_UI.py`** - **-> `touch-ui-suite` (`TouchUING`)**. Relevant
  to this device since it has a real MPI3501 touchscreen, so this
  rebuild deliberately stayed conservative - fixing only concrete,
  provable bugs rather than a broader redesign. Fixes both
  originally-flagged bugs: (1) `Touch_Button.draw()`'s except handler
  called `logging(repr(e))` - `logging` is the module, not callable,
  so a real drawing exception raised a second, unhandled `TypeError`
  instead of being logged; (2) `on_internet_available` did
  `check_output(["apt", "install", "-y"].extend(self.needsAptPackages))`
  - `list.extend()` mutates in place and returns `None`, so this always
  crashed with `check_output(None)`. Two more bugs found during the
  build: a bare `if reverse:` (undefined name, should be
  `button.reverse`) that would `NameError` on any momentary+reverse
  touch button; and a dead "missing evtest binary" check (`if not
  evtest:` right after `Popen(...)` - a `Popen` object is always
  truthy, so a genuinely missing binary instead raised
  `FileNotFoundError` that was swallowed by a broader try/except much
  further out, meaning the plugin's own auto-install-on-connectivity
  feature could never actually trigger).
  - **User-approved additions**: a real webhook status page (reader
    thread alive?, touchscreen process active?, last touch seen?,
    pending apt packages?) - the original returned nothing at all; and
    long-press detection (a new `longpress_seconds` option drives an
    extra `touch_longpress` event dispatched alongside the normal
    `touch_release`, through the same targeted/broadcast dispatch
    logic as every other event).
  - 33 tests, all passing against the real framework. The core
    touch-detection pipeline (spawning `evtest`/`ts_print`, parsing
    real touch input) can't be exercised without physical touchscreen
    hardware - **please test this one carefully on the real MPI3501
    setup**. See `plugins-wip:touch-ui-suite/NOTES.md` for full detail.

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

## Reviewed, no bugs found and fixed/extended anyway (moved to plugins-wip)

Like `timer.py` above, these three were originally confirmed clean on
a first read and left kept-as-is. When the user asked for improvement
suggestions on the remaining kept-as-is plugins in this cluster, all
three were approved for a pure feature/efficiency rebuild (no bugs to
fix, just additions) and moved to `plugins-wip`:

- **`clock.py`** -> `clock-suite` (`ClockNG`). Adds configurable
  positions (were hardcoded) and configurable `strftime` date/time
  format strings (the original hardcoded 12-hour time with no way to
  get a 24-hour clock without editing the source), with a validating
  fallback for a bad format string. 16 tests passing.
- **`display-aircrack.py`** -> `display-aircrack-suite`
  (`DisplayAircrackNG`). The original shelled out to `ps -A` on
  *every single UI render tick* just to check one boolean status -
  now throttled via a configurable `check_interval` (default 3s),
  with the displayed value still updating every tick from the last
  known state. Also adds configurable position and status text
  (was a bare `"(1)"`/`"(0)"`), and drops an unused `scapy`
  dependency. 13 tests passing.
- **`display_version.py`** -> `display-version-suite`
  (`DisplayVersionNG`). Adds a configurable position (was hardcoded)
  and drops an unused `scapy` dependency. 7 tests passing.

All three sandbox-tested against the real cloned framework; none
tested on real hardware yet. See each suite's own
`plugins-wip:*-suite/NOTES.md` for full detail.

## Reviewed, real findings on a closer look (REMOVED at the user's request)

These three were also on the "kept as-is" list after the first pass,
but reading the source in full while gathering improvement
suggestions for the group above surfaced real problems in each - the
user chose to drop all three rather than fix them:

- **`darkmode.py`** (same source as `pwnagotchi_LCD_colorized_darkmode`) -
  hardcodes `pwnagotchi.ui.view.BLACK = 0xFF` / `WHITE = 0x00` on
  load (and the reverse on unload) without reading
  `config['ui']['invert']` - the exact setting `View.__init__` itself
  uses to decide which BLACK/WHITE pair is "native" for a given
  display (confirmed in `pwnagotchi/ui/view.py`). On a device
  configured with `invert = true`, darkmode's hardcoded values may
  not compose correctly with the display's actual native state - a
  real, previously undocumented gap, not just a style nit. Also
  declares an unused `scapy` pip dependency.
- **`themes.py`** - `get_html()`'s `except` branch logs the read
  error but falls through to `return html_data`, a name that was
  never assigned in that branch - `UnboundLocalError` (not the
  original's own logged error) if `themes.html` is ever
  missing/unreadable next to the plugin file. Also hardcodes three
  absolute script paths (`/root/flip_col.sh`, `/root/flip_faces.sh`,
  `/root/flip_led.sh`) with no existence check, and swallows a
  missing-script `FileNotFoundError` into a bare `return` (`None`)
  with no real error surfaced to the browser. Plus an unused `scapy`
  dependency.
- **`extras/facemod/faces.py`** (the shared source behind both
  `PWNAGOTCHI-CUSTOM-FACES-MOD` and `pwnagotchi-fallout-faces-mod`) -
  not actually a plugin at all (no `Plugin` subclass, so this fork's
  loader never registers it). Diffed byte-for-byte against the real
  framework's own `pwnagotchi/ui/faces.py` - it's an exact copy. Face
  customization is already natively supported via `config['ui']
  ['faces']` (confirmed: `View.__init__` calls
  `faces.load_from_config(config['ui']['faces'])`), so this file adds
  nothing the framework doesn't already do built-in.

`internet-connection.py` itself was also clean on its own read, but
its whole three-way group was consolidated and rebuilt anyway (see
"In progress" above), so it was never tracked separately here.

## Correction (added during Cluster 36 review, 2026-09-29)

Two claims in this document turn out to be based on an incorrect
premise about what `on_ui_setup`/`on_ui_update`'s `ui` parameter
actually is, and both are corrected here:

- The `crack_house.py` writeup above states that `ui.is_waveshare_v2()`,
  `ui.is_inky()`, `ui.is_lcdhat()`, and similar display-detection
  methods "only exist on this fork's `Display` class, never on the
  plain `View` that plugin hooks actually receive," and that this
  crashed `crack_house.py` with `AttributeError` on the very first
  line of `on_ui_setup`, on every display type, on every load.
- The `screen_refresh.py` writeup above makes the same claim about
  `ui.init_display()`, used inside `on_ui_update`.

Both are **wrong**. This was re-checked empirically while researching
Cluster 36 (a different plugin, `bitcoin.py`, uses the same
`is_waveshare_v2()`-style pattern in `on_ui_setup`): a real `Display`
object was constructed in the sandbox from the real
`pwnagotchi/defaults.toml`, and `plugins.on` was instrumented to
capture exactly what `on_ui_setup` receives. The result confirmed the
`ui` parameter genuinely is a `Display` instance, not a bare `View`.
The reason is in `pwnagotchi/ui/view.py`: `View.__init__` sets
`self._implementation = impl` and then calls
`plugins.on('ui_setup', self)` — and since `Display.__init__` calls
`super(Display, self).__init__(...)` first, `self` is genuinely
Display-typed for the whole time `View.__init__` (and by extension
`View.update()`, which fires `on_ui_update` the same way) is running.
Python's object type is fixed at construction, independent of which
class's `__init__` happens to be executing. So `is_waveshare_v2()`,
`is_inky()`, `init_display()`, and the rest of `Display`'s
hardware-detection methods are all genuinely callable from either
hook, on every display type, with no crash.

**What this does and doesn't change:**

- It does **not** change `CrackHouseNG`'s disposition — the rebuild
  fixed several other independently-real bugs in `crack_house.py`
  (the `UnboundLocalError`, the missing-potfile crash, the
  inconsistent fallback source), so the fix was still warranted; only
  the "crashed on every load" framing for this one specific cause was
  incorrect. The display-detection replacement (configurable
  `position_x`/`position_y`) already built into `CrackHouseNG` is
  harmless and stays as-is either way.
- It does **not** change `screen_refresh.py`'s final disposition —
  it was removed at the user's request because e-ink-ghosting
  clearing has no use case on his TFT/LCD screen, a reason entirely
  independent of this bug claim.
- It **does** mean neither plugin actually had a load-crashing display-
  detection bug on this fork in the first place — that specific
  diagnosis in both writeups above should be read as superseded by
  this note, not as an accurate account of why either plugin needed
  fixing.

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
