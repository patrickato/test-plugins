# Cluster 37 - Hardware-specific

Status: **IN PROGRESS** - 10 removed, 5 fixed/upgraded and moved to
`plugins-wip` (2 merged into one, 3 individually fixed/upgraded), 1
kept as-is (no bugs found), 2 deferred at the user's request
(`flipperLink.py`, `pwndroid.py` - the latter has a real security bug
and is flagged as a priority to come back to).

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, "## Hardware-specific"
section, Group 59 in the elimination log.

## Excluded from this cluster (already handled elsewhere)

- `memtemp-plus.py` / `memtemp_adv.py` / `memtemp_ng.py` - see Cluster 25
- `prime_gsm_hat.py` - see Cluster 26
- `Touch_UI` - see Cluster 34

## Record-only, no action needed

- `pwnagotchi-18650` - a battery case design (hardware, not software)
- `pwnagotchi-plugin-pisugar2` / `pwnagotchi-plugin-pisugar3` - duplicate
  listings of `pisugar2.py`/`pisugar3.py` below (still pending decision
  themselves)
- `pwnagotchi-WittyPi4L3V7-plugin` - searched exhaustively, not present
  anywhere in this environment, could not be reviewed

## Removed at the user's request (6)

- **basiclight.py** - GPIO traffic-light-style signal lights. Dead
  `on_ai_ready`/`on_ai_policy`/`on_ai_training_start/step/end`/
  `on_ai_best_reward`/`on_ai_worst_reward` hooks (not real hooks on this
  fork - no `[ai]` self-play subsystem exists here at all). Wrong
  declared dependency (`pip: ["scapy"]`, file only imports `RPi.GPIO`,
  which itself isn't declared).
- **gpio_shutdown.py** - GPIO-triggered clean shutdown. Real `KeyError`
  on load: `self.options["gpio"]` read with no guard, and the framework
  never merges a plugin's `__defaults__` (confirmed via
  `pwnagotchi/plugins/__init__.py`'s `load()` - it assigns
  `plugin.options` straight from the user's own `config.toml` section).
- **gsmfake.py** - claimed to feed bettercap fake GPS coordinates from a
  GSM/GPRS modem. **Not actually a pwnagotchi plugin at all** - no
  `plugins.Plugin` subclass anywhere in the file, so this fork's loader
  never registers it. It's a verbatim copy of gpsd's own `gpsfake.py`
  test harness with cosmetic plugin-style dunders (`__name__`,
  `__defaults__`, `__help__`) added on top, but those never get read
  because there's no `Plugin` subclass for the loader to find.
- **img2xbm.py** - claimed to convert images to XBM format for a
  Flipper Zero display. **Not a pwnagotchi plugin** - a standalone CLI
  tool with no `plugins` import and no `Plugin` class. Its own
  `main()` function body is literally `pass` - even as a standalone
  tool it doesn't do anything when run.
- **rgb.py** - claimed RGB LED control. **Not a real plugin** - the file
  is a mismatched MicroPython/CircuitPython SPI display driver
  (`import utime`, `import ustruct` - modules that don't exist in
  standard CPython or on this pwnagotchi image), built around
  `DisplaySPI`/`Display` base classes using MicroPython's pin API
  (`.init(self.rst.OUT, value=1)`-style calls). No `Plugin` subclass
  anywhere. Reads as a vendor driver file that ended up in the wrong
  repository, not a pwnagotchi plugin at all.
- **gpio_buttons_ng.py** - GPIO button-to-shell-command mapping.
  Re-initializes GPIO pins 17/22/27 (Pimoroni display-hat LED pins)
  inside the per-button `for` loop on every single iteration - if the
  user's configured `gpios` list includes any of those three pins as a
  button, this silently reconfigures that pin away from
  `GPIO.IN, PUD_UP` + edge-detect right after setting it up, breaking
  that button.

## Removed: battery/UPS plugins for hardware the user doesn't own (4)

The battery/UPS plugins in this cluster were grouped and discussed
together. `mad_hatter.py` (see "Kept as-is" below) turned out to
genuinely support the user's actual hardware - a Waveshare UPS HAT,
matched via its `ups_type = "waveshare"` alias to its INA219 chip
driver. The other four each target different, specific hardware the
user does not own, so they were removed rather than fixed:

- **pibat.py** - PiBat I2C UPS/battery hat. Also had a real bug (opens
  the I2C bus at module-import time with no guard - a full, silent
  plugin-load failure if I2C isn't enabled/no device is present) but
  the primary reason for removal is that this isn't the user's
  hardware.
- **pisugar2.py** - PiSugar 2 UPS/battery hat. Also had real bugs
  (unguarded `KeyError` on two options; `on_unload` unconditionally
  removes a UI element that only exists on "new model" PiSugar2
  hardware, crashing unload on the original model) but removed as not
  matching owned hardware.
- **pisugar3.py** - PiSugar 3 UPS/battery hat. Also had a real bug
  (unguarded `KeyError` on the `shutdown` option, silently disabling
  auto-shutdown and spamming logs; a race condition if the UI fires
  before `on_loaded` finishes) but removed as not matching owned
  hardware.
- **pivoyager.py** - PiVoyager UPS + RTC hat. Also had real bugs
  (wrong declared dependency; unguarded coords causing a cascading
  failure; an unmapped battery-status `KeyError` every cycle; its
  shutdown watchdog thread runs outside the framework's exception
  safety net, so any error silently kills it forever) but removed as
  not matching owned hardware.

## Feature-upgraded and moved to `plugins-wip` (1 plugin)

### mad_hatter.py -> MadHatterNG (`mad-hatter-suite`, file `MadHatterNG.py`)

Universal UPS/battery monitor supporting MAX17040/17048 fuel gauges,
all INA219-based HATs (explicitly including Waveshare, per its own
docstring and `ups_type` alias table), and the PiSugar 2/2 Pro/3
families through one plugin with auto-detection. **No bugs found** -
it correctly merges its own defaults and guards throughout, unlike
every single-hardware battery plugin reviewed in this cluster. This
is the one plugin in the battery/UPS group that actually targets
hardware the user owns (a Waveshare UPS 3S HAT).

Because there were no bugs to fix, this was a **pure feature-upgrade
rebuild**, not a bugfix. Everything that already worked was preserved
verbatim: all chip-backend calibration math (MAX170xx VCELL scaling,
INA219 shunt-voltage-based current calculation, PiSugar 2/2 Pro/3
register handling), the `ups_type` auto-detect/alias system
(including `"waveshare"` -> `"ina219"`), the `self.options =
dict(self.__defaults__)` defaults-merge workaround, and the existing
on-screen positioning (`ui_position_x`/`ui_position_y`, including the
negative-x-means-"pixels in from the right edge" convention - this
plugin was already user-positionable before the rebuild).

**Naming note:** the file is `MadHatterNG.py` (capital NG, no
underscore) per the user's explicit request, but the `config.toml`
section is `[main.plugins.MadHatterNG]` - NOT snake_case
`mad_hatter_ng` - because this fork's loader
(`pwnagotchi/plugins/__init__.py`, `load_from_file()`) registers and
looks up every plugin by the plugin file's exact basename, case
included (`plugin_name = os.path.basename(filename.replace(".py",
""))`, confirmed by reading and running that function against this
file). A `mad_hatter_ng` config section for a file named
`MadHatterNG.py` would never appear in the framework's "enabled"
list - not an options bug, a total no-load. Documented prominently in
the suite's `config.toml` header, `README.md`, and its own `NOTES.md`.

**4 new features built (all approved):**

- **Threshold notifications** - fires a notification through
  whichever notification suite is available (looked up via
  `pwnagotchi.plugins.loaded`, matching the real framework's plugin
  registry) when a warning/critical/shutdown-imminent threshold is
  crossed, instead of only updating the on-screen text. Fires once
  per crossing, not every poll cycle, and degrades gracefully (log +
  skip) if `apprise-notify-suite`/`discord-suite` isn't loaded.
- **Historical trend logging** - a bounded, disk-persisted history of
  voltage/SoC/drain-rate readings (configurable size/interval), with
  new `/history` (inline-SVG rendering, no external chart dependency)
  and `/history.json` webhook pages.
- **Drain-rate / activity correlation** - reads `timer-suite`'s real
  CSV output (best-effort/optional, same graceful-degradation pattern
  as `BluetoothReconNG`'s correlation feature) to show drain rate
  during active epochs vs. idle, alongside the existing flat
  mAh/current time estimate.
- **Config-sanity webhook page** (`/sanity`) - cross-checks the
  configured `ups_type` against what was actually auto-detected on
  the I2C bus, and flags internally inconsistent option combinations
  (e.g. `shunt_ohms <= 0`, a fixed `battery_cells` that doesn't match
  the detected pack voltage, `charging_gpio` colliding with a
  reserved/I2C pin).

**Testing:** 60 automated tests passing, including spot-checks of the
preserved calibration math against hand-encoded fake I2C register
values (not just "does it run"), the positioning logic, the
notification threshold-crossing logic, history retention, the
correlation logic against a constructed sample `timer-suite` CSV, and
the sanity-check page's flagging logic. **Not tested on real hardware
yet** - this is the one plugin in the entire Hardware-specific
cluster confirmed to match hardware the user actually owns, so a
real-hardware pass here is especially worth doing: the Waveshare UPS
3S HAT's actual `shunt_ohms`/current sign, GPIO charge detection
against a real status line, notifications against a real Discord
webhook/Apprise target, and a real discharge cycle to sanity-check
`avg_current_ma` and the drain-rate correlation numbers.

**Original preserved:** an exact, unmodified copy of `mad_hatter.py`
is kept in [`originals/`](originals/) (no real upstream `config.toml`
was ever found for it - the sample in `reference-configs/` was
machine-generated from its own `__defaults__` dict, not a real found
sample, so there's no `mad_hatter.config.original.toml`).

## Fixed/upgraded individually and moved to `plugins-wip` (2 plugins)

### fix_region.py -> FixRegionNG (`fix-region-suite`, file `fix_region_ng.py`)

Forces the WiFi radio's regulatory domain (country code) via `iw reg
set`, persisted across reboots with a root-owned shell script + a
systemd service, so channels the stock regulatory domain blocks (e.g.
12/13 outside the US) become available. The core mechanism was sound;
the implementation had five real, source-verified bugs.

**Bugs fixed:**

- Import-time `KeyError` crash risk: `REGION =
  pwnagotchi.config["main"]["plugins"]["fix_region"]["region"]` ran at
  MODULE IMPORT TIME with no fallback - a user who left `region` unset
  (reasonably trusting the documented `__defaults__`, which is never
  actually merged by this fork's loader) would crash before a plugin
  instance even existed. Fixed: no config access at import time at
  all; the region is read and validated (real ISO 3166-1 alpha-2
  format check) entirely inside `on_loaded`, with a safe fallback.
- Command-injection surface: every shell interaction was raw string
  concatenation run through `os.system(...)`, and the region string
  was written directly into a generated shell script. Fixed: every
  command now runs via `subprocess.run([...])` with an argument list -
  no `shell=True`, no string-interpolated command lines anywhere.
- Config changes were silently ignored after the first load: the
  script/service files were only ever written `if not
  os.path.exists(...)`, so changing `region` and restarting did
  nothing once those files existed. Fixed: a small state file tracks
  the last-applied region; a real change is now detected and
  reapplied, and a no-change boot no longer triggers a needless
  restart.
- `on_unload` unconditionally shelled out to remove files and
  stop/disable a systemd service that might not exist, spamming stderr
  errors. Fixed: guarded file removal (`try/except FileNotFoundError`)
  and a real `systemctl is-enabled` check before stopping/disabling
  anything.
- Bogus `__dependencies__` entry (`pip: ["scapy"]`) - `scapy` is never
  imported or used anywhere in this plugin. Removed; the real
  dependency is the `iw` CLI tool (already standard on this project's
  images), documented as `apt: ["iw"]` for clarity.

**All approved upgrades built:** real ISO 3166-1 alpha-2 region
validation; all shell interaction via argument lists; the current
regulatory domain (`iw reg get`) detected and logged before any
change, and shown live on the webhook status page; an optional,
off-by-default GPS-based region auto-suggestion (looks up a loaded
GPS-providing sibling plugin, e.g. this repo's own `gps-tagger-suite`,
via `pwnagotchi.plugins.loaded`, matches coordinates against a small
hand-built ~24-country bounding-box table) - explicitly a rough,
informational-only hint (never auto-applied, degrades silently on any
failure), not a real offline geocoding database.

**Testing:** 60 automated tests passing, including region-format
validation, the "only reapply on a genuine change" logic, guarded
`on_unload` cleanup, webhook page rendering/escaping, and the
GPS-suggestion feature's firing and silent-degradation paths. **Not
tested on real hardware** - this sandbox has no real WiFi radio to
confirm `iw reg set` actually changing the live regulatory domain, or
that channels 12/13 actually appear afterward.

**Original preserved:** an exact copy of `fix_region.py`, plus its
real upstream `config.toml` sample, is kept in
[`originals/`](originals/) (`fix_region.py`,
`fix_region.config.original.toml`).

**Naming note:** unlike `MadHatterNG.py`, this suite follows
`bluetooth_recon_ng.py`'s snake_case-filename convention: the file is
`fix_region_ng.py` and the config section is
`[main.plugins.fix_region_ng]`, matching the file's exact basename per
the same verified framework fact used throughout this cluster.

### sigstr.py -> SigStrNG (`sigstr-suite`, file `sigstr_ng.py`)

Shows live WiFi signal strength (RSSI) as an on-screen bar. The
design was sound; the bugs were entirely in the implementation,
including a background timer thread that crashed on a fixed 2-second
cycle calling a framework function that doesn't exist.

**Bugs fixed:**

- `on_unload(self)` was missing the required `ui` parameter - this
  fork's real loader calls `on_unload(self, ui)`, so every unload
  raised `TypeError` before the method body ran, which also meant the
  original's `self.timer.cancel()` never executed: a crash AND a
  leaked background thread on every unload.
- The timer's `refresh()` callback called
  `pwnagotchi.plugins.notify(...)`, a function that does not exist
  anywhere in this fork's real framework (confirmed against
  `pwnagotchi/plugins/__init__.py`) - `AttributeError` on a fixed
  2-second cycle, forever, from the moment the plugin loaded.
- The entire background `threading.Timer` self-reschedule loop was
  redundant: `on_ui_update(self, ui)` (which already does the real
  signal-read-and-display work) is already called periodically by
  this fork's own UI refresh loop on its own. Removed entirely - this
  also fully resolves the thread-leak half of the first bug.
- Hardcoded interface name `"wlan0"` - some builds/adapters enumerate
  differently. Fixed: `interface` is now a config option, with
  fallback-and-warn to the first `iw dev`-detected wireless interface
  if the configured one isn't found.
- `generate_signal_bar`'s fill/empty characters were visually
  backwards (`'░'` for filled, `'█'` for empty) - a strong signal
  rendered looking mostly empty and vice versa. Swapped.

**All approved upgrades built:** a bounded (never-unbounded) signal
history ring buffer rendered as a compact unicode sparkline, both
on-screen and in full on the webhook page; strong/medium/weak
threshold classification (`STR`/`MED`/`WEAK` tags, configurable dBm
thresholds) instead of a raw number, sized for this project's
monochrome e-ink displays; optional, off-by-default RSSI-vs-handshake-
capture correlation against `timer-suite`'s real CSV output
(best-effort, degrades silently if absent); on-screen positioning
(`ui_position_x`/`ui_position_y`, same negative-x-from-right-edge
convention as `MadHatterNG.py`), replacing the original's fixed `(0,
205)` with a configurable default of the same values.

**Testing:** automated tests passing, including the signature/notify/
timer-thread bug fixes (directly confirming the removed calls/
attributes are actually gone, not just "no exception observed"), the
interface fallback logic, bounded history retention, sparkline
rendering, threshold classification at and around each boundary,
on-screen positioning, webhook rendering/escaping, and handshake
correlation (matched, out-of-window, and feature-disabled cases).
**Not tested on real hardware** - `iw dev ... link` parsing is
verified against hand-constructed sample output only, and the
strong/medium/weak thresholds are reasonable defaults, not tuned
against this project's real adapters.

**Original preserved:** an exact copy of `sigstr.py` is kept in
[`originals/`](originals/). No real upstream `config.toml`/`config.yaml`
was found for this one anywhere, so there is no
`sigstr.config.original.toml`.

**Naming note:** same snake_case-filename convention as
`fix_region_ng.py`/`bluetooth_recon_ng.py`: file `sigstr_ng.py`,
config section `[main.plugins.sigstr_ng]`.

## Merged and moved to `plugins-wip` (2 plugins -> 1 new plugin)

### blemon_plugin.py + bluetoothsniffer.py -> BluetoothReconNG (`bluetooth-recon-suite`)

Both were legitimate, correctly-framed plugins with real but fixable
bugs - normally each would have been fixed and moved to `plugins-wip`
as its own separate suite. Instead, **per the user's explicit
direction**, they were merged into one plugin covering both radio
types (BLE via bettercap's `ble.recon`, classic Bluetooth/BR-EDR via
`hcitool scan`) under one unified device table, one config, one
webhook page, and one persisted state file.

**Bugs fixed:**

- `blemon_plugin.py`:
  - Dead `on_ai_ready`/`on_ai_policy`/`on_ai_training_start/step/end`/
    `on_ai_best_reward`/`on_ai_worst_reward`/`on_free_channel` hooks -
    none of these are real hooks on this fork, removed entirely.
  - `ui.set("blecount", ...)` called in `on_bcap_ble_device_lost`, but
    the element was registered under the key `"blemon_count"` - wrong
    key, the count silently never updated on that event. BluetoothReconNG
    computes both counts live from the device table instead of a
    hand-maintained counter, so this class of bug can't recur.
  - `name is ""` identity comparison bug - fixed to `==`.
  - Wrong declared dependency (`pip: ["scapy"]`, unused) - removed.
- `bluetoothsniffer.py`:
  - Real load-time `KeyError`: `__init__` set `self.options` to a dict
    of sensible defaults, but the framework completely overwrites
    `self.options` with the raw `config['main']['plugins'][name]` dict
    before `on_loaded` runs, and `__defaults__` is never merged either -
    so `on_loaded`'s `self.options["devices_file"]` (and others) would
    `KeyError` unless the user set every key explicitly in
    `config.toml`. Fixed using the same `_opt()`/module-level `DEFAULTS`
    pattern already established in `crack-house-suite`/`timer-suite`/
    `gps-tagger-suite`.
  - `on_unload` called `ui.remove_element("BluetoothSniffer")`, but the
    element was registered under the key `"BtS"` - wrong key, would
    raise `KeyError` from `State.remove_element()` (`del
    self._state[key]` has no guard). BluetoothReconNG wraps every
    `remove_element` call individually in try/except on unload.
  - Unguarded missing-`hcitool`-binary crash (`FileNotFoundError` not
    caught) - guarded.

**All approved upgrades built:**

- Unified BLE + classic device table, deduplicated by MAC, persisted to
  disk as JSON and reloaded on `on_loaded` (counts/history survive a
  reboot).
- Configurable retention/expiry pruning (`retention_hours`, default 168
  = 7 days) - stale entries dropped from both the in-memory table and
  the persisted file.
- Configurable `rssi_threshold` filtering and a `known_devices` MAC
  allowlist (flags matches as `is_known` rather than dropping data).
- Configurable `classic_scan_interval_seconds` for the `hcitool` loop
  (BLE stays event-driven through bettercap, no polling needed).
- Offline OUI/vendor lookup - a curated table of ~90 common
  manufacturer prefixes (Apple, Samsung, Google, Amazon, Espressif,
  Raspberry Pi Foundation, etc.), with graceful "Unknown" fallback and
  an `oui_extra_path` option to load additional entries from a local
  JSON file. This is a curated subset, not the full IEEE OUI registry -
  no offline copy of that registry was available to build from, and the
  entries chosen are ones that could be stated with reasonable
  confidence rather than padded with guessed prefixes.
- Best-effort tracker flagging (`is_tracker` + `tracker_type`) for
  Apple Find My devices (company ID `0x004C`, payload type/length bytes
  `[0x12, 0x19]` - a commonly-cited pattern from public
  reverse-engineering, not an Apple-documented spec), Tile trackers
  (company ID `0x0136` alone - Tile's BT SIG-assigned company ID; no
  more specific payload pattern is publicly documented, so this is a
  broader match than the other two), and Samsung SmartTag/SmartTag+
  (service UUID containing `fd5a`, OR company ID `0x0075` with
  `payload[0] == 0x01`). **These signatures are unverified against real
  hardware** - the byte patterns come from public reverse-engineering
  write-ups, not vendor documentation, and Apple/Tile/Samsung could
  change them at any time. Treat tracker flags as a hint, not a
  certainty, until confirmed against a real AirTag/Tile/SmartTag.
- WiFi/Bluetooth correlation against **three** existing `plugins-wip`
  data sources (all optional/best-effort - if a source's file/directory
  doesn't exist, that part of the correlation is skipped silently, no
  crash, no required config):
  1. `crack-house-suite`'s `saving_path` potfile (`hostname:password`
     lines) - which nearby networks have actually been cracked.
  2. `timer-suite`'s `output_path` CSV (`timestamp`, `network`,
     `time_to_deauth`, `time_to_handshake`,
     `time_between_deauth_and_handshake`) - what WiFi networks were
     active/captured at what times.
  3. `gps-tagger-suite`'s `pn_output_path` directory (one
     `pn_ap_<hostname>_<mac>.json` file per AP with GPS coordinates) -
     location context for a correlated network, when available.
  A Bluetooth device sighting is matched against WiFi network activity
  within a configurable `correlation_window_minutes` (default 10); if
  any of those networks are in the cracked list, the device record gets
  `correlated_networks` (hostnames) and `any_cracked` (bool); if
  GPS-tagger-suite has a location for one of those networks, it's
  attached as `correlated_location`.
- Webhook status page (`on_webhook`) showing total device count plus
  **clearly labeled** BLE/Classic counts (e.g. "BLE: 5" / "Classic: 3",
  never two bare unlabeled numbers), a full device table sorted by
  last-seen, and a JSON export link.
- JSON export route that takes **no user-supplied path parameter at
  all** - it always serves exactly the one persisted device-table file
  this plugin itself writes. This was a deliberate design choice after
  this same project flagged a real path-traversal/arbitrary-file-
  disclosure bug in `pwndroid.py`'s download handler (Cluster 37's own
  findings table) - BluetoothReconNG's export has no equivalent attack
  surface because it never accepts a path from the request.
- Two independently user-configurable on-screen element positions
  (`ble_position_x`/`ble_position_y`/`classic_position_x`/
  `classic_position_y`, each defaulting to `None` = "use a sensible
  built-in position"), following the exact pattern already established
  in `crack-house-suite`'s `position_x`/`position_y`/
  `stats_position_x`/`stats_position_y`.

**Explicitly dropped from scope** (noted so it doesn't look like an
oversight): `blemon_plugin.py`'s per-device `ble.enum` auto-GATT-
enumeration, and both originals' chatty on-screen status-line
messaging - neither fits a recon/tracking tool's actual purpose.

**Originals preserved:** exact, unmodified copies of both source files
(plus their real upstream `config.toml` samples, tagged
`*.config.original.toml`) are kept in
[`originals/`](originals/) specifically so they aren't lost if
`BluetoothReconNG` needs to be abandoned or reverted for any reason.

**Testing:** 84 automated tests passing against the real cloned
framework conventions (options/defaults handling, UI element keys, OUI
lookup, tracker-signature matching against known-good sample bytes,
retention/expiry pruning, RSSI filtering, correlation logic against
constructed sample source files, webhook rendering, export route).
**Not tested on real hardware yet** - specifically still needs
verification of: bettercap's real BLE event JSON schema (this sandbox
had no bettercap Go source to confirm the exact manufacturer-data key
names used, so `_extract_manufacturer_info` degrades to "no match"
rather than guessing wrong and crashing - low risk, but real-hardware
confirmation would let tracker flagging work reliably), `hcitool scan`
output format on the actual image, and the tracker-flagging signatures
themselves against a real AirTag/Tile/SmartTag.

## Kept as-is, no bugs found (1)

- **wof.py** - "Wheel of Fortune"-style random on-screen face/message
  picker. Reviewed, no bugs found. No changes made or needed.

## Deferred at the user's request (2)

- **flipperLink.py** - bridges pwnagotchi to a Flipper Zero over
  Bluetooth. Real bugs found (a UI value set as `bool` instead of
  `str`; an unguarded `KeyError`; an undeclared `pybluez` dependency)
  and four upgrade ideas discussed (bug fixes, reconnect logic,
  two-way control from the Flipper, suppressing the user's own Flipper
  from BluetoothReconNG's device list). Saved for later - only worth
  building if/when the user has a Flipper Zero to test it against.
- **pwndroid.py** - Android companion-app webhook integration. **Has a
  real path-traversal/arbitrary-file-disclosure bug** in its webhook
  download handler - flagged as a security priority to come back to,
  not merely deferred for lack of interest. Also missing a dependency
  declaration and drops AP/station data on one code path.

## Related

An idea backlog for offensive/defensive Bluetooth plugins written up
during this cluster's review (AirTag/Tile/SmartTag detector,
BlueBorne-style passive fingerprinting, GATT service mapper, SDP
scanner, WiFi/BT data fusion, BLE advertisement spam, and dongle-
dependent ideas like raw BLE sniffing/crackle/GATT MITM) lives at the
repo root: `OFFENSIVE_BLUETOOTH_IDEAS_2026-09-29.md`. Nothing in it is
approved for building.
