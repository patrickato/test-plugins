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

## `reference-configs/` - real upstream config for every tracked plugin

[`reference-configs/`](reference-configs/) holds one real config file per
plugin still tracked in `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`
(everything not already removed) - fetched from whichever source repo
actually ships it (any format: `.toml`, `.yml`/`.yaml`, `.json`), or
built from the plugin's own Python source (`__defaults__` dict, or a
scan of its `self.options` usage) when no shipped sample exists. See
[`reference-configs/MANIFEST.md`](reference-configs/MANIFEST.md) for the
full per-plugin breakdown and what each status tag means. Any real
API key/token/password found in an upstream sample was redacted before
being copied here. The 5 plugins already moved to `plugins-wip` are not
duplicated here - their configs live in their own suites.

## Status key (used inside each PLAN.md)

| Status | Meaning |
|---|---|
| `PROPOSED` | Scope/design written, not approved to build |
| `APPROVED` | User signed off, not yet built |
| `BUILT` | Code exists - see `pwnagotchi-plugins/<name>/` for the real plugin |
| `ABANDONED` | Decided against, kept for the record |

## Standing correction: `__defaults__` is never read on this fork

While researching Cluster 18 (Bluetooth plugins), I read this
jayofelony fork's actual plugin loader
(`pwnagotchi/plugins/__init__.py`, `load()`) directly and confirmed it
never merges a plugin's class-level `__defaults__` attribute - it
assigns `plugin.options` straight from `config['main']['plugins'][name]`
(the user's own `config.toml` section, or `{}` if none exists). A
grep of this fork's entire core source turns up zero references to
`__defaults__` anywhere. Every earlier cluster's "missing
`__defaults__`" finding (Cluster 10's `adsbsniffer.py`, Cluster 12's
removed `dashboard.py`/`dashboard2.py`, Cluster 13's `rss_voice.py`,
Cluster 16's `expv2.py`/`xp.py`, Cluster 17's `age.py`/`agev2.py`)
recommended "add a `__defaults__` block" as the fix - that
recommendation does not actually work on this fork and has been
corrected in each cluster's own NOTES.md (look for "CORRECTED FIX" or
"Correction" callouts). The real fix on this build is either setting
every option explicitly in `config.toml`, or patching the plugin to
use `self.options.get(key, fallback)` instead of indexing
`self.options[key]` directly - the pattern `xp_grid.py` (Cluster 16)
and `git_backup.py` (Cluster 15) already happen to use. No plugin's
keep/remove status changes because of this correction, only the fix
text.

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

### Cluster 6 - cloud-crack-upload destinations (revisited in Cluster 31)

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 19, revisited
in Group 46. Originally 7 of 8 plugins in this cluster were found
completely non-functional on this image (same `.pcap`-only filter bug
as Cluster 5, but here it's the plugin's only trigger, not a secondary
path) and all 8 were kept pending a shared one-line fix. A closer
per-plugin pass in Cluster 31 removed 3 of the 8 outright (each had its
own additional, more serious bug beyond the shared one), found a real
command-injection security concern in `hashespwnagotchi.py`, then fixed
and moved both survivors (`banthex-de.py`, `hashespwnagotchi.py`) to
`plugins-wip`.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`cloud-crack-upload cluster notes`](cluster-06-cloud-crack-upload/NOTES.md) | `banthex.py`, `banthex-de.py`, `better_onlinehashcrack.py`, `dropbox_ul.py`, `hashespwnagotchi.py`, `nextcloud.py`, `wpa-cracking-project-with-pwnagotchi`, `pwn2crack.py` | 3 REMOVED (`banthex.py`, `dropbox_ul.py`, `nextcloud.py`); `banthex-de.py` -> `plugins-wip:banthex-suite/` (`BanthexNG`), `hashespwnagotchi.py` -> `plugins-wip:hashespwnagotchi-suite/` (`HashesPwnagotchiNG`, security issue fixed) - both IN PROGRESS, not yet tested on real hardware; `better_onlinehashcrack.py`/`wpa-cracking-project-with-pwnagotchi` KEPT AS-IS untouched this pass; `pwn2crack.py` already works, no fix needed |

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

### Cluster 13 - TTS / voice plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 26. Removed
`pwnassistant.py` (not a real plugin - module-level infinite
microphone-listening loop, would hang the whole agent forever if ever
imported) and `voice_gamer.py` (downloads and `sudo cp`s an
unvalidated URL over pwnagotchi's own core `voice.py` module - a real
security anti-pattern, plus missing `import logging` and a broken
`on_unload` signature). Kept `pwnspeaker.py` (comprehensively broken
as shipped - nearly every hook concatenates a string with a
non-string value, plus points at a 32-bit-only `pico2wave` package -
needs a real rewrite but the underlying approach is sound), `rss_voice.py`
(works correctly - not actually audio, replaces on-screen status text;
one documented default-shape gap), and `speak_to_me.py` (clean,
modern `espeak-ng`-based, best-built of the five).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`TTS/voice cluster notes`](cluster-13-tts-voice/NOTES.md) | `pwnassistant.py` (removed), `pwnspeaker.py`, `rss_voice.py`, `speak_to_me.py`, `voice_gamer.py` (removed) | 2 REMOVED, 3 KEPT (1 documented as needing a real rewrite, 2 clean) |

### Cluster 14 - fake-AP plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 27. Removed
`apfaker.py` - diffed line-for-line against `better_apfaker.py`,
confirmed exact functional duplicate (only a class-name difference
and one dead config key). Kept `better_apfaker.py`, flagged a real
architecture concern: its `on_ready()` runs an unbounded transmit
loop directly in that synchronous startup hook instead of a spawned
thread - likely blocks the whole agent main loop while active. Fix
(spawn a thread) documented, not applied.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`fake-AP cluster notes`](cluster-14-fake-ap/NOTES.md) | `apfaker.py` (removed), `better_apfaker.py` | 1 REMOVED (exact duplicate), 1 KEPT AS-IS - documented fix for blocking main-loop risk |

### Cluster 15 - backup plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 28. Removed
`auto_backup_ng.py` - diffed against its unmodified original
(dadav's `auto_backup.py`) and confirmed to be a cosmetic rename with
no retention/garbage-collection logic at all (corrects a prior
master-list description inaccuracy), always overwriting a single
fixed archive filename. `AutoBackup v2.0` (wpa-2) does the identical
local-tar job strictly better - timestamped archives, real retention
with auto-pruning, disk-full self-healing, include/exclude lists, a
background scheduler thread, a manual-trigger webhook page - so it
was kept and `auto_backup_ng.py` removed as a strictly-inferior
duplicate. `GitHub_Backups` (wpa-2) was also kept - the only one of
the three that pushes a copy off-device (force-pushed to GitHub/
Gitea over SSH), so it's complementary rather than redundant. One
architecture note flagged for `GitHub_Backups`: its backup routine
runs synchronously inside `on_internet_available` rather than in a
spawned thread, so a slow SSH push could briefly block that hook -
documented, not fixed, and less severe than Cluster 14's finding
since it's a bounded, cooldown-gated operation rather than an
unbounded loop.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`backup cluster notes`](cluster-15-backup/NOTES.md) | `auto_backup_ng.py` (removed), `AutoBackup v2.0`, `GitHub_Backups` | 1 REMOVED (strictly-inferior duplicate), 2 KEPT (both clean, 1 documented threading note) |

### Cluster 16 - XP/leveling plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 29. Removed
`exp.py` - diffed line-for-line against `Experience-Plugin-Pwnagotchi`
(the unmirrored upstream) and confirmed an exact functional duplicate.
Removed `Experience-Plugin-Pwnagotchi` too, same duplicate-mirror
reasoning as earlier Discord/Telegram/fake-AP removals. Kept
`expv2.py` (a strict superset of `exp.py`, adding a Strength stat) -
documented two inherited bugs: a missing-`__defaults__` gap for its
UI-position options, and an `==`-vs-`=` typo in legacy-save migration
that silently drops saved level/total-XP. Kept `xp.py` and
`xp_grid.py` - a separate, more developed leveling system (ranks,
face-glyph changes, a webhook dashboard, peer level-sharing);
documented its own missing-`__defaults__` gap plus a permanent 4x
XP-rate penalty baked in by a dead `on_ai_ready` dependency on this
fork.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`XP/leveling cluster notes`](cluster-16-xp-leveling/NOTES.md) | `exp.py` (removed), `Experience-Plugin-Pwnagotchi` (removed), `expv2.py`, `xp.py`, `xp_grid.py` | 2 REMOVED (exact duplicates), 3 KEPT (2 documented gaps on expv2.py, 2 on xp.py, 0 on xp_grid.py) |

### Cluster 17 - age/strength plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 30.
Findings-only, all 3 kept. `age.py` and `agev2.py` (itsdarklikehell/
Kaska) are near-identical four-stat counters (Age/Strength/Access
Points/Deauths); both share a missing-`__defaults__` gap for their
UI-position options, and both update Strength/APs/Deauths only via
the dead `on_ai_training_step` hook, so those three stats are
permanently frozen at 0 on this fork - only Age (wall-clock based)
actually works. `agev2.py` additionally has its own real bug: its Age
UI element is added under the key `"AgeV2"` but `on_ui_update` calls
`ui.set("Age", ...)` - the wrong key - so its Age display is broken
as shipped. The third entry, `age.py` (AlienMajik variant), is a
confirmed-unrelated plugin (filename collision only) - a full
prestige/lore RPG system that avoids the dead-AI-hook trap via a
passive-accrual fallback, correctly handles the `.pcapng` extension,
and reads as the most carefully engineered plugin found in this
project to date.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`age/strength cluster notes`](cluster-17-age-strength/NOTES.md) | `age.py`, `agev2.py`, `age.py` (AlienMajik variant) | 3 KEPT (2 documented gaps shared, 1 additional real bug on agev2.py, AlienMajik variant clean) |

### Cluster 18 - Bluetooth scanning plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 32. Removed
`bluetooth_scanner.py` - confirmed non-functional by construction, not
merely buggy: imports a `BasePlugin` class that doesn't exist in this
or any pwnagotchi version, calls `self.log` (no such attribute),
defines `on_periodic` (not a real hook), and calls
`agent.display_text(...)` (not a real method) - built against an
imagined API. Would need a full rewrite, not a patch. Kept
`blemon_plugin.py` (correctly built BLE monitor integrated with
bettercap's real event stream, one small wrong-UI-key bug) and
`bluetoothsniffer.py` (also correctly framed classic-Bluetooth
scanner, but with three real bugs: a wrong UI-key on unload, a
genuine `UnboundLocalError` risk that can drop a scan's results, and
instance-dict defaults discarded by the loader per the project-wide
`__defaults__` correction below - plus an unconfirmed `hcitool`-
availability compatibility risk on newer Debian Bookworm-based
images).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`Bluetooth cluster notes`](cluster-18-bluetooth/NOTES.md) | `bluetooth_scanner.py` (removed), `blemon_plugin.py`, `bluetoothsniffer.py` | 1 REMOVED (non-functional by construction), 2 KEPT (1 small bug each on blemon_plugin.py, 3 bugs + 1 open question on bluetoothsniffer.py) |

### Cluster 19 - auto-hotspot/connect plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 33. Findings-only,
all 5 kept. Two of the most severe bugs found anywhere in this project
turned up here: `auto-hotspot.py` can't even import on this fork (dead
`pwnagotchi.ai.reward` import - no `pwnagotchi/ai/` module exists here)
and separately has a real infinite-loop hazard in `on_ui_update` (`while`
where `if` was clearly intended, four times); `away_base.py`/`home_base.py`
share a fatal `NameError` in a module-level `_log()` helper that
incorrectly references `self` outside any method scope, plus an
independent `TypeError` from an extra argument passed to
`agent.next_epoch()`. `extWifi.py` (A1buS variant) has an unconditional
reboot loop - both branches of `on_loaded()` fall through to the same
`self.restart_pi()` call, so the device would never stay booted once
enabled - assessed as the single worst bug found in the project to date.
`ext_wifi.py` (itsdarklikehell variant) is milder: missing interface
validation and no restart call after its `sed` edit. All 5 are assessed
as fixable with mechanical patches, no full rewrite needed.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`auto-hotspot/connect cluster notes`](cluster-19-auto-hotspot/NOTES.md) | `auto-hotspot.py`, `away_base.py`, `home_base.py`, `ext_wifi.py`, `extWifi.py` | 5 KEPT (2 fatal-but-fixable bugs on auto-hotspot.py, shared fatal-but-fixable bug + 1 more on away_base.py/home_base.py, 1 active reboot-loop hazard on extWifi.py, 1 minor gap on ext_wifi.py) |

## Newly discovered plugins (Group 34 audit)

A user-requested audit cross-checked every plugin filename in
`itsdarklikehell`, `sniffleupagus`, and `pwnagotchi-unofficial`'s archive
against the master list and found 42 plugins never added at all - see
Group 34 in the master list's elimination log. 23 were selected and
added as new bullets, split into Clusters 20-26 below, reviewed the same
way as everything else.

### Cluster 20 - cracking-pipeline "_ng" rewrites

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 35. Findings-only,
all 6 kept. `aircrackonly_ng.py` is a clean improvement over
`aircrackonly.py` (adds an on-screen delete-notice). `onlinehashcrack_ng.py`
shares `better_onlinehashcrack.py`'s already-documented `.pcap`-only
backlog-scan bug, but uses a possibly-more-current download endpoint and
reads the device's real global whitelist instead of a plugin-scoped
copy. Major finding: neither form of `quick_rides_to_jail` works -
`quick_rides_to_jail.py` has no `class X(plugins.Plugin):` wrapper at
all, so it silently never registers as a plugin (confirmed against this
fork's loader source); `quick_rides_to_jail_ng.py` fixes that
registration but shares a second bug with the original - a module-level
`OPTIONS` dict that's declared but never populated - so it registers and
then `KeyError`s on first real use. The master list's `quick_rides_to_jail.py`
description was corrected in place to reflect this.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`cracking-pipeline _ng cluster notes`](cluster-20-cracking-pipeline-ng/NOTES.md) | `aircrackonly.py`, `aircrackonly_ng.py`, `better_onlinehashcrack.py`, `onlinehashcrack_ng.py`, `quick_rides_to_jail.py`, `quick_rides_to_jail_ng.py` | 6 KEPT (aircrackonly pair clean, onlinehashcrack pair shares a known bug with 2 differences, quick_rides_to_jail pair both non-functional for independent reasons - description corrected) |

### Cluster 21 - LED/wardriving "_ng" rewrites

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 36. Removed
`led.py`, `led-ng.py`, `morse_code.py`, `morse_code-ng.py` (4) - the
`led-ng.py` rewrite had a real regression bug (dropped the "led" prefix
from its sysfs LED path, pointing at a nonexistent device name), and
`morse_code-ng.py` was purely cosmetic with no functional difference
either way. Kept `wardriver-pwnagotchi-plugin`, `wardriver_ng.py`,
`f0xtr0t`, `webgpsmap_ng.py` (4, findings-only). `wardriver_ng.py` is a
real regression against itsdarklikehell's own `wardriver.py` mirror -
drops the on-screen UI and session-merging entirely, and its directory
cleanup lost the file-type filter the original had (a real bug).
`webgpsmap_ng.py` filters `.pcap` throughout its core map-building logic
instead of `.pcapng`, so it never finds this device's real captures -
this fork's own bundled `webgpsmap.py` default already handles this
correctly - but it does add `.paw-gps.json` GPS-source support nothing
else on the list has.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`LED/wardriving _ng cluster notes`](cluster-21-led-wardriving-ng/NOTES.md) | `led.py`/`led-ng.py` (removed), `morse_code.py`/`morse_code-ng.py` (removed), `wardriver-pwnagotchi-plugin`/`wardriver_ng.py` (kept), `f0xtr0t`/`webgpsmap_ng.py` (kept) | 4 REMOVED, 4 KEPT (wardriver_ng.py and webgpsmap_ng.py both real regressions vs. their references, fixes documented) |

### Cluster 22 - cracked-password display mirrors

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 37. Findings-only,
both kept. `show_password.py`/`show_pwd.py` are a third, independent
mirror of Cluster 7's `mycracked_pw.py`/`display-password.py`/
`display-password-qr.py` family, reading a WPA-SEC potfile instead of a
hashcat potfile. `show_password.py` has the recurring missing-defaults
gap on `orientation`; `show_pwd.py` fixes that with a self-populating
default, but changes its `awk` query to dedupe by network before taking
the last line - can show an older crack for a repeat network rather than
the literal most-recent line - and drops the friendly empty-result
fallback message. Neither crashes; both work as shipped.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`password display mirrors cluster notes`](cluster-22-password-display-mirrors/NOTES.md) | `show_password.py`, `show_pwd.py` | 2 KEPT (show_password.py has a missing-defaults gap, show_pwd.py fixes it but changes "most recent" semantics and drops the empty-result fallback) |

### Cluster 23 - Bluetooth tethering

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 38. Removed
`bt-tether_ng.py` - confirmed via direct diff to be byte-for-byte
identical to `bt-tether.py` apart from a renamed class and `__name__`
attribute. Kept `bt-tether.py` - a substantial, well-built plugin with
real defensive per-device option validation rather than bare indexing,
one of the more carefully built plugins found in this audit. One
cosmetic-only issue remains, not fixed: a copy-pasted `__help__` string
from an unrelated plugin.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`Bluetooth tethering cluster notes`](cluster-23-bluetooth-tethering/NOTES.md) | `bt-tether.py` (kept), `bt-tether_ng.py` (removed) | 1 REMOVED (exact duplicate), 1 KEPT (no bugs found, cosmetic __help__ typo only) |

### Cluster 24 - remote/server control

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 39. Removed
`fancyserver.py` - two real bugs (a `NameError` on its error-logging path
from an unused `traceback` import, and an `UnboundLocalError` risk on
`name`/`state` in its "plugin" command branch). Kept `cmd_server.py`
(two real bugs - a `NameError` on a narrow cleanup-failure path, and a
reply-misdirection bug when multiple clients are connected
simultaneously), `console.py` (one cosmetic bug - a broken diagnostic
log line that silently drops its content rather than crashing -
otherwise clean), and `webcfg_ng.py` (no bugs found; its `save-config`
webhook path fully overwrites `config.toml` with no merge safety net,
unlike its own `merge-save-config` path).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`remote/server control cluster notes`](cluster-24-remote-server-control/NOTES.md) | `fancyserver.py` (removed), `cmd_server.py`, `console.py`, `webcfg_ng.py` (all kept) | 1 REMOVED (2 real bugs), 3 KEPT (cmd_server.py has 2 real bugs, console.py has 1 cosmetic bug, webcfg_ng.py clean with a design note) |

### Cluster 25 - memtemp variants

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 40. Findings-only,
both kept alongside the already-listed `memtemp-plus.py`. `memtemp_adv.py`
has a real `NameError` bug - a one-character typo (`y_pos` instead of
`v_pos`) in its waveshare_v3 vertical-orientation fallback position
logic - plus a missing-defaults gap on `scale` even by its own file's
stated intent. `memtemp_ng.py` has no bugs, but its default "cpu" field
calls the framework's own `pwnagotchi.cpu_load()` with no tag, which
sleeps 0.1s internally on every call - a small per-refresh UI-thread
block; a non-blocking alternate field exists in the same file but isn't
the default.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`memtemp variants cluster notes`](cluster-25-memtemp-variants/NOTES.md) | `memtemp_adv.py`, `memtemp_ng.py` | 2 KEPT (memtemp_adv.py has a real NameError bug plus a scale-defaults gap, memtemp_ng.py clean but has a 0.1s UI-blocking design trade-off on its default field) |

### Cluster 26 - misc grab-bag

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 41. Findings-only,
all 6 kept for now. The final cluster spun out of the Group 34 discovery
audit - unlike the others, a genuine grab-bag with no shared lineage.
Two of the more significant findings in the project: `prime_gsm_hat.py`
is not actually a pwnagotchi plugin at all (no `plugins.Plugin` subclass
anywhere - a standalone Python-2-era manual setup script using the
removed `raw_input()` builtin), and `auto-update_ng.py` has four
module-level functions that all reference a nonexistent `self`,
guaranteeing `NameError` and silently disabling its auto-install feature
while detect/notify still works. Also found: `wigle_ng.py` has the
recurring `.pcap`-vs-`.pcapng` bug in its GPS-to-handshake matching;
`wpa-sec-list.py` has an `IndexError` risk on a malformed potfile line;
`wpa-sec_ng.py` turned out to be a completely different plugin than
`wpa-sec-list.py` (an uploader, not a display page) - the master list's
shared description for the two has been corrected and split into two
entries. `auto_tune.py` had no bugs found after extensive review.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`misc grab-bag cluster notes`](cluster-26-misc-grab-bag/NOTES.md) | `wigle_ng.py`, `wpa-sec-list.py`, `wpa-sec_ng.py`, `auto-update_ng.py`, `prime_gsm_hat.py`, `auto_tune.py` | 6 KEPT (wigle_ng.py has the recurring .pcap/.pcapng bug, wpa-sec-list.py has an IndexError risk, wpa-sec_ng.py was misdescribed and shares the Cluster 6 backlog-scan bug, auto-update_ng.py's install feature is silently broken, prime_gsm_hat.py isn't a real plugin at all, auto_tune.py clean) |

## Category-by-category pass (started after Cluster 26)

With the discovery-audit thread (Clusters 20-26) complete, the review
moved to going through the master list's own category sections one at a
time, source-verifying plugins that hadn't been individually reviewed
yet.

### Cluster 27 - attack-mode toggles & AP restriction

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 42. All 3
removed. `cuffs.py` had one low-severity bug (mutates a list while
iterating it, only affecting an internal log count/unused list - real
enforcement was correct) but was removed anyway. `enable_assoc.py`/
`enable_deauth.py` were both clean, but removed once it was confirmed
(via this fork's own `defaults.toml`) that `associate`/`deauth` are
already `true` by default - these plugins only force them back to `True`
on load (redundant) and `False` on unload (a kill-switch, not an
enabler as their descriptions imply).

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`attack-mode toggles cluster notes`](cluster-27-attack-toggles/NOTES.md) | `cuffs.py`, `enable_assoc.py`, `enable_deauth.py` | 3 REMOVED |

### Cluster 28 - Discord hash-dump ecosystem (moved to `plugins-wip`, not kept/removed)

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 43. New
workflow: instead of keep/remove, a plugin can now be marked in progress
and moved into the separate `patrickato/plugins-wip` repo for a full
rebuild (fix, test on real hardware, package with config.toml + README +
setup docs) before graduating to `patrickato/complete-plugins`.
`DiscoHash` and `hashbot.py` (both already on the master list) plus
`discoBoss.py` (pulled in for its direct overlap with `hashbot.py`,
though never formally listed here) are consolidated into two pieces in
the new "DiscoHash Suite": `discohash_ng.py` (pi-side) and a rebuilt
`hashbot.py` (off-pi, now also owns discoBoss's former reboot/poweroff/
status commands). Full research and design-decision writeup in
`plugins-wip:discohash-suite/NOTES.md`; setup walkthrough in
`plugins-wip:discohash-suite/SETUP.md`.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`plugins-wip: discohash-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/discohash-suite/NOTES.md) | `DiscoHash`, `discoBoss.py`, `hashbot.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |

### Cluster 29 - handshake download web-UI plugins

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 44.
`handshakes-dl.py` removed as a redundant subset of
`handshakes-dl-hashie.py` (same author, same `.pcap`-only bug, but the
hashie version also surfaces already-converted `.2500`/`.16800`/`.22000`
hash files per capture). Notably, even jayofelony's own official plugin
repo distributes `handshakes-dl.py` with this same unfixed bug.
`handshakes-dl-hashie.py` moved to `plugins-wip` for a full rebuild.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`handshakes-dl cluster notes`](cluster-29-handshakes-dl/NOTES.md) | `handshakes-dl.py`, `handshakes-dl-hashie.py` | 1 REMOVED (redundant subset), 1 IN PROGRESS - moved to `plugins-wip` |

### Cluster 30 - Attack/Capture: privacy / honeypot / evasion

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 45.
`privacy-nightmare.py` moved to `plugins-wip` for a full rebuild (nine
source-verified bugs fixed, plus a `.gps.json` sidecar, distance filter,
and GPS-conflict-avoidance improvements). `wd_honey_Pot.py` is not
fixable with a patch (same "imagined API" root cause as the
already-removed `bluetooth_scanner.py`) - options presented, decision
deferred. `neurolyzer.py` has no bugs but overlaps `mac_randomizer.py`
over MAC control - both flagged, decision on both deferred.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`plugins-wip: gps-tagger-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/gps-tagger-suite/NOTES.md) | `privacy-nightmare.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`Cluster 30 notes`](cluster-30-privacy-honeypot-evasion/NOTES.md) | `wd_honey_Pot.py`, `neurolyzer.py`, `mac_randomizer.py` | DEFERRED - left on the list, decisions pending |

### Cluster 32 - Attack/Capture: last two unreviewed (mesh control, potfile sorting)

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 48.
`potfilesorter.py` removed - its `on_webhook()` signature can never be
called by the real framework, making its whole advertised feature
unreachable dead code, and it separately contains a bare `exit()` in an
error branch that could have crashed the entire pwnagotchi daemon (raises
`SystemExit`, which the framework's plugin dispatcher does not catch) had
that path ever become reachable. `meshpwnstic.py` (Meshtastic LoRa mesh
remote control) saved for later - functional concept, but ships with no
sender authentication at all on its `/bcap`/`/deauth`/`/assoc`/`/restart`
mesh commands, plus four smaller bugs; flagged as a fix candidate rather
than fixed this pass.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`Cluster 32 notes`](cluster-32-mesh-potfile/NOTES.md) | `potfilesorter.py`, `meshpwnstic.py` | 1 REMOVED (`potfilesorter.py`), 1 SAVED FOR LATER (`meshpwnstic.py`, fix candidate) |

### Cluster 33 - Network / Security analysis

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 49. 9 of 14
plugins (`dns_spoof_detector.py`, `mac_adress_logger.py`,
`mac_randomizer.py`, `network_intrusion_detector.py`,
`network_mapper.py`, `network_packet_sniffer.py`, `rogue_ap_detector.py`,
`traffic_sniffer.py`, `wifi_analyser.py`) removed - all by the same
author ("Deus Dust"), all sharing one fatal defect: `from
pwnagotchi.plugins import BasePlugin`, a class that does not exist
anywhere on this fork, so none of them could ever load. `wifi_jammer.py`
(same fatal defect, plus zero targeting scope in its original design)
was judged worth a real rebuild rather than removal and moved to
`plugins-wip` as `wifi-jammer-suite` (`WifiJammerNG`) - rebuilt around
an `authorized_networks` allowlist that is empty by default and gates
every firing path, using bettercap's own native deauth call instead of
a separate `aireplay-ng` subprocess. `beacons.py` and `test_security.py`
reviewed with real, fixable bugs found, decision deferred.
`beaconify.py` reviewed, no bugs, kept as-is.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`plugins-wip: wifi-jammer-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/wifi-jammer-suite/NOTES.md) | `wifi_jammer.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`Cluster 33 notes`](cluster-33-network-security/NOTES.md) | all 14 plugins in this category | 9 REMOVED, 1 moved to `plugins-wip` (`wifi_jammer.py`), 3 DEFERRED (`beacons.py`, `test_security.py`, `mac_randomizer.py`'s cross-reference on `neurolyzer.py`), 1 KEPT AS-IS (`beaconify.py`) |

### Cluster 34 - Display / UI

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Groups 50-55. First
category-wide pass over Display/UI (19 plugins) - most of this
category had never been reviewed in either the earlier duplicate-cluster
round or the current category-by-category pass. 8 removed: `printp.py`
(explicit example plugin, `KeyError`-crashes on load with no
`__defaults__` fallback), `PwnagotchiCharacterPlugin`/`Pwan-Girl`/
`screen_color_invert` (no locatable source anywhere in the cloned
archives - record only), `Bat-Trinity` (Waveshare 3.7" driver that
imports a module path that doesn't exist on this fork, so it can never
load), `display-text.py` (no-op demo, nothing worth preserving),
`sprite_faces.py` (upstream author's own unfixed, self-flagged bug),
and `screen_refresh.py` (fixed and briefly moved to `plugins-wip` as
`ScreenRefreshNG`, then removed at the user's request - not needed on
a TFT/LCD screen, since its whole purpose is clearing e-ink ghosting).
The remaining 7 fix candidates are fixed/extended and moved to
`plugins-wip`: `internet-connection.py`'s three-way group ->
`internet-connection-suite` (`InternetConnectionNG`), `tweak_view.py`
-> `tweak-view-suite` (`TweakViewNG`), `timer.py` -> `timer-suite`
(`TimerNG`, initially kept as-is, revisited once the user deferred a
set of proposed improvements to this project's judgment),
`crack_house.py` -> `crack-house-suite` (`CrackHouseNG`),
`more_uptime.py` -> `more-uptime-suite` (`MoreUptimeNG`), `viz.py` ->
`viz-suite` (`VizNG`), and `Touch_UI.py` -> `touch-ui-suite`
(`TouchUING`, kept deliberately conservative - it's the plugin tied to
the user's real MPI3501 touchscreen). Several of these turned out to
have crash bugs worse than originally flagged - `crack_house.py`,
`screen_refresh.py`, and `viz.py` all had a guaranteed on-load/on-import
crash on every display type that the first-pass review hadn't caught
(each assumed an API - a `Display`-only method, or an import path -
that simply doesn't exist on this fork). All 7 remaining suites are
built, documented, and sandbox-tested against the real framework; none
tested on real hardware yet. After the initial bug-fix rebuilds, the
user reviewed and approved a further round of specific improvements
for 4 of them: `CrackHouseNG` (case-insensitive matching, cross-reboot
persistence), `MoreUptimeNG` (configurable cycle interval and
state subset/order), `VizNG` (last-updated timestamp, cracked-node
cross-referencing against CrackHouseNG, configurable poll interval),
and `TouchUING` (a real webhook status page, long-press detection) -
see each suite's own NOTES.md for detail. Several more plugins in this
category are kept as-is pending formal confirmation. No plugin in this
batch invented a fake hook name, unlike Cluster 33.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`plugins-wip: internet-connection-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/internet-connection-suite/NOTES.md) | `internet-connection.py`, `wanmon.py`, `internet-conection.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: tweak-view-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/tweak-view-suite/NOTES.md) | `tweak_view.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: timer-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/timer-suite/NOTES.md) | `timer.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: crack-house-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/crack-house-suite/NOTES.md) | `crack_house.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: more-uptime-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/more-uptime-suite/NOTES.md) | `more_uptime.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: viz-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/viz-suite/NOTES.md) | `viz.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`plugins-wip: touch-ui-suite/NOTES.md`](https://github.com/patrickato/plugins-wip/blob/main/touch-ui-suite/NOTES.md) | `Touch_UI.py` | IN PROGRESS - moved to `plugins-wip`, not yet tested on real hardware |
| [`Cluster 34 notes`](cluster-34-display-ui/NOTES.md) | all 19 plugins in this category | 8 REMOVED (including `screen_refresh.py`, removed after review), 7 fix candidates fixed/extended and moved to `plugins-wip`, remaining plugins kept as-is pending formal confirmation |

---
*Started by Claude Sonnet 5 · 2026-09-28 · open for any AI or human to continue*
