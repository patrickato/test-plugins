# Plugin Upgrade Proposals

This folder is separate from `pwnagotchi-plugins/` on purpose. Nothing
here is installed, functional, or approved for build yet - these are
planning documents only: scope, design notes, and a proposed
`config.toml` for a plugin upgrade that's been discussed but not
greenlit.

**Nothing in `pwnagotchi-plugins/`, `release/`, or any existing file in
this repo gets edited, overwritten, or deleted by anything placed
here.** This folder only ever grows by addition - new cluster folders,
new proposal folders inside them. If a proposal is later approved and
built, the resulting plugin goes into `pwnagotchi-plugins/<name>/` as
its own new folder, same as every other plugin in this repo - it does
not retroactively rewrite anything in this planning folder either.
Old proposals stay as a record even after being built or abandoned,
until a manual cleanup pass decides otherwise.

This is meant to be a workspace any AI assistant (or human) can pick
up and continue - not just a single-session scratch space. Each
proposal document is written to stand alone: enough context to pick
up cold, no dependency on remembering a prior conversation.

## Structure

```
plugin-upgrade-proposals/
  README.md                          <- this file
  cluster-NN-<short-name>/            <- one folder per elimination-list duplicate cluster
    <plugin>-upgrade/
      PLAN.md                         <- scope, design, rationale
      config-example.toml             <- proposed config, not yet wired to real code
```

## Status key (used inside each PLAN.md)

| Status | Meaning |
|---|---|
| `PROPOSED` | Scope/design written, not approved to build |
| `APPROVED` | User signed off, not yet built |
| `BUILT` | Code exists - see `pwnagotchi-plugins/<name>/` for the real plugin |
| `ABANDONED` | Decided against, kept for the record |

## Index

### Cluster 2 - aggressive/instant-attack mode

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 14 (all three
kept on the master list; these are upgrade proposals discussed
alongside that decision, not replacements pulled from the list).

| Proposal | Target plugin | Status |
|---|---|---|
| [`hulk-upgrade`](cluster-02-aggressive-attack-mode/hulk-upgrade/PLAN.md) | `hulk.py` | PROPOSED |
| [`instattack-upgrade`](cluster-02-aggressive-attack-mode/instattack-upgrade/PLAN.md) | `instattack.py` | PROPOSED |
| [`probenpwn-upgrade`](cluster-02-aggressive-attack-mode/probenpwn-upgrade/PLAN.md) | `probenpwn.py` | PROPOSED |

### Cluster 3 - auto-authenticate + recon on known networks

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Groups 15-16. A
verification pass on this cluster found `educational-purposes-only.py`
and `woop_woop.py` both fail to load on this image outright (dead
top-level import of a module removed from this fork's AI/RL layer);
`hp_educational-purposes.py` was removed from the master list entirely
(functionally inert on both its claimed features, needs a rebuild not
a tweak); `educational-purposes-exclusively.py` already works. See
Group 15/16 in the master list's elimination log for full findings on
all four plugins in this cluster.

| Proposal | Target plugin | Status |
|---|---|---|
| [`educational-purposes-only-upgrade`](cluster-03-auto-authenticate-recon/educational-purposes-only-upgrade/PLAN.md) | `educational-purposes-only.py` | PROPOSED |
| [`woop-woop-upgrade`](cluster-03-auto-authenticate-recon/woop-woop-upgrade/PLAN.md) | `woop_woop.py` | PROPOSED |
| [`educational-purposes-exclusively-notes`](cluster-03-auto-authenticate-recon/educational-purposes-exclusively-notes/NOTES.md) | `educational-purposes-exclusively.py` | KEPT AS-IS - notes only |
| [`hp_educational-purposes-removed`](cluster-03-auto-authenticate-recon/hp_educational-purposes-removed/NOTES.md) | `hp_educational-purposes.py` | REMOVED - record only |

### Cluster 5 - pcap→hash conversion

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 18. A fourth
plugin (`hashie_ng.py`, co-authored by jayofelony himself) was found
during this cluster's review and added to the master list. All three
plugins in this cluster share one bug (documented once, applies to
all): their live conversion path works fine, but their startup
backlog-scan filters for `.pcap` only and never matches this image's
`.pcapng` files.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`shared batch-scan pcapng fix`](cluster-05-pcap-hash-conversion/NOTES.md) | `hashie-hcxpcapngtool.py`, `hashieclean.py`, `hashie_ng.py` | KEPT AS-IS - documented fix, low priority |

### Cluster 6 - cloud-crack-upload destinations

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 19. 7 of 8
plugins in this cluster are completely non-functional on this image -
same `.pcap`-only filter bug as Cluster 5, but here it's the plugin's
only trigger, not a secondary path. All share one fix. One plugin
(`pwn2crack.py`) already works correctly and needs nothing.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`shared upload-trigger pcapng fix`](cluster-06-cloud-crack-upload/NOTES.md) | `banthex.py`, `banthex-de.py`, `better_onlinehashcrack.py`, `dropbox_ul.py`, `hashespwnagotchi.py`, `nextcloud.py`, `wpa-cracking-project-with-pwnagotchi` | KEPT AS-IS - documented fix, low priority (+ extra whitelist flag on hashespwnagotchi.py) |

### Cluster 7 - cracked-password display/export

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 20. All three
plugins kept. `display-password.py` and `display-password-qr.py` are
near-copies of `mycracked_pw.py` missing three imports (`qrcode`,
`csv`, `io`), which breaks their copy-pasted QR/wordlist code with an
uncaught `NameError` - but their actual advertised on-screen
cracked-password display works fine independently via a separate
shell one-liner. `mycracked_pw.py` itself works correctly (minor
staleness quirk only). `display-password-qr.py`'s name is misleading:
it never actually renders a QR code on-device.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`shared missing-imports fix`](cluster-07-cracked-password-display/NOTES.md) | `display-password.py`, `display-password-qr.py`, `mycracked_pw.py` | KEPT AS-IS - documented fix, low priority |

### Cluster 8 - GPS/location status plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 21. All 10
kept. `gps-plus.py` fits the user's actual USB GPS hardware (u-blox 7
dongle, puck receiver, GPS sensor) but shares a `.pcap`/`.gps.json`
filename-mangling bug on this image's `.pcapng` captures with
`gpsdeasy.py` and `mygps.py` - one documented fix applies to all
three. `gps_error.py`/`gps_fix.py`/`gps_grid.py`/`gps_live.py`/
`gps_sat.py` are lightweight status add-ons dependent on a plugin
registered as `"gps"` (open question whether `gps-plus.py` satisfies
that). `gps_led.py` needs an LED wired to GPIO 26. `gsmfake.py` isn't
a real plugin (no `plugins.Plugin` subclass) and will likely log an
ImportError on every boot - kept per user decision, flagged as a real
cost rather than harmless dead weight.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`GPS status cluster notes`](cluster-08-gps-status/NOTES.md) | `gps-plus.py`, `gps_error.py`, `gps_sat.py`, `gps_fix.py`, `gps_grid.py`, `gps_led.py`, `gps_live.py`, `gpsdeasy.py`, `gsmfake.py`, `mygps.py` | ALL 10 KEPT AS-IS - documented fixes/flags, low priority |

### Cluster 9 - wardriving / WiGLE plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 22. All 10
kept. 3 confirmed broken as shipped with fixes documented:
`f0xtr0t` (fatal `.pcap`-only map scan), `Pwnagotchi-JSON-to-Wigle-CSV.py`
(not a real plugin, unconditional `sys.exit()` at import time - real
crash risk if the loader ever imports it), `wardrive.py` (missing
`import os`, guaranteed `NameError` on load). `pwnagotchi_GPSD-ng`
shares the known `.pcap`/`.pcapng` bug pattern (fix documented).
`snoopr.py`, `theylive.py`, `wardriver-pwnagotchi-plugin`,
`warwalking_trails_kml_single.py`, `WigleLocator` are clean.
`theylive.py` is notably a strictly-better, already-`.pcapng`-fixed
alternative to Cluster 8's `gpsdeasy.py`.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`wardriving/WiGLE cluster notes`](cluster-09-wardriving-wigle/NOTES.md) | `f0xtr0t`, `Pwnagotchi-JSON-to-Wigle-CSV.py`, `pwnagotchi_GPSD-ng`, `snoopr.py`, `theylive.py`, `tracker.py`, `wardrive.py`, `wardriver-pwnagotchi-plugin`, `warwalking_trails_kml.py`/`_single.py`, `WigleLocator` | ALL 10 KEPT AS-IS - 3 documented fixes for broken plugins, 1 documented fix for a shared bug, rest clean/noted |

### Cluster 10 - aircraft tracking

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 23. All 3
kept, not duplicates. `skyhigh.py` is clean (no RTL-SDR needed,
internet/OpenSky API only). `adsbsniffer.py` sets its defaults as an
instance dict instead of class-level `__defaults__` - likely
`KeyError`s in `on_loaded()` as shipped. `pwnaware.py` has a fatal
`on_loaded()` bug (f-string mixed with `%`-formatting against a dict)
plus two undefined-variable bugs in less-common paths. Both fixes
documented (user owns multiple RTL-SDR dongles, so directly relevant).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`aircraft tracking cluster notes`](cluster-10-aircraft-tracking/NOTES.md) | `adsbsniffer.py`, `pwnaware.py`, `skyhigh.py` | ALL 3 KEPT AS-IS - documented fixes for 2, clean for 1 |

### Cluster 11 - clock / time-sync plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 24. Removed
`clock_wav_v3.py` (redundant with `clock.py`, and only builds its UI
on Waveshare v3 screens - broken/erroring on the user's MPI3501 TFT).
Kept `clock.py` (clean, works on any screen), `rtc_grid.py` (needs a
physical I2C RTC module the user doesn't have, safe dormant), and
`RaspiSyncedTime.py` (not a real plugin, but unlike other misfiled
scripts in this project it has no risky top-level code - harmless).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`clock/time-sync cluster notes`](cluster-11-clock-timesync/NOTES.md) | `clock.py`, `clock_wav_v3.py` (removed), `rtc_grid.py`, `RaspiSyncedTime.py` | 3 KEPT AS-IS, 1 REMOVED (redundant + broken on user's hardware) |

### Cluster 12 - dashboard plugins (removed)

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 25. Both
`dashboard.py` and `dashboard2.py` removed per user decision.
`dashboard.py` hard-requires a Pivoyager UPS/RTC hat (crashes on load
without one). `dashboard2.py` has a leftover dead call to an
undefined method - crashes every UI refresh cycle. Neither worked out
of the box on this build.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`dashboard cluster notes`](cluster-12-dashboard/NOTES.md) | `dashboard.py`, `dashboard2.py` | REMOVED - record only |

---
*Started by Claude Sonnet 5 · 2026-09-28 · open for any AI or human to continue*
