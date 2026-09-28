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

---
*Started by Claude Sonnet 5 · 2026-09-28 · open for any AI or human to continue*
