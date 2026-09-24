# Pwnagotchi Plugin Project — Build List

**Status:** planning / list locked, details TBD
**Target platform:** Jayofelony Pwnagotchi image (Debian Trixie aarch64, Python 3.13.x)
**License intent:** GPLv3 (matches upstream Pwnagotchi)
**Scope rule:** every plugin here fills a real gap or fixes broken/unfinished behavior in the
Pwnagotchi ecosystem — nothing that duplicates a bundled or known-good community plugin.

Each entry is a standard Pwnagotchi plugin (a Python class using `on_loaded`,
`on_ui_setup`, `on_ui_update`, `on_handshake`, `on_epoch`, `on_internet_available`,
`on_wifi_update`, `on_bcap_*`, and/or a web handler). Details (config schema, exact
hooks, UI placement, storage) get ironed out per-plugin before we build it.

Legend — **Status:** `planned` · `speccing` · `building` · `testing` · `done`
Legend — **Lift:** S (small) · M (medium) · L (large)

---

## Progress — built, tested off-Pi, pushed
Off-Pi unit tests only (fake `pwnagotchi` harness). **Physical Pi validation is still
pending for every plugin below.**

- ✅ P05 `own_network_allowlist` — 7 tests
- ✅ P30 `boot_post` — 6 tests
- ✅ P39 `streaks` — 7 tests
- ✅ P33 `circadian_faces` — 6 tests
- ✅ P41 `auto_timezone` — 8 tests
- ✅ P46 `field_notes` — 8 tests
- ✅ P01 `handshake_janitor` — 9 tests
- ✅ P02 `capture_grader` — 6 tests
- ✅ P03 `crack_reconciler` — 6 tests
- ✅ P04 `capture_retention` — 7 tests

- ✅ P07 `sd_wear` — 8 tests
- ✅ P06 `doctor` — 7 tests
- ✅ P12 `battery_historian` — 9 tests
- ✅ P14 `thermal_predictor` — 6 tests
- ✅ P13 `fan_curve` — 6 tests

- ✅ P21 `channel_occupancy` — 5 tests
- ✅ P38 `signal_compass` — 7 tests
- ✅ P24 `rtl433_ambient` — 7 tests
- ✅ P25 `adsb_ambient` — 6 tests

**Phases 1–4 complete (19 plugins, 135 tests green).**
Next: Phase 5 — connectivity (P18 ha_mqtt → P20 mesh_vpn_presence → P43 ble_console).

---

## Batch A — Capture lifecycle (the biggest hole in the ecosystem)

Everything captures; almost nothing manages captures afterward. This batch is the
project's flagship because it's near-total whitespace.

### P01 — Handshake Janitor  `handshake_janitor`
- **Purpose:** de-duplicate partial/duplicate `.pcap` captures per BSSID, keep the most
  complete EAPOL set, reclaim SD space.
- **Gap:** no maintained plugin manages capture files after they're written.
- **Hooks:** `on_handshake`, `on_epoch` (periodic sweep), web view for the keep/drop log.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #1

### P02 — Capture Quality Grader  `capture_grader`
- **Purpose:** score each capture (full 4-way handshake? PMKID? beacon present?) so only
  crackable files get uploaded/kept.
- **Gap:** uploaders fire on everything, including dead files.
- **Hooks:** `on_handshake`, UI badge, web list.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #2

### P03 — Crack-Status Reconciler  `crack_reconciler`
- **Purpose:** one local view merging wpa-sec / OHC / local hashcat results back onto each
  capture, so solved handshakes aren't re-uploaded.
- **Gap:** results live in three silos; nothing reconciles them on-device.
- **Hooks:** `on_internet_available` (pull results), web dashboard.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #3

### P04 — Retention / Expiry Engine  `capture_retention`
- **Purpose:** age- and SD-pressure-based cleanup with an owner-visible "about to delete"
  queue and a grace window.
- **Gap:** no policy-driven retention exists; cards fill until something breaks.
- **Hooks:** `on_epoch`, web review queue.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #4

### P05 — Own-Network Allowlist  `own_network_allowlist`
- **Purpose:** tag the owner's home/lab BSSIDs as authorized practice; separate them from
  field logs and change device reactions to them.
- **Gap:** no first-class notion of "my own gear" for authorized testing.
- **Hooks:** `on_wifi_update`, `on_handshake`, config-driven allowlist, UI marker.
- **Lift:** S · **Status:** planned · **Brainstorm ref:** #5

### P42 — Wordlist Manager  `wordlist_manager`
- **Purpose:** manage/rotate/dedupe local wordlists for the cracking backends
  (quickdic/hashcat), fetch from configured sources, report sizes/coverage. Supports
  authorized cracking of the owner's own captures without being another cracker.
- **Gap:** wordlist handling is manual and ad-hoc; no plugin curates them on-device.
- **Hooks:** `on_internet_available` (fetch/refresh), web manager view, config for sources
  and dedupe policy.
- **Lift:** M · **Status:** planned · **Added:** Round 3 (2026-09-24)

---

## Batch B — Device health & self-repair

`watchdog` restarts wedged services, but nothing *explains* or *protects the card*.

### P06 — Doctor / Explain  `doctor`
- **Purpose:** read recent logs + state and produce a concise "what's wrong, why, and what
  to do" (stuck wifi driver, low disk, pwngrid down, noisy plugin, bt-tether fail).
- **Gap:** diagnosis is manual log-reading today.
- **Hooks:** `on_epoch`, web report, optional UI health glyph.
- **Lift:** L · **Status:** planned · **Brainstorm ref:** #6

### P07 — SD-Wear Estimator  `sd_wear`
- **Purpose:** track write volume over time, estimate remaining card life, warn before it
  dies. Complements a RAM-buffered logging strategy.
- **Gap:** SD death kills more Pis than anything and nobody measures it.
- **Hooks:** `on_epoch`, UI counter, web trend.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #7

### P30 — Boot POST Card  `boot_post`
- **Purpose:** one startup screen — "everything checked out (or didn't)": radio, GPS,
  disk, services, clock, key plugins.
- **Gap:** no consolidated power-on self-test surface exists.
- **Hooks:** `on_ready`/`on_loaded`, one-shot UI card, web detail.
- **Lift:** S · **Status:** planned · **Brainstorm ref:** #30

### P36 — Plugin Conflict Referee  `conflict_referee`
- **Purpose:** detect when two plugins fight over the display, GPIO pins, or `config.toml`
  keys, and report exactly which plugins and which resource.
- **Gap:** a huge share of "why is my screen/pin broken" problems are silent plugin
  collisions with no tooling to spot them.
- **Hooks:** `on_loaded`/`on_ready` (scan registered UI elements, claimed pins, watched
  keys), web report, UI warning glyph.
- **Lift:** M · **Status:** planned · **Added:** Round 2 (2026-09-24)

---

## Batch C — Power & thermal (beyond reading a UPS)

### P12 — Battery Health Historian  `battery_historian`
- **Purpose:** learned runtime curve per charge cycle; warn as a cell ages. UPS plugins
  show instantaneous % only.
- **Gap:** no longitudinal battery-health tracking.
- **Hooks:** `on_epoch` (sample), web trend chart. Reads existing UPS/PiSugar data.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #12

### P13 — PWM Fan Curve  `fan_curve`
- **Purpose:** real temperature-driven PWM fan control with a configurable curve and
  hysteresis; today it's mostly on/off or manual.
- **Gap:** no clean temp→PWM curve plugin.
- **Hooks:** `on_epoch`, GPIO PWM, UI RPM/temp readout. **HW:** PWM-capable fan.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #13

### P14 — Thermal-Throttle Predictor  `thermal_predictor`
- **Purpose:** from the temperature slope, act *before* the throttle hits (warn / shed
  optional load / spin fan early).
- **Gap:** everything reacts after throttling, not before.
- **Hooks:** `on_epoch`, integrates with P13, UI warning.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #14

---

## Batch D — Connectivity that isn't just "tether"

### P18 — Home Assistant MQTT Discovery  `ha_mqtt`
- **Purpose:** auto-register temp / captures / mood / battery / uptime as Home Assistant
  sensors via MQTT discovery.
- **Gap:** widely wanted, no clean maintained plugin.
- **Hooks:** `on_epoch` (publish), `on_internet_available`, MQTT client. **Dep:** broker.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #18

### P20 — Tailscale / WireGuard Presence  `mesh_vpn_presence`
- **Purpose:** bring the unit up on the owner's own tailnet/WG so the companion reaches it
  anywhere — no port-forwarding.
- **Gap:** remote reach today means manual VPN setup outside pwnagotchi.
- **Hooks:** `on_loaded` (bring up), `on_internet_available`, UI status, web link.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #20

### P43 — Companion BLE Serial Console  `ble_console`
- **Purpose:** expose status and a small set of safe, allow-listed commands over a BLE
  UART service so a phone can reach the unit when there is no IP network at all.
- **Gap:** remote status today assumes an IP link; nothing offers a no-network BLE path.
- **Hooks:** `on_loaded` (start BLE service thread), `on_epoch` (refresh advertised status),
  config for command allow-list and pairing. **HW:** BLE-capable adapter.
- **Lift:** L · **Status:** planned · **Added:** Round 3 (2026-09-24)

---

## Batch E — Passive RF awareness (observe, never attack)

### P21 — Channel Occupancy Logger  `channel_occupancy`
- **Purpose:** log which 2.4/5 GHz channels are busiest over time; render a simple heatmap.
- **Gap:** genuinely useful, nobody logs it cleanly.
- **Hooks:** `on_wifi_update`/`on_bcap_wifi_ap_new`, web heatmap.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #21

### P24 — rtl_433 Ambient Sniffer  `rtl433_ambient`
- **Purpose:** if an RTL-SDR is present, passively log 433 MHz weather/TPMS/sensor beacons
  as ambient environment data.
- **Gap:** no Pwnagotchi plugin bridges rtl_433.
- **Hooks:** background reader of `rtl_433 -F json`, `on_epoch` aggregate, web list.
  **HW:** RTL-SDR. **Dep:** `rtl_433`.
- **Lift:** L · **Status:** planned · **Brainstorm ref:** #24

### P25 — ADS-B Ambient  `adsb_ambient`
- **Purpose:** planes overhead (from a local dump1090 feed) as ambient/event data.
- **Gap:** no plugin consumes ADS-B.
- **Hooks:** poll dump1090 JSON, `on_epoch`, UI/event trigger. **HW:** RTL-SDR + dump1090.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #25

### P38 — Signal Compass  `signal_compass`
- **Purpose:** turn the RSSI trend of a selected BSSID into a warmer/colder "getting
  closer" readout — useful for locating your own misplaced device or AP.
- **Gap:** RSSI is shown as a raw number; nothing turns it into directional/proximity
  guidance.
- **Hooks:** `on_wifi_update`/`on_bcap_wifi_ap_new` (track target RSSI), UI meter, web view.
- **Lift:** M · **Status:** planned · **Added:** Round 2 (2026-09-24)

---

## Batch F — Knowledge / data on-device

### P29 — Offline Reader (Kiwix / ZIM)  `offline_reader`
- **Purpose:** manuals / wiki on-device via a bundled ZIM reader; a genuinely useful
  field-computer feature.
- **Gap:** no offline-library plugin.
- **Hooks:** web handler serving ZIM content, optional UI shortcut. **Dep:** `libzim`/kiwix.
- **Lift:** L · **Status:** planned · **Brainstorm ref:** #29

---

## Batch G — Behavior & delight

### P33 — Circadian Faces  `circadian_faces`
- **Purpose:** shift face/mood by real sunrise/sunset (from GPS or configured location) —
  no fake data, just time of day.
- **Gap:** faces are static to time; nothing ties them to the real day cycle.
- **Hooks:** `on_ui_update`, sun-times calc from GPS/config.
- **Lift:** S · **Status:** planned · **Brainstorm ref:** #33

### P34 — Achievement / Trophy Engine  `achievements`
- **Purpose:** a real milestone/badge system (first-of-kind, streaks, totals, hidden ones)
  — `age` tracks raw stats but there's no achievement layer.
- **Gap:** no extensible achievement framework exists.
- **Hooks:** `on_handshake`/`on_epoch`/`on_wifi_update` (triggers), persistent store, web
  trophy cabinet, UI toast.
- **Lift:** L · **Status:** planned · **Brainstorm ref:** #34

### P35 — Daily Digest Card  `daily_digest`
- **Purpose:** a rendered end-of-day summary (captures, distance, new networks, uptime)
  saved to disk and optionally pushed.
- **Gap:** no daily rollup surface.
- **Hooks:** `on_epoch` (day boundary), render to PNG, optional notifier handoff.
- **Lift:** M · **Status:** planned · **Brainstorm ref:** #35

### P39 — Streak & Milestone Tracker  `streaks`
- **Purpose:** track days alive, longest outing, most networks in a day, consecutive-day
  streaks — the longevity stats that make people attached to the device.
- **Gap:** `age` tracks raw totals; nothing surfaces streaks/records. Complements the
  achievement engine (P34) but is its own lightweight records board.
- **Hooks:** `on_epoch`/`on_handshake` (update counters), persistent store, UI record line,
  web board.
- **Lift:** S · **Status:** planned · **Added:** Round 2 (2026-09-24)

### P46 — Field Notes Annotator  `field_notes`
- **Purpose:** attach a quick text note to the current session/location from the web UI or
  a phone ("cool spot", "my house", "test rig") for later review alongside captures/tracks.
- **Gap:** no way to annotate a session in the moment; context is lost by review time.
- **Hooks:** web handler (add/list notes), `on_epoch` (stamp time/GPS), persistent store.
- **Lift:** S · **Status:** planned · **Added:** Round 3 (2026-09-24)

---

## Batch H — Display & UI integrity

### P37 — E-ink Ghosting Manager  `eink_ghosting`
- **Purpose:** schedule periodic full refreshes and budget partial updates on e-ink
  displays to fight ghosting/burn-in, with configurable refresh cadence and hysteresis.
- **Gap:** e-ink ghosting is a chronic, widely-complained-about problem with no clean
  dedicated fix.
- **Hooks:** `on_ui_update` (count partial updates), scheduled full-refresh trigger, config
  for cadence per display model.
- **Lift:** M · **Status:** planned · **Added:** Round 2 (2026-09-24)

---

## Batch I — Sensors, radio & system

### P40 — Multi-Adapter Role Manager  `multi_adapter`
- **Purpose:** with two or more Wi-Fi adapters, cleanly assign roles (one monitor, one
  uplink) and keep them from stepping on each other; surface which adapter has which role.
- **Gap:** dual-adapter setups are common but role assignment is manual and fragile.
- **Hooks:** `on_loaded` (enumerate/assign), `on_wifi_update`, UI role line, web control.
  **HW:** 2+ Wi-Fi adapters.
- **Lift:** L · **Status:** planned · **Added:** Round 3 (2026-09-24)

### P41 — Auto-Timezone from GPS  `auto_timezone`
- **Purpose:** set the system timezone from the current GPS location so timestamps and
  time-of-day features stay correct while traveling.
- **Gap:** no plugin syncs TZ to location; travelling units log in the wrong local time.
- **Hooks:** `on_epoch` (check fix, resolve TZ, apply), config for manual override.
  **HW/Dep:** GPS + offline lat/lon→TZ lookup.
- **Lift:** S · **Status:** planned · **Added:** Round 3 (2026-09-24)

### P44 — Environmental Sensor Logger  `env_sensors`
- **Purpose:** log real ambient conditions (temperature, humidity, pressure, gas/air
  quality, lux) from attached sensors — actual field weather, not CPU temp. Support
  **multiple sensor types** behind one driver interface (e.g. BME280/BME680, DHT22,
  SHT31, TSL2591), each toggled and addressed in config.
- **Gap:** `memtemp` reads the SoC only; nothing logs the surrounding environment, and no
  plugin abstracts several sensor chips under one config.
- **Hooks:** `on_epoch` (sample enabled sensors), UI readout, web trend, config selecting
  sensor type(s), I2C address, and sample cadence per sensor. **HW:** I2C sensors.
- **Lift:** L · **Status:** planned · **Added:** Round 3 (2026-09-24)

### P45 — Ambient Light Auto-Dim  `auto_dim`
- **Purpose:** dim or blank the display based on measured ambient light (or fall back to
  a time schedule) to save power and reduce glare.
- **Gap:** brightness is static; no light-reactive control exists.
- **Hooks:** `on_ui_update`/`on_epoch` (read lux, adjust backlight), config for thresholds
  and time fallback. **HW:** light sensor (optional; time fallback otherwise).
- **Lift:** M · **Status:** planned · **Added:** Round 3 (2026-09-24)

---

## Cross-cutting decisions to iron out (applies to most plugins)
- Shared storage location & format (SQLite vs JSON) under `/etc/pwnagotchi/` vs
  `/var/lib/`.
- **Per-plugin config:** Pwnagotchi merges plugin settings into the single
  `/etc/pwnagotchi/config.toml` under `main.plugins.<name>.*`. Each plugin ships its own
  documented example config snippet (a `config.toml` block with sane defaults) beside its
  source, which the installer/user pastes into the main file. We keep one example per
  plugin so options are discoverable and copy-pasteable.
- Common UI placement conventions so plugins don't collide on the small display.
- A shared, optional notifier seam (so P06/P07/P35 etc. can push via one path).
- Packaging: one repo of independent plugins vs a small shared support module.
- Test strategy: non-Pi unit tests with fake adapters + a target-Pi validation checklist.

---

_Brainstorm refs map to the working idea list from planning chat. Additional plugin
ideas beyond this locked set are tracked separately as they're proposed._
