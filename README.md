# Pwnagotchi Plugin / Helper R&D

This repository is the experimental staging area for **Jayofelony Pwnagotchi**
plugins, helpers, diagnostics and integration ideas.

It is intentionally separate from Beastagotchi.

## Purpose

Use this repo to explore gaps that can improve Pwnagotchi itself, especially:

- diagnostics and triage;
- configuration validation;
- connectivity troubleshooting;
- display/touch troubleshooting;
- radio/monitor health;
- plugin dependency health;
- storage/SD-card early warning;
- backup verification and recovery;
- support bundles;
- exact framebuffer mirroring;
- contextual help/runbooks;
- safe update preflight;
- hardware inventory.

Useful work may later be adapted into Beastagotchi through its Signal/Event/
Action/Capability contracts. A Pwnagotchi plugin does not need to become a Beast
feature to be worthwhile.

## Current idea backlog

See:

- [PWNAGOTCHI_GAP_AND_PLUGIN_IDEAS_2026-09-24.md](PWNAGOTCHI_GAP_AND_PLUGIN_IDEAS_2026-09-24.md)
- [OFFENSIVE_BLUETOOTH_IDEAS_2026-09-29.md](OFFENSIVE_BLUETOOTH_IDEAS_2026-09-29.md) - offensive/defensive Bluetooth plugin ideas, from the Cluster 37 (Hardware-specific) review
- [BEAST_RECON_SUITE_PROPOSAL_2026-10-06.md](BEAST_RECON_SUITE_PROPOSAL_2026-10-06.md) - capture→crack pipeline, GPS/RSSI maps, attacker-source locator, tracker locator (shared BeastSpatialDB + BeastPlot spine); passive/authorized-only, nothing built yet

## Development principles

- Target the current Jayofelony image first unless an experiment states otherwise.
- Prefer read-only diagnosis before automatic repair.
- Never hide mutations from the user.
- Preserve config before changing it.
- Keep plugins independently disableable/removable.
- Avoid unnecessary duplicate polling.
- Reuse existing Linux/Pwnagotchi services and libraries where practical.
- Record exact image/Pwnagotchi/kernel/hardware versions during testing.
- Separate source/off-screen testing from real-device validation.
- Keep experimental code clearly labeled until physically validated.
