# redteam-roadmap — resume point

Long-term store for the user's red-team learning roadmap, so a brand-new chat can
pick up where we left off. **Read this file first**, then `INTERESTS.md`, then
`ATLAS.md`.

## What this is
A guided journey through "all of hacking," built as a personal curriculum for the
user (a cybersecurity student working toward red team engineer, with a home lab —
"the tinker shop"). We map the field, he pegs interests, we go deep topic by
topic, and turn picks into learn+build work.

## Files
- **`ATLAS.md`** — the full field map, every category, handled (A1…LL4).
- **`INTERESTS.md`** — his pegged interests organized into 11 tracks, candidate
  additions awaiting his yes, the agreed discussion order, and his gear list.
- **`godrive-manifest.md`** — the USB-fleet deep-dive's concrete output: a vetted
  "one USB to rule them all" build list (Ventoy NVMe core + tiered ISOs), each with
  official source, version, how-to-verify, and maintained status. Build entry by
  entry, verify each as added.
- **`README.md`** — this resume point.

## The operating agreement (important — carries across sessions)
- Everything we build or run is on **his own gear or explicitly authorized
  targets**. Understand-and-defend is always open; **weaponized artifacts aimed at
  non-consenting third parties are not** built.
- His own principle, which we hold to: *"the user must choose to do wrong... keep
  the friction."* Safe defaults, deliberate authorization, no point-and-shoot
  weapons for use on others.
- He wants tools kept REAL (not test-only neutered) so learning stays honest — fine,
  because the limit is the *target*, not how real/advanced the tool is.
- Sharp personal tooling can live in a **private** repo of his; publication risk ≠
  a different rule set. Privacy doesn't unlock anything that wouldn't be built
  otherwise.

## Current position (update as we go)
- **Roadmap captured** (this folder) on 2026-10-05.
- **Discussion order:** (1) Flipper ✓ done · (2) Tor/dark web ✓ done ·
  (3) USB fleet ← in progress (god-drive manifest started — see `godrive-manifest.md`;
  Ventoy/Medicat/Hiren's verified, next = seed the NVMe core + Tier 1 ISOs) ·
  (4) Kali/BlackArch · (5) revisit list → build+learn plan.
- Tor note: highest-value slices for him = dark-web **threat-intel monitoring**
  (automatable) + a **Tails/Whonix** clean research environment (sketch queued,
  he said yes). Mechanics/OPSEC/onion-services/I2P/Hyphanet all walked.
- Already-built, graduated tooling that feeds these tracks lives in
  `patrickato/complete-plugins`: **badhid-ng** (BadUSB/BadHID, incl. B3 /stage),
  **remoteexec-ng** (remote-exec agent + fleet controller = cross-network control
  seed), **netmanager-ng** (wifi target manager + authorized capture backend).
  Staging in `patrickato/plugins-wip`; BLE wireless BadHID is `badhid-ble-suite`
  (needs on-device BLE bring-up).

## How to resume in a new chat
"Read `redteam-roadmap/` in patrickato/test-plugins and let's continue the
roadmap." Then pick a track/handle or the next queued deep-dive.
