# Beast Recon Suite — design notes & proposals

_Proposed 2026-10-06; expanded with the full idea set and organized into automatic tool-chains. Status: notes only, nothing built yet. For patrickato/test-plugins (idea backlog) → graduate approved pieces to plugins-wip._

**Scope (non-negotiable, same as the rest of the project):** every capture/crack piece operates only on networks you own or have written authorization to test. All detector / DF / recon pieces are passive, receive-only. Per repo policy, nothing here is approved for building without an explicit per-item decision.

**Data rule (baked in):** every map/plot is driven by real captured data. A sample dataset may ship only as a clearly-labeled placeholder until real data loads — never presented as real, never mixed into real output.

**Selection status (2026-10-06):** pursuing the original six suite tools + the full list below. Explicitly flagged by the user to pursue: **#1 RF Fusion, #2 rtl_433 decoder, #12 wpa-sec integration.** #9 is optional (user's call). #13 reclassified (see below). #17 merged into the spine (it was the view half of #1).

---

## The spine — build once, everything else is a view or a feeder

- **BeastSpatialDB** — one SQLite store of "sightings": `(kind, id, ssid/name, channel/freq, rssi, lat, lon, bearing, first_seen, last_seen, meta_json)`. `kind` = ap | client | capture | attack_event | tracker | rf_emitter. Every tool writes here.
- **BeastPlot** — the offline true-distance plot/map engine from the wardrive map. Every "map"/timeline/radar below is a filtered query against the DB rendered by BeastPlot. (**Absorbs old #17 "fusion timeline"** — that was just this, showing all `kind`s on one scrubber.)
- **DF capability** — shared RSSI-over-movement + GPS direction-finding math. Used by the maps, the attacker locator, and the tracker locator; built once, not three times.
- **Alert bus** — one internal pub/sub. Detectors publish; outputs (screen, Discord, TTS, log) subscribe. Lets detection auto-trigger capture + notification without each plugin wiring its own.

---

## Automatic tool-chains (the "combine" answer)

Several of these are weak alone and strong when they fire each other. Grouped so each chain runs hands-off once armed.

### Chain A — Capture → Crack *(authorized / own nets only)*
Auto-flow: **handshake captured → Triage scores it → crackable ones queue → Crack runs → results flip the map + CrackHouse.**
- **CaptureTriageNG** — scores each capture crackable/partial/junk, dedupes, GPS-tags. *Good:* stop wasting GPU on dead captures. *Bad:* an efficiency multiplier for cracking if aimed off-scope.
- **CrackPipelineNG** — queues triaged captures to hashcat on the Pi5/PC, tracks status, writes back. Wrapper around hashcat, not a new cracker. *Good:* the whole chain automated, Pi4 offloaded. *Bad:* a turnkey WiFi-breaking line if pointed at others' nets.
- **Wordlist/Ruleset Manager (#11)** — crack backend: organizes dictionaries/rules. *Good:* sharper cracking of your own. *Bad:* same accelerant off-scope.
- **wpa-sec integration (#12)** *(selected)* — submit your own handshakes to distributed cracking. *Good:* crack your own far faster. *Bad:* submitting others' captures leaks their data and facilitates unauthorized cracking.
- **CaptureMapNG** — BeastPlot view of captures by location, colored by crack status. Prior art: `webgpsmap` (online tiles); ours is offline + crack-aware. *Bad:* a geolocated "nets I can get into" map.

### Chain B — Recon Enrichment (one engine, not five plugins)
Auto-flow: **every AP/client sighting in the DB gets auto-enriched the moment it's seen.** Instead of five separate plugins, one pass that attaches:
- **Vendor + fingerprint (#8)** — OUI → make, plus behavioral IE/rate fingerprint that sees through MAC randomization. *Good:* instant inventory, step one of any assessment. *Bad:* device-profiling of people, re-identifying randomized MACs.
- **Probe-request / PNL (#5)** — the networks each device keeps calling for. *Good:* the clearest lesson in how WiFi use leaks you. *Bad:* a PNL is a travel history → deanonymization.
- **Presence timeline (#6)** — first/last/when-present per device. *Good:* learn your baseline, flag a lingering unknown. *Bad:* movement/presence surveillance of passers-by.
- **Hidden-SSID resolver (#9)** *(optional)* — recovers cloaked SSIDs passively. *Good:* proves hiding an SSID buys ~nothing; fills the map's blank column. *Bad:* de-cloaking others' hidden nets is recon.
- **Crypto posture (#10)** — rates each AP's WPA2/WPA3/PMF. *Good:* audit your own hardening. *Bad:* a "who's soft" list if aimed outward.

### Chain C — Multi-radio spatial ingest
Auto-flow: **every radio writes geo-tagged sightings → DB → BeastPlot.** The feeders for the whole map.
- **RF Fusion (#1)** *(selected)* — bridge the HackRF/SDR so WiFi, BT, sub-GHz share one timeline. *Good:* multi-radio awareness almost nobody has. *Bad:* ambient RF logging captures others' devices/sensors.
- **rtl_433 decoder (#2)** *(selected)* — decode 433/915 MHz sensors. *Good:* read your own sensors, deep protocol-RE learning. *Bad:* reads neighbors' sensors — TPMS → vehicle tracking, etc.
- **ADS-B / AIS (#3)** — planes/boats overhead. *Good:* legal RX, real antenna project, fun. *Bad:* aggregated tracking of specific private craft.
- **Spectrum waterfall (#4)** — live congestion/interference on the TFT. *Good:* see the RF world. *Bad:* mostly benign; helps locate emitters.
- **DFMapNG** — RSSI-over-movement + GPS → bearing on the plot. *Good:* "it's that way, ~N m." *Bad:* DF locates any transmitter — the people-tracking edge is inherent.

### Chain D — Defense / IDS (detection auto-triggers capture + alert)
Auto-flow: **Attack Source Locator sees/classifies/locates an attack → auto-fires the forensics recorder → baseline + LAN + proximity detectors all publish to the alert bus → everything paints on the timeline.** This is the headline combine.
- **AttackSourceLocatorNG** — passively detects deauth/flood/spam/evil-twin, IDs source MAC, locates via DF, live radar. *Good:* who/what/where in real time. *Bad:* the classifier read backwards is a spec for generating those attacks; DF half is a people-finder.
- **Attack Replay-Forensics recorder (#16)** — on a detected attack, auto-dumps the raw frames to a timestamped pcap. *Good:* real DFIR; learn attacks by reading real ones; evidence. *Bad:* a clean frame recording is a template to replay the attack.
- **Airspace baseline / anomaly (#7)** — learns normal, flags deviations. *Good:* early warning something changed. *Bad:* the "normal" is a pattern-of-life of nearby people.
- **Rogue-DHCP / ARP-spoof detector (#14)** *(your LAN)* — catches MITM on your own network. *Good:* spot poisoning. *Bad:* the detection logic describes how the attack runs.
- **"Parked outside" alerting (#15)** — warns when a new device camps nearby. *Good:* real physical early-warning for a rural spot. *Bad:* surveils everyone passing to do it.

### Chain E — Tracker watch
Auto-flow: **BLE tracker keeps reappearing near you → locate via DF → alert bus.**
- **TrackerLocatorNG** — flags AirTag/Tile/SmartTag/find-my beacons, logs, locates. Prior art: Apple Tracker Detect, AirGuard; ours is cross-vendor + always-on + locates. *Bad:* the signature DB also finds/pulls someone's legit tracker, or dodges detection.

### Chain F — Unattended ops & output
Auto-flow: **Scheduled survey runs A/B/C hands-off → auto-report → signed.**
- **Scheduled survey + auto-report (#20)** — timed passive sweeps into a clean report. *Good:* pro habit, real portfolio output. *Bad:* continuous outward aggregation is surveillance over time.
- **Tamper-evident log signer (#22)** — cryptographically signs session logs. *Good:* court-grade integrity. *Bad:* negligible.
- **Capture black-box recorder (#13)** *(reclassified clean)* — timestamped metadata+events of the run. Storing public beacon **metadata** is not a problem; the only downside is if it ever logs probe identifiers or frame contents, so it stays metadata+events only. *Bad:* none meaningful as scoped.
- **Field endurance optimizer (#18)** — throttle-aware power/thermal for long runs. *Good:* more field time. *Bad:* negligible.
- **TTS alerts (#21)** — spoken callouts (an alert-bus output). *Good:* hands-free. *Bad:* negligible.

### Standalone utility (no chain)
- **Property coverage heatmap (#19)** — walk your land, map your own WiFi dead zones. *Good:* clean sysadmin survey. *Bad:* ~none.

---

## Build order (respects the spine + selections)

1. **Spine** — BeastSpatialDB + BeastPlot + alert bus + DF capability.
2. **Chain C feeders #1, #2** (selected) — first real data into the DB.
3. **Chain B enrichment** — cheap, makes every map richer immediately.
4. **Chain A** capture→crack (incl. #11, #12).
5. **Chain D** defense (locator → #16 → alert bus).
6. **Chain E** tracker, **Chain F** ops, **#19** utility.

## Repo / workflow

- This doc is the idea backlog for the suite (top-level, linked from README). Nothing is approved to build without an explicit per-item go; the selections above authorize the listed items only.
- Builds land in `patrickato/plugins-wip` as suites (spine first, as shared deps), following `CONVENTIONS.md`.
- Offensive-policy note: none of these are deauth/jam/targeting tools; the closest, AttackSourceLocator, is detection + passive DF, not targeting. No allowlist gate needed, but all stay passive/authorized as stated.
