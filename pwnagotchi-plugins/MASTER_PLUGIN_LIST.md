# Master Plugin List

Everything found across both research rounds, minus jayofelony-bundled
defaults, your own custom plugins, and everything already cut for being
either superseded-by-bundled or (in one case) a pure name/architecture
non-issue. One bullet per plugin, by category, alphabetical within each
category. Ready for the next removal round.

A few plugins are genuinely the same file re-hosted by several people
(this ecosystem re-mirrors constantly) - those are one bullet with the
aliases noted, not one bullet per mirror.

**Status tags:** a bullet with no tag is untouched/kept. **IN PROGRESS,
moved to `plugins-wip`** means the plugin has been pulled into the
separate `patrickato/plugins-wip` repo to be fixed, tested against real
hardware, and fully packaged (plugin + config.toml + README + setup
instructions) - once that's done it graduates to `patrickato/complete-plugins`
and is removed from this list entirely. See `plugins-wip` for
work-in-progress rebuilds and `complete-plugins` for finished ones.

## Elimination log

**Group 48 (Cluster 32 - Attack/Capture, last two unreviewed):**
`potfilesorter.py` removed - its `on_webhook()` signature can never match
the framework's real call, so the entire advertised sort/backup feature
is unreachable dead code; separately, `on_loaded()` calls a nonexistent
`self.load_data()`, `readpotfiledata()` references an undefined
`handshake_dir`, and - most seriously - `copy_config()`'s error branches
call bare `exit()`, which raises `SystemExit`, a `BaseException` the
framework's plugin dispatcher does NOT catch (it only catches
`Exception`) - meaning this could have crashed the whole pwnagotchi
daemon, not just the plugin, had the broken webhook signature ever been
"fixed" without also removing that. `meshpwnstic.py` saved for later -
functional Meshtastic LoRa remote-control concept, but ships with zero
sender authentication on its `/bcap`/`/deauth`/`/assoc`/`/restart`
commands (any device on the mesh can run them) plus four smaller bugs;
fix candidate, not removed. See Cluster 32 notes.

**Group 47 (Cluster 31, continued - fixing what was kept):**
`banthex-de.py` moved to `plugins-wip` as `banthex-suite` (`BanthexNG`) -
the shared `.pcap`/`.pcapng` bug fixed, plus a permanent-skip-on-failure
bug (a single transient upload failure blacklisted a handshake forever)
fixed with bounded retries. `hashespwnagotchi.py` moved to `plugins-wip`
as `hashespwnagotchi-suite` (`HashesPwnagotchiNG`) - the confirmed
command-injection security issue fixed (every `hcxpcapngtool`/`tcpdump`
call now runs via `subprocess.run([...], shell=False)` with a real
argument list, never a shell string, closing the path a maliciously-named
AP could have used to run commands as root), plus a previously-unknown
`on_config_changed` crash bug (`self.status` was never assigned -
setting the `interval` option crashed this method every time, silently
disabling the startup batch-conversion pass), the shared `.pcap` bug, a
Python-2-only `.encode("hex")` call, the already-flagged disabled
whitelist, and the same permanent-skip-on-failure bug as `banthex-de.py`,
all fixed. Full detail in `plugins-wip:banthex-suite/NOTES.md` and
`plugins-wip:hashespwnagotchi-suite/NOTES.md`.

**Group 46 (Cluster 31 - Attack/Capture, cloud-crack-upload destinations,
revisiting Group 19):** `banthex.py` removed - redundant with, and more
buggy than, `banthex-de.py` (which fixes a file-deletion copy/paste bug
`banthex.py` has in its corrupted-state-file recovery path). `dropbox_ul.py`
removed. `nextcloud.py` removed - source review found an additional bug
beyond the shared `.pcap`/`.pcapng` issue: `_make_session()` returns
`False` on bad credentials/URL, but the caller never checks that return
value, guaranteeing an `AttributeError` crash on every internet-available
cycle instead of the clean failure the code intended. `hashespwnagotchi.py`
kept on the list pending a decision - real security concern found and
confirmed this cluster: it shells out via `subprocess.getoutput()` with
Python-string-formatted commands, and this fork's handshake filenames
embed the AP's ESSID (attacker-controlled), creating a real command-
injection risk from a maliciously-named nearby AP; also still has the
`.pcap` batch-scan bug and a disabled whitelist-exclusion call already
flagged back in Group 19. `banthex-de.py` kept, not yet fixed. See
`plugin-upgrade-proposals/cluster-06-cloud-crack-upload/NOTES.md` (updated
this cluster) for full detail.

**Group 45 (Cluster 30 - Attack/Capture, continued):** `privacy-nightmare.py`
moved to `plugins-wip` as `gps-tagger-suite` (renamed `GPSTaggerNG`) - nine
source-verified bugs fixed (see `plugins-wip:gps-tagger-suite/NOTES.md`),
plus the distance-filter/no-GPS-log-limit/manage_gps improvements approved
for this cluster; also fixed two additional bugs found only during the
rebuild (invalid multi-object JSON output files, and a hostname-only
filename collision risk between different APs sharing an SSID).
`wd_honey_Pot.py` - **decision deferred, left on the list**: calls a
nonexistent `self.register_event()` and listens for event names that never
fire on this fork (same "imagined API" class as the already-removed
`bluetooth_scanner.py`), not fixable with a patch; options presented
(full rewrite from scratch / drop entirely / fold a lightweight decoy-AP
feature into another plugin) - revisit later. `neurolyzer.py` -
**decision deferred, left on the list**: well-engineered, no bugs found,
several improvements suggested (per-measure config toggles, a cooldown on
the evasion protocol, on-screen stealth-level display) but not yet built;
flagged as directly overlapping `mac_randomizer.py` (Network/Security
analysis category) over control of the interface's MAC - `mac_randomizer.py`
annotated in place with the same cross-reference; both plugins' fates
will be decided together in a future pass.

**Group 1 - hardware you don't own:** partial pass. Removed the Waveshare
e-paper family (5: `Pwnagotchi_Waveshare_2.66inch`, `Pwnagotchi-on-waveshare-v4`,
`Pwnagotchi-WS-V3-V4`, `Pwnagotchi-Waveshare-V3-Fix`, `waveshare_v3_touch.py` -
you're on the MPI3501 TFT, not e-paper) and the Pimoroni Button Shim/Display
HAT Mini/LCD HAT family (6: `buttonshim.py`, `bshim.py`, `display_settings.py`,
`fireworks.py`, `lcdhat.py`, `lcdhatcontrols.py`). Left in for now: the
UPS/battery-hat group, the RTL-SDR/LoRa/GSM-hat group, the BLE group, the
Flipper Zero group, and the GPIO-button/LED group.

**Group 2 - duplicate/overlapping function:** partial pass. Discord group -
kept `Discord v3.0.1` (wpa-2), dropped `discord.py`, `discord_notify.py`,
`pwng2discord`, `pwnagotchi-discord-plugin` (4). Telegram group - kept
`TelePwn v2.0` (wpa-2), dropped `telegram.py`, `neonbot.py` (2). All other
duplicate groups (GPS, wardriving, TTS/voice, crack pipeline, fake-AP,
cloud-crack-upload, password display, backup, clock, dashboard, XP/leveling,
age/strength, Bluetooth scanning, aircraft tracking, auto-hotspot/connect)
left in for now.

**Group 3 - ethical/legal scope (unscoped active plugins):** no changes -
left in for now (`educational-purposes-exclusively.py`, `educational-purposes-only.py`,
`hp_educational-purposes.py`, `woop_woop.py`, `enterprise.py`, `wifi_jammer.py`,
`wifi_password_cracker.py`, `instattack.py`, `hulk.py`).

**Group 4 - maintenance/activity status:** removed all 7 flagged
(`pwnagotchi-postinstall`, `dontuse.py`, `pwna-template-testing.py`,
`Fancygotchi`, `monstart`/`monstop` counted as one entry, `phwn_hwm.py`).

**Group 5 - category/interest sweep:** no changes - left in for now.

**Group 6 - external dependency burden:** no changes - left in for now.

**Group 7 - cloud-upload destination consolidation:** no changes - left
in for now.

**Group 8 - overlap with your own custom plugins:** no changes - left
in for now.

**Group 9 - trust/provenance tier:** kept everything, including the
~130-plugin Tier 3 (individual one-off repos) - no changes.

**Group 10 - unclear-purpose flags:** removed `deauthenticator.py`
(name/description mismatch, likely a mislabeled duplicate of
`display_version.py`).

**Group 11 - conflict risk:** no changes - left in for now.

**Group 12 - image-compatibility re-check (source-verified):** removed 2.
`hashie.py` - filters for `.pcap` files and shells out to `hcxpcaptool`
(classic-pcap-era tool); this image only ever writes `.pcapng`, so it
silently processes nothing - dead on arrival, superseded by
`hashie-hcxpcapngtool.py` which is already on the list. `event_multithreading_for_plugins`
- patches `pwnagotchi/plugins/__init__.py` itself (core plugin-loading
file); highest-risk item on the list for silently breaking plugin loading
on a fork with its own modified internals, no diff could be confirmed
compatible.

**Group 44 - cluster 29 (handshake download web-UI plugins):** removed
`handshakes-dl.py` (1) - both it and `handshakes-dl-hashie.py` share the
same author, the same code skeleton, and the same `.pcap`-only bug
(glob filter, filename-length math, and hardcoded download extension all
assume a 5-character `.pcap` extension - none match this fork's real
`.pcapng` captures). `handshakes-dl-hashie.py` is a strict superset -
same capture-download page, plus it also surfaces already-converted
`.2500`/`.16800`/`.22000` hash files per capture - so `handshakes-dl.py`
was removed as a redundant subset rather than reviewed as a separate
option. Notably, even jayofelony's own official plugin repo
(`jayofelony/pwnagotchi-torch-plugins`) distributes `handshakes-dl.py`
with this exact same unfixed bug. `handshakes-dl-hashie.py` marked
**IN PROGRESS, moved to `plugins-wip`** for a full rebuild (same new
workflow as Cluster 28's DiscoHash Suite). See
`plugin-upgrade-proposals/cluster-29-handshakes-dl/NOTES.md` for the
full writeup.

**Group 43 - cluster 28 (Discord hash-dump ecosystem): moved to
`plugins-wip` for a full rebuild, not removed or kept as-is.** New
workflow starting here: rather than a binary keep/remove, a plugin can
now be marked **in progress** - moved into the separate `plugins-wip`
repo to be fixed, tested, documented, and packaged (plugin + config.toml
+ README + setup instructions) before graduating to `complete-plugins`
and being removed from this list entirely. `DiscoHash` (broken - wrong
hardcoded handshake directory plus the recurring `.pcap`/`.pcapng` bug)
and `hashbot.py` (not actually a pwnagotchi plugin - a standalone off-pi
script) were both already on this list; `discoBoss.py` (hardcoded
Discord token/channel placeholders, channel-only reboot/poweroff
authorization, duplicates `hashbot.py`'s hash-retrieval logic) was pulled
into scope for its direct overlap with `hashbot.py`, though it was never
formally on this master list. All three are consolidated into two pieces
in the new "DiscoHash Suite" (`plugins-wip` repo, `discohash-suite/`):
`discohash_ng.py` (pi-side) and a rebuilt `hashbot.py` (off-pi, now also
owns discoBoss's former reboot/poweroff/status commands, removing a
redundant always-on Discord bot from the pwnagotchi itself). Full
research writeup and every design decision in
`plugins-wip:discohash-suite/NOTES.md`; setup walkthrough in
`plugins-wip:discohash-suite/SETUP.md`. Not yet tested on real hardware.

**Group 42 - cluster 27 (attack-mode toggles & AP restriction):** removed
all 3 (`cuffs.py`, `enable_assoc.py`, `enable_deauth.py`). This is the
first cluster of a new review pass - now going category-by-category
through the full master list rather than only the discovery-audit
plugins. `cuffs.py` had one low-severity bug (mutates a list while
iterating it in `on_unfiltered_ap_list`, which only affects a log count
and an unused internal list - actual AP-scoping enforcement is correct)
but was removed anyway. `enable_assoc.py`/`enable_deauth.py` were both
clean (no bugs) but removed once it was confirmed, by reading this
fork's own `defaults.toml`, that `associate`/`deauth` are both already
`true` by default out of the box - these plugins only force them back to
`True` on load (redundant against the default) and `False` on unload
(a live kill-switch, not an enabler as their descriptions imply). See
`plugin-upgrade-proposals/cluster-27-attack-toggles/NOTES.md` for the
full writeup.

**Group 41 - cluster 26 (misc grab-bag):** findings-only, all 6 kept for
now (`wigle_ng.py`, `wpa-sec-list.py`, `wpa-sec_ng.py`, `auto-update_ng.py`,
`prime_gsm_hat.py`, `auto_tune.py`) - the final cluster spun out of the
Group 34 discovery audit. Two of the more significant findings in the
project: `prime_gsm_hat.py` is not actually a pwnagotchi plugin at all -
no `plugins.Plugin` subclass anywhere, confirmed via the same
`Plugin.__init_subclass__` registration check used on
`quick_rides_to_jail.py` in Cluster 20 - it's a standalone Python-2-era
manual setup script using the removed `raw_input()` builtin. And
`auto-update_ng.py` has four module-level functions
(`make_path_for`, `download_and_unzip`, `verify`, `install`) that all
reference `self.__class__.__name__` despite not being class methods,
guaranteeing `NameError` on every call - caught by the caller's own
try/except, silently disabling the auto-install feature while
detect/notify still works. Also found: `wigle_ng.py` has the
`.pcap`-vs-`.pcapng` bug in its core GPS-to-handshake matching path;
`wpa-sec-list.py` has an `IndexError` risk on a malformed potfile line
that breaks its whole page; `wpa-sec_ng.py` turned out to be a
completely different plugin than `wpa-sec-list.py` (an uploader to
wpa-sec.stanev.org, not a display page) - the master list's shared
description for the two has been corrected/split. `auto_tune.py`
(sniffleupagus) had no bugs found after extensive review of its 692
lines. See
`plugin-upgrade-proposals/cluster-26-misc-grab-bag/NOTES.md` for the
full writeup and fixes.

**Group 40 - cluster 25 (memtemp variants):** findings-only, both kept
(`memtemp_adv.py`, `memtemp_ng.py`) alongside the already-listed
`memtemp-plus.py`. `memtemp_adv.py` has a real `NameError` bug - a
one-character typo (`y_pos` instead of `v_pos`) in its waveshare_v3
vertical-orientation fallback position logic - plus a missing-defaults
gap on `scale` even by its own file's stated intent. `memtemp_ng.py` has
no bugs, but its default "cpu" field calls the framework's own
`pwnagotchi.cpu_load()` with no tag, which sleeps 0.1s internally on
every call - a small per-refresh UI-thread block; a non-blocking
alternate field ("cpus") exists in the same file but isn't the default.
`memtemp_adv.py`'s psutil-based CPU reading doesn't have this blocking
cost. See
`plugin-upgrade-proposals/cluster-25-memtemp-variants/NOTES.md` for the
full writeup and fixes.

**Group 39 - cluster 24 (remote/server control):** removed `fancyserver.py`
- two real bugs (a `NameError` on its error-logging path from an unused
`traceback` import, and an `UnboundLocalError` risk on `name`/`state`
in its "plugin" command branch). Kept `cmd_server.py` (two real bugs -
a `NameError` on a narrow cleanup-failure path, and a reply-misdirection
bug when multiple clients are connected simultaneously; both plugins
share an unauthenticated-local-socket design worth knowing about),
`console.py` (one cosmetic bug - a broken diagnostic log line that
silently drops its content rather than crashing - otherwise a clean,
well-defended plugin), and `webcfg_ng.py` (no bugs found; its
`save-config` webhook path fully overwrites `config.toml` with no merge
safety net, unlike its own `merge-save-config` path). See
`plugin-upgrade-proposals/cluster-24-remote-server-control/NOTES.md` for
the full writeup and fixes.

**Group 38 - cluster 23 (Bluetooth tethering):** removed `bt-tether_ng.py`
- confirmed via direct diff to be byte-for-byte identical to
`bt-tether.py` apart from a renamed class and `__name__` attribute (2
lines differ across 716). Kept `bt-tether.py` - a substantial,
well-built plugin (pairs with a phone over Bluetooth NAP/PAN, brings up
a network interface, makes the web UI reachable through it), with real
defensive per-device option validation rather than bare indexing. One
cosmetic-only issue not fixed: `__help__` is copy-pasted from an
unrelated plugin ("This plugin automatically uploads collected WiFi to
wigle.net" - the real `__description__` is correct). See
`plugin-upgrade-proposals/cluster-23-bluetooth-tethering/NOTES.md` for
the full writeup.

**Group 37 - cluster 22 (cracked-password display mirrors):** findings-only,
both kept (`show_password.py`, `show_pwd.py`) - a third, independent
mirror of the same idea as Cluster 7's `mycracked_pw.py`/
`display-password.py`/`display-password-qr.py` family, reading a
WPA-SEC potfile instead of a hashcat potfile. `show_password.py` has the
recurring missing-defaults gap on its `orientation` option (`KeyError`
on load unless set explicitly). `show_pwd.py` fixes that with a
self-populating default, but changes its `awk` query to dedupe by
network before taking the last line - meaning it can show an older crack
for a network that's been cracked more than once, working against the
"recently cracked" framing - and drops `show_password.py`'s friendly
empty-result fallback message. Neither crashes; both work as shipped,
just with different trade-offs. See
`plugin-upgrade-proposals/cluster-22-password-display-mirrors/NOTES.md`
for the full writeup and fixes.

**Group 36 - cluster 21 (LED/wardriving "_ng" rewrites):** removed
`led.py`, `led-ng.py`, `morse_code.py`, `morse_code-ng.py` (4). Kept
`wardriver-pwnagotchi-plugin`, `wardriver_ng.py`, `f0xtr0t`,
`webgpsmap_ng.py` (4, findings-only, documented for later fixing).
`led-ng.py` has a real regression bug (dropped the "led" prefix from its
sysfs LED path format string, pointing at a device name that doesn't
exist on real Raspberry Pi hardware). `morse_code-ng.py` is a purely
cosmetic rewrite of `morse_code.py`, no functional difference either
way. `wardriver_ng.py` is a real regression against itsdarklikehell's
own `wardriver.py` mirror - drops the on-screen UI and session-merging
entirely, and its directory cleanup lost the file-type filter the
original had (a real bug, not just a missing feature). `webgpsmap_ng.py`
filters `.pcap` throughout its core map-building logic instead of
`.pcapng`, so it never finds this device's real captures - this fork's
own bundled `webgpsmap.py` default already does this correctly - but it
does add `.paw-gps.json` GPS-source support nothing else on the list
has. See `plugin-upgrade-proposals/cluster-21-led-wardriving-ng/NOTES.md`
for the full writeup and fixes.

**Group 35 - cluster 20 (cracking-pipeline "_ng" rewrites):** findings-only,
all 6 kept (`aircrackonly.py`, `aircrackonly_ng.py`, `better_onlinehashcrack.py`,
`onlinehashcrack_ng.py`, `quick_rides_to_jail.py`, `quick_rides_to_jail_ng.py`).
`aircrackonly_ng.py` is a clean improvement over `aircrackonly.py` (adds an
on-screen delete-notice, no new bugs). `onlinehashcrack_ng.py` shares
`better_onlinehashcrack.py`'s already-documented `.pcap`-only backlog-scan
bug, but uses a possibly-more-current download endpoint
(`/wpa-exportcsv` vs. the older `/exportcsv`) and reads the device's real
global whitelist (`config['main']['whitelist']`) instead of a
plugin-scoped copy. Major finding: neither form of `quick_rides_to_jail`
actually works. `quick_rides_to_jail.py` has no `class X(plugins.Plugin):`
wrapper at all - confirmed via this fork's own loader source
(`Plugin.__init_subclass__` is the only registration path) that it
silently never registers as a plugin and none of its code ever runs.
`quick_rides_to_jail_ng.py` fixes the registration by wrapping everything
in a proper class, but both files share a second, independent bug - a
module-level `OPTIONS = dict()` that's declared but never populated from
`self.options` anywhere - so the `_ng` version registers correctly and
then raises `KeyError` the moment any real code path runs. The existing
master-list description for `quick_rides_to_jail.py` was corrected in
place to reflect this (previously implied it worked, with no caveat).
See `plugin-upgrade-proposals/cluster-20-cracking-pipeline-ng/NOTES.md`
for the full writeup and fixes.

**Group 34 - newly discovered plugins added to the list (23 files, 13
bullets).** A user-requested audit cross-checked every plugin filename in
`itsdarklikehell/pwnagotchi-plugins` (198 files), `sniffleupagus/pwnagotchi_plugins`
(23 files), and `pwnagotchi-unofficial`'s full archive (213 unique
filenames) against this master list. Confirmed 42 plugins across those
repos had never been added to the list at all - most concentrated in
`itsdarklikehell`'s repo, largely "_ng" (next-gen) rewrites of plugins
already on the list, plus a handful of standalone utilities. Of those 42,
23 were selected this round and added as new bullets above, marked
"pending review" with their upcoming cluster number:
- Cluster 20 (cracking-pipeline "_ng" rewrites): `aircrackonly_ng.py`,
  `onlinehashcrack_ng.py`, `quick_rides_to_jail_ng.py`
- Cluster 21 (LED/wardriving "_ng" rewrites): `led-ng.py`,
  `morse_code-ng.py`, `wardriver_ng.py`, `webgpsmap_ng.py`
- Cluster 22 (cracked-password display mirrors): `show_password.py`,
  `show_pwd.py`
- Cluster 23 (Bluetooth tethering): `bt-tether.py`, `bt-tether_ng.py`
- Cluster 24 (remote/server control): `fancyserver.py`, `cmd_server.py`,
  `console.py`, `webcfg_ng.py`
- Cluster 25 (memtemp variants): `memtemp_adv.py`, `memtemp_ng.py`
- Cluster 26 (misc grab-bag): `wigle_ng.py`, `wpa-sec-list.py`,
  `wpa-sec_ng.py`, `auto-update_ng.py`, `prime_gsm_hat.py`, `auto_tune.py`

This is a discovery/addition pass only - no keep/remove decisions made
yet, all 23 are now on the list pending the same cluster-by-cluster
review as everything else. The remaining 19 of the 42 found (mostly
watchdog/blindbug-recovery plugins and the UPS-Lite hardware family)
were not selected this round and remain undocumented for a future pass
if wanted.

**Group 33 - cluster 19 (auto-hotspot/connect plugins):** findings-only,
all 5 kept (`auto-hotspot.py`, `away_base.py`, `home_base.py`,
`ext_wifi.py`, `extWifi.py`), no bullets changed. This cluster turned up
some of the most severe bugs found in the project to date. `auto-hotspot.py`
cannot even import on this fork (`ModuleNotFoundError` on
`pwnagotchi.ai.reward` - confirmed no `pwnagotchi/ai/` module exists
anywhere in this fork's source) and separately has an infinite-loop bug
in `on_ui_update` (`while STATUS == "rssi_low":` and three similar
`while` blocks instead of `if`, with nothing inside the loop ever
changing `STATUS`) that would permanently hang the UI thread if the
import were ever fixed. `away_base.py` and `home_base.py` share a fatal
`NameError`: a module-level `_log()` helper references `self` outside
any method scope, breaking nearly all real functionality starting with
`on_loaded()`'s first line, plus a second, independent bug - both call
`agent.next_epoch(self)` with an extra argument the real method (confirmed
via `pwnagotchi/automata.py`) doesn't accept. `extWifi.py` (A1buS variant)
has an unconditional reboot loop: both branches of `on_loaded()` fall
through to the same `self.restart_pi()` call regardless of whether the
config line already existed, so the device would never stay booted once
enabled. `ext_wifi.py` (itsdarklikehell variant) is milder - missing
interface validation and no restart call after its `sed` edit, so it
silently does nothing until a manual reboot. All 5 assessed as fixable
with mechanical patches (no full rewrite needed) - see
`plugin-upgrade-proposals/cluster-19-auto-hotspot/NOTES.md` for the full
writeup, bug-by-bug fixes, and fixability assessment.

**Group 32 - duplicate/broken cluster 18 (Bluetooth scanning plugins):**
removed `bluetooth_scanner.py` (1) - confirmed non-functional by
construction, not merely buggy: imports `BasePlugin` from
`pwnagotchi.plugins`, a class that does not exist in this or any
pwnagotchi version (only `Plugin` does), so the file fails to even
import (`ImportError`) before any of its own code runs. Also calls
`self.log` (no such attribute on the real base class), defines
`on_periodic` (not a real hook - the framework never calls it), and
calls `agent.display_text(...)` (not a real method) - built against
an imagined API, not this framework. Would need a full rewrite from
scratch, not a patch - removed rather than documented-as-fixable.
Kept `blemon_plugin.py` (correctly built, deeply integrated with
bettercap's real BLE event stream, one small wrong-UI-key bug) and
`bluetoothsniffer.py` (also correctly framed, but carries three real
bugs: a wrong UI-key on unload, a genuine `UnboundLocalError` risk in
its scan loop, and instance-dict defaults discarded by the loader per
Group 31's correction - plus an unconfirmed `hcitool`-availability
compatibility risk on newer Debian Bookworm-based images). See
`plugin-upgrade-proposals/cluster-18-bluetooth/NOTES.md` for the full
writeup and fixes.

**Group 31 - project-wide correction: `__defaults__` is never read on
this fork.** While researching Cluster 18 (Bluetooth plugins), I read
this jayofelony fork's actual plugin loader
(`pwnagotchi/plugins/__init__.py`, `load()`) directly and confirmed it
never merges a plugin's class-level `__defaults__` attribute at all -
it assigns `plugin.options` straight from `config['main']['plugins'][name]`
(the user's own `config.toml` section, or `{}` if none exists). A
project-wide grep of this fork's entire core source turns up zero
references to `__defaults__` anywhere. Every earlier cluster's
"missing `__defaults__`" finding (Cluster 10's `adsbsniffer.py`,
Cluster 12's removed `dashboard.py`/`dashboard2.py`, Cluster 13's
`rss_voice.py`, Cluster 16's `expv2.py`/`xp.py`, Cluster 17's
`age.py`/`agev2.py`) recommended "add a `__defaults__` block" as the
fix - that recommendation does not actually work on this fork and has
been corrected in each cluster's own NOTES.md. The real fix on this
build is either setting every option explicitly in `config.toml`, or
patching the plugin to use `self.options.get(key, fallback)` instead
of indexing `self.options[key]` directly - the pattern `xp_grid.py`
(Cluster 16) and `git_backup.py` (Cluster 15) already happen to use,
which makes them correctly resilient on this fork independent of
whether that was the original author's intent. No plugin's keep/
remove status changes because of this correction - it only affects
which fix text is accurate.

**Group 30 - cluster 17 (age/strength plugins):** findings-only, all 3
kept. `age.py` and `agev2.py` (itsdarklikehell/Kaska) are near-
identical four-stat counters (Age/Strength/Access Points/Deauths);
both share a missing-`__defaults__` gap for their UI-position options,
and both update Strength/APs/Deauths only via the dead `on_ai_training_step`
hook (removed on this fork), so those three stats are permanently
frozen at 0 - only Age (wall-clock based, not epoch-based despite the
description) actually works. `agev2.py` additionally has a real bug of
its own: its Age UI element is added under the key `"AgeV2"` but
`on_ui_update` calls `ui.set("Age", ...)` - the wrong key - so
`agev2.py`'s Age display is broken as shipped, worse off than `age.py`
in that respect. The third entry, `age.py` (AlienMajik variant), is a
confirmed-unrelated plugin (filename collision only) - a much larger
prestige/lore RPG system that avoids the dead-AI-hook trap via a
passive-accrual fallback in `on_epoch`, correctly handles the
`.pcapng` extension, and reads as the most carefully engineered plugin
found in this entire project to date (self-documented bugfix history,
thread-safe locking, throttled atomic saves). No changes made to any
of the three. See
`plugin-upgrade-proposals/cluster-17-age-strength/NOTES.md` for the
full writeup and fixes.

**Group 29 - duplicate cluster 16 (XP/leveling plugins):** removed
`exp.py` (1) - diffed line-for-line against `Experience-Plugin-Pwnagotchi`
(GaelicThunder's original, unmirrored source) and confirmed an exact
functional duplicate (only whitespace/f-string formatting and author-
credit differences). Removed `Experience-Plugin-Pwnagotchi` (1) as the
same duplicate pair, same reasoning as the Discord/Telegram/fake-AP
mirror removals earlier in this project. `expv2.py` is `exp.py` plus
one added derived stat (a "Strength" value, `exp * level * 0.05`) -
otherwise character-for-character the same class, so kept as the
strict superset covering everything the other two did. Both `exp.py`
and `expv2.py` share a missing-`__defaults__` gap for their UI-position
options (same recurring pattern as `adsbsniffer.py`/`dashboard.py`)
and a real `==`-vs-`=` typo bug in their legacy-save-migration code
that silently drops saved level/total-XP on migration from the old
`.txt` format - documented for `expv2.py` (the one kept) since it's
inherited unchanged. Kept `xp.py` and `xp_grid.py` (2) - a separate,
more developed leveling system (20 weighted events, 21 named ranks
that change on-screen face glyphs, a live webhook dashboard, peer
level-sharing via `xp_grid.py`) with its own missing-`__defaults__`
gap and a permanent 4x XP-rate penalty baked in by a dead `on_ai_ready`
dependency on this fork (never fatal, just reduced XP gains forever).
See `plugin-upgrade-proposals/cluster-16-xp-leveling/NOTES.md` for the
full writeup.

**Group 28 - duplicate cluster 15 (backup plugins):** removed
`auto_backup_ng.py` (1) - diffed against its unmodified original
(dadav's `auto_backup.py`) and confirmed to be a cosmetic
rename/relabel only (class name, log tags, f-strings, two added
no-op hooks) with **no retention or garbage-collection logic at
all**, despite the master list's prior description claiming
otherwise - it always overwrites a single fixed `.tar.gz` filename.
`AutoBackup v2.0` (wpa-2, file itself declares `__version__ = "2.4"`)
does the identical job (local tar backup of config/SSH keys/
handshakes) strictly better: timestamped archives, real retention
(`max_backups_to_keep`, auto-pruned), disk-full self-healing,
include/exclude lists, a proper background scheduler thread, and a
manual-trigger webhook page. Kept `AutoBackup v2.0` and
`GitHub_Backups` (wpa-2's `git_backup.py`) - the latter is
complementary rather than redundant, since it's the only one of the
three that pushes a copy off-device (force-pushed to a GitHub/Gitea
remote over SSH, one-way, no push history retained by design) rather
than storing locally. `GitHub_Backups` has one architecture note
worth flagging: its backup routine runs synchronously inside
`on_internet_available` rather than in a spawned thread (`AutoBackup
v2.0` does spawn a thread), so a slow/stalled SSH push could block
that hook - same pattern class as Cluster 14's blocking-hook finding,
though less severe since this one is a finite operation rather than
an infinite loop. See
`plugin-upgrade-proposals/cluster-15-backup/NOTES.md` for the full
writeup.

**Group 27 - duplicate cluster 14 (fake-AP plugins):** removed
`apfaker.py` (1) - exact functional duplicate of `better_apfaker.py`
(same author, diffed line-for-line: only differences are the class
`__name__`, one dead/unreferenced config key
(`path: /home/pi/apfaker/`) added in the "better" version, and
cosmetic log-line reordering). Kept `better_apfaker.py`. Both (before
the diff) shared a real architecture concern worth flagging: `on_ready()`
ends in an unbounded `while not self.shutdown: sendp(...); sleep(...)`
loop that runs directly in that synchronous startup hook rather than
a spawned background thread - since `on_ready()` is expected to
return so the main agent loop can continue, this pattern likely
blocks the whole pwnagotchi process for as long as the plugin runs,
similar in kind (though intentional here, not accidental) to
`pwnassistant.py`'s hang from Cluster 13. Fix (spawn the transmit
loop in its own thread) documented, not applied. See
`plugin-upgrade-proposals/cluster-14-fake-ap/NOTES.md` for the full
writeup.

**Group 26 - duplicate cluster 13 (TTS/voice plugins):** removed
`pwnassistant.py` and `voice_gamer.py` (2). `pwnassistant.py` isn't a
real plugin at all - no `plugins.Plugin` subclass, and its module-
level code calls an interactive Google OAuth flow followed by an
infinite `while True:` microphone-listening loop, both of which run
the instant the file is imported - would hang the entire pwnagotchi
process forever at plugin-load time if ever placed where the loader
scans it. `voice_gamer.py` downloads a file from a configurable URL
and `sudo cp`s it over pwnagotchi's own core `voice.py` system module
with zero content validation - a real remote-code-injection design,
not just a bug - plus it never imports `logging` (NameError on its
very first log call) and its `on_unload` is missing the `ui` param
the framework passes. Kept `pwnspeaker.py` (comprehensively broken as
shipped - nearly every event hook concatenates a string with a
non-string value via `+`, throwing `TypeError`; also its own setup
instructions point at an armhf/32-bit-only `pico2wave` .deb package,
incompatible with this 64-bit image - needs a real rewrite, not a
one-line fix, but kept per broad-scope philosophy since `pyttsx3`
(the TTS engine it also uses) works fine once the string-building is
fixed), `rss_voice.py` (works correctly - not actually audio TTS
despite the "voice" name, replaces on-screen status text from RSS
feeds; one default-shape gap documented), and `speak_to_me.py` (clean
- modern `espeak-ng` engine, threaded queue avoids overlapping
speech, curated event set, no bugs found - the best-built plugin of
the five). See
`plugin-upgrade-proposals/cluster-13-tts-voice/NOTES.md` for the full
writeup.

**Group 25 - duplicate cluster 12 (dashboard plugins):** removed
`dashboard.py` and `dashboard2.py` (2), per user decision - not
needed. Both consolidate clock/RAM/CPU/temp/deauth-counter/handshake-
counter/cracked-count into one display; `dashboard.py` additionally
integrates a Pivoyager UPS/RTC hat (unconditional `on_loaded()` call
to a `/usr/local/bin/pivoyager` binary with no existence check -
would `FileNotFoundError` without that specific hat) plus an internet-
ping status check; `dashboard2.py` is `dashboard.py` with the
Pivoyager code stripped, but left a leftover dead call to the
now-undefined `self.get_status()` in `on_ui_update()` - throws
`AttributeError` on every single UI refresh cycle. Both also share an
undeclared-`__defaults__` gap on their ~7-9 position options
(`clock_x_pos` etc.), same pattern as Clusters 10/11. See
`plugin-upgrade-proposals/cluster-12-dashboard/NOTES.md` for the full
writeup.

**Group 24 - duplicate cluster 11 (clock/time-sync plugins):** removed
`clock_wav_v3.py` (1) - genuinely the same LoganMD-authored clock
plugin as `clock.py`, but only builds its UI element when
`ui.is_waveshare_v3()` is true (user is on an MPI3501 TFT, not
Waveshare), so on this hardware it creates nothing yet still calls
`ui.set('clock', ...)` every cycle - same class of screen-lock bug as
`wardrive.py` (Cluster 9). `clock.py` does the same job with a
hardcoded fixed position that works on any screen, no screen check at
all. Kept `clock.py`, `rtc_grid.py` (needs a physical I2C RTC module
at 0x68 the user doesn't have; safe to leave dormant, every hook is
try/excepted), and `RaspiSyncedTime.py` (not a real plugin - a
standalone utility class with no `plugins.Plugin` subclass, meant to
be imported by other code - but unlike `gsmfake.py`/
`Pwnagotchi-JSON-to-Wigle-CSV.py` it has no risky top-level code, so
importing it accidentally is harmless, not a crash risk). See
`plugin-upgrade-proposals/cluster-11-clock-timesync/NOTES.md` for the
full writeup.

**Group 23 - duplicate cluster 10 (aircraft tracking):** kept all 3 -
`adsbsniffer.py`, `pwnaware.py`, `skyhigh.py`. Not duplicates -
`skyhigh.py` needs no hardware (OpenSky Network API over internet),
`adsbsniffer.py` and `pwnaware.py` both need an RTL-SDR dongle (user
owns a couple) but use different toolchains (`adsbsniffer.py` shells
out to `rtl_adsb` directly; `pwnaware.py` reads a running
`dump1090-fa` daemon's JSON output) - not interchangeable. `skyhigh.py`
is clean, no issues found. `adsbsniffer.py` sets its option defaults
as an instance dict in `__init__` instead of the class-level
`__defaults__` the plugin loader actually merges config against -
likely `KeyError`s in `on_loaded()` unless every option is set
explicitly in config.toml. `pwnaware.py` has a hard bug in
`on_loaded()`: `logging.warn(f"...options = " % self.options)` mixes
an f-string with `%`-formatting against a dict with no `%s`
placeholder - throws `TypeError` immediately, before the very next
line that sets the `numPlanes` default, so every later hook reading
`self.options["numPlanes"]` will `KeyError`. Also has two undefined-
variable bugs (`err` instead of `e` in one except block, bare `hex`
instead of `"hex"` as a dict key) in less-common code paths. All
fixes documented, not applied. See
`plugin-upgrade-proposals/cluster-10-aircraft-tracking/NOTES.md` for
the full writeup.

**Group 22 - duplicate cluster 9 (wardriving/WiGLE plugins):** kept
all 10 - `f0xtr0t`, `Pwnagotchi-JSON-to-Wigle-CSV.py`,
`pwnagotchi_GPSD-ng`, `snoopr.py`, `theylive.py`, `tracker.py`,
`wardrive.py`, `wardriver-pwnagotchi-plugin`,
`warwalking_trails_kml.py`/`warwalking_trails_kml_single.py`,
`WigleLocator`. Three source-confirmed as broken as shipped:
`f0xtr0t`'s core map-population scan is `.pcap`-only, so on this
image (`.pcapng`) it finds zero handshakes and the map never
populates - fatal, only trigger path, fix documented.
`Pwnagotchi-JSON-to-Wigle-CSV.py` isn't a real plugin (standalone CLI
script) and has an unconditional top-level `sys.exit(1)` outside any
`__main__` guard - a real crash risk if the plugin loader ever imports
it, not just dead weight. `wardrive.py` calls `os.path.exists()` in
`on_ui_setup` without importing `os` - guaranteed `NameError` on
load on every screen type, and even fixed only draws UI elements on
Waveshare v2 screens (user is on an MPI3501 TFT). All three fixes
documented, not applied (user asked to keep broad scope, not narrow
yet). `pwnagotchi_GPSD-ng` (fmatray, different/more mature project
than Cluster 8's `gpsdeasy.py`) shares the same `.pcap`-only
backlog-scan and filename-mangling bug pattern as Cluster 5/8 - fix
documented. `snoopr.py`, `theylive.py`, `wardriver-pwnagotchi-plugin`,
`warwalking_trails_kml_single.py`, and `WigleLocator` are all clean -
no bugs found, none depend on handshake filenames at all except
`theylive.py` which was explicitly verified/fixed by its author for
this fork's `.pcapng` format (notably a strictly better alternative to
Cluster 8's `gpsdeasy.py`). `tracker.py` and
`warwalking_trails_kml.py` depend on a plugin registered as `"gps"`
(same architecture note as Cluster 8); the base (non-`_single`) KML
plugin also has a design flaw - it writes a new single-point file
every epoch instead of accumulating one trail, contrary to its own
name. See
`plugin-upgrade-proposals/cluster-09-wardriving-wigle/NOTES.md` for
the full writeup of all 10.

**Group 21 - duplicate cluster 8 (GPS/location status plugins):** kept
all 10 - `gps-plus.py`, `gps_error.py`, `gps_fix.py`, `gps_grid.py`,
`gps_led.py`, `gps_live.py`, `gpsdeasy.py`, `gps_sat.py`,
`gsmfake.py`, `mygps.py`. None are duplicates of each other - each
does a distinct job (different GPS sources, different status readouts,
one LED indicator, one non-plugin test script). `gps-plus.py` fits the
user's actual GPS hardware (owns a u-blox 7 USB dongle, a second
puck-style USB GPS receiver, and another GPS sensor) but shares a
filename bug with `gpsdeasy.py` and `mygps.py`: `filename.replace(
".pcap", ".gps.json")` isn't extension-aware, so on this image's real
`.pcapng` captures it produces a mangled `net.gps.jsonng` instead of
`net.gps.json` - fix is a one-line extension-strip before appending
`.gps.json`, documented for all three. `gps_error.py`/`gps_fix.py`/
`gps_grid.py`/`gps_live.py`/`gps_sat.py` are lightweight status
add-ons that read a plugin registered under the exact name `"gps"` -
harmless to leave enabled even before that dependency is confirmed
wired up (open question: does `gps-plus.py` register as `"gps"`?),
just inert until it is. `gps_led.py` needs an LED wired to GPIO 26 to
do anything, otherwise inert. `gsmfake.py` is flagged as not actually
a loadable plugin (no `plugins.Plugin` subclass, top-level imports of
`gps_ng`/`gps.fake` modules not present on this image) - kept on the
list per user decision, but will likely log an ImportError on every
boot when the plugin loader scans it. See
`plugin-upgrade-proposals/cluster-08-gps-status/NOTES.md` for the full
writeup of all 10.

**Group 20 - duplicate cluster 7 (cracked-password display/export):** kept
all 3 - `mycracked_pw.py`, `display-password.py`, `display-password-qr.py`.
Source review: `display-password.py` and `display-password-qr.py` are
near-identical files (both by the same author, `display-password-qr.py`
literally embeds a `_update_all()` method copy-pasted from `mycracked_pw.py`
without its `import qrcode`/`import csv`/`import io` lines) - both throw an
uncaught `NameError` inside `_update_all()` the moment a password is
actually cracked (`qrcode`/`csv`/`io` referenced but never imported), which
kills that method every time it's called from `on_loaded()`. Their actual
advertised on-screen feature is unaffected by this bug and works
independently - `on_ui_update()`/`on_webhook()` read the last cracked
password via a separate `tail -n 1 ... | awk` shell one-liner that doesn't
touch `_update_all()` at all. `display-password-qr.py`'s name is misleading:
despite the file name, comment header, and an unused embedded Flask/Jinja
`TEMPLATE` string referencing `/home/pi/qrcodes/`, it never actually renders
a QR code on the device screen - the QR-generation code lives only inside
the broken `_update_all()`. `mycracked_pw.py` is the functional original
these two forked from: same `_update_all()` logic but with all three
imports present, so QR/wordlist generation actually runs. Its only flaw is
minor - `_update_all()` only runs `on_loaded()` and `on_handshake()`, so its
`mycracked.txt` wordlist and QR codes go stale between captures on quiet
runs, not a functional break. See
`plugin-upgrade-proposals/cluster-07-cracked-password-display/NOTES.md` for
the full writeup and fix.

**Group 19 - duplicate cluster 6 (cloud-crack-upload destinations):** kept
all 8 - `banthex.py`/`banthex-de.py`, `better_onlinehashcrack.py`,
`dropbox_ul.py`, `hashespwnagotchi.py`, `nextcloud.py`,
`wpa-cracking-project-with-pwnagotchi`, `pwn2crack.py`. Source review
found 7 of 8 completely non-functional on this image, not just
partially like Cluster 5 - all seven trigger exclusively from
`on_internet_available` and filter the handshake directory with
`filename.endswith('.pcap')`, which never matches this image's
`.pcapng` output. All seven share the same underlying wpa-sec-clone
template (confirmed by `banthex.py`'s own header comment). Only
`pwn2crack.py` works correctly - it converts live via `on_handshake`
(no extension assumption) and uploads the `.22000` files it creates
itself. `wpa-cracking-project-with-pwnagotchi` verified to genuinely
exist (a university thesis project with a self-hosted Docker backend,
not a third-party service) after an initial doubt about it, same bug
as the other six. All fixable with the identical one-line change.
Extra flag: `hashespwnagotchi.py` has its whitelist-exclusion call
commented out, unlike all its siblings - worth fixing alongside the
main bug if this one is ever touched, or it would upload everything
indiscriminately once working. Full notes saved to
`plugin-upgrade-proposals/cluster-06-cloud-crack-upload/`.

**Group 18 - duplicate cluster 5 (pcap->hash conversion):** kept all 3 -
`hashie-hcxpcapngtool.py`, `hashieclean.py`, and a new find,
`hashie_ng.py` (co-authored by jayofelony himself, not on any prior
list - added here). Source review found all three share the same bug:
their live `on_handshake` conversion path works correctly on `.pcapng`
files, but their startup backlog/catch-up scan (`_process_stale_pcaps`)
filters with `.endswith('.pcap')`, so it silently finds nothing on this
image - same bug pattern as the already-removed `hashie.py`, just
limited to the backlog path rather than the live path this time.
Notably, even jayofelony's own touched version (`hashie_ng.py`) carries
this forward - it looks like a lineage-wide oversight from before the
fork switched to `.pcapng`, not one author's mistake. `hashieclean.py`
additionally deletes "lonely" pcaps that can't be converted (currently
unreachable via the same broken batch path). Fix/upgrade notes saved
to `plugin-upgrade-proposals/cluster-05-pcap-hash-conversion/`.

**Group 17 - duplicate cluster 4 (deauth counting):** no changes -
`deauth.py` and `counter.py` both kept. Source-verified clean (real,
simple, no compatibility issues found in either). They share the deauth
counter (genuinely redundant on-screen display) but each also tracks a
different second metric - `deauth.py` also counts handshakes,
`counter.py` also counts associations - so this isn't a true duplicate,
just a partial overlap. Noted as a possible future merge candidate
rather than forcing a pick now.

**Group 16 - duplicate cluster 3 decision:** removed `hp_educational-purposes.py`
(1) - functionally inert on both its honeypot half (never transmits real
beacon frames) and its auto-connect half (hardcoded SSID, never reads
config, RSSI check backwards for real dBm values) - would need a rewrite,
not a tweak, to do either thing it claims. Kept the other 3:
`educational-purposes-only.py` and `woop_woop.py` both need only the same
one-line fix (removing the dead `pwnagotchi.ai.reward` import) to load at
all; `educational-purposes-exclusively.py` already works close to as
described. Upgrade/fix notes for all 4 (including the removed one, for
the record) saved under `plugin-upgrade-proposals/cluster-03-auto-authenticate-recon/`.

**Group 15 - duplicate cluster 3 (auto-authenticate + recon on known
networks) verification pass:** no removals yet, findings only - real
source pulled directly from itsdarklikehell/pwnagotchi-plugins (all four
files confirmed to genuinely exist, contrary to an initial failed
verification attempt that searched web/API indexes instead of the actual
repo tree). `educational-purposes-only.py` AND `woop_woop.py` both contain
a top-level `from pwnagotchi.ai.reward import RewardFunction` import -
that module was fully removed from this fork's AI/RL layer, so **both
plugins fail to load at all** on this image (a real Group-12-category
compatibility break that slipped through the original pass since these
files weren't individually opened at the time). `woop_woop.py` also
targets any SSID found in the wpa-sec cracked-potfile, not a single
configured home network - broader scope than described, worth flagging
before any keep decision. `hp_educational-purposes.py` is functionally
inert on both its honeypot half (never transmits real beacon frames,
purely simulated in a Python set) and its auto-connect half (hardcoded
`home_network="test-net"`, never reads `self.options`; RSSI check is
backwards for real dBm values). `educational-purposes-exclusively.py` is
the one that works roughly as described - config-driven, no AI-module
import - though it carries a dead, never-called `_port_scan()` method.
No list changes made pending a decision.

**Group 14 - duplicate cluster 2 (aggressive/instant-attack mode):** no
changes - `hulk.py`, `instattack.py`, `probenpwn.py` all kept, despite a
source review finding `hulk.py` has zero target scoping (unconditional
`wifi.deauth *` every 5s, ignores `main.whitelist` entirely).

**Group 13 - duplicate cluster 1 (dictionary-crack speed variants):** removed
`quickdic.py`, `better_quickdic.py`, `pwnagotchi_fast_dictionary` (3) - all
three do the same job, and source review found real defects in each
(main-loop-blocking with no timeout; a live `os.listdir()` bug that reads
the wrong directory). Replaced by a custom-built `best_quickdic` plugin
(not part of this list - lives alongside the other custom plugins in this
repo).

---

## Attack / Capture behavior

- **aircrackonly.py** / **aircrackonly_ng.py** - Verifies a pcap actually contains a handshake/PMKID; deletes it if not (`_ng` also shows an on-screen status message when it deletes a pcap)
- **auto_tune.py** - Adjusts AUTO mode parameters; no bugs found after extensive review (692 lines); see Cluster 26 notes
- **banthex-de.py** - **IN PROGRESS, moved to `plugins-wip`** as `banthex-suite` (renamed `BanthexNG`) - `.pcap`/`.pcapng` bug fixed, plus a permanent-skip-on-failure bug fixed with bounded retries; see Cluster 31 notes
- **better_apfaker.py** - Creates fake APs
- **better_onlinehashcrack.py** - Uploads handshakes to onlinehashcrack.com (alternate implementation)
- **better_quickdic.py** - Quick dictionary scan; optionally sends found passwords as QR code/text to a Telegram bot
- **deauth.py** - Counts successful deauth attacks for the session
- **discoBoss.py** - Configurable rule engine for managing deauth ("disco") behavior
- **DiscoHash** - **IN PROGRESS, moved to `plugins-wip`** - broken as shipped (wrong hardcoded handshake directory plus the recurring `.pcap`/`.pcapng` bug); being rebuilt as `discohash_ng.py`, consolidated with `discoBoss.py` and `hashbot.py` into the DiscoHash Suite; see `plugins-wip` repo, `discohash-suite/`
- **educational-purposes-exclusively.py** / **educational-purposes-only.py** - Auto-authenticates to known networks and performs internal network recon (no target scoping)
- **enterprise.py** - Attempts to obtain credentials from enterprise networks when bored
- **handshakes-dl-hashie.py** - **IN PROGRESS, moved to `plugins-wip`** - web-UI handshake download page, also surfaces already-converted `.2500`/`.16800`/`.22000` hash files per capture; broken as shipped (the recurring `.pcap`-only bug in its glob filter, filename math, and download handler); being rebuilt; see `plugins-wip` repo
- **hashbot.py** - **IN PROGRESS, moved to `plugins-wip`** - not actually a pwnagotchi plugin (standalone script meant to run off-pi); consolidated into the DiscoHash Suite as the sole Discord-command bot (absorbing `discoBoss.py`'s control functions too); see `plugins-wip` repo, `discohash-suite/`
- **hashespwnagotchi.py** - **IN PROGRESS, moved to `plugins-wip`** as `hashespwnagotchi-suite` (renamed `HashesPwnagotchiNG`) - the confirmed command-injection security issue fixed (every external command now runs via a real argument list, never a shell), plus the `on_config_changed` crash bug, the `.pcap`/`.pcapng` bug, a Python-2 `.encode("hex")` bug, the disabled whitelist, and a permanent-skip-on-failure bug all fixed; see Cluster 31 notes
- **hashie-hcxpcapngtool.py** - Converts pcaps to crackable hash formats via hcxpcapngtool, updated for modern hcxtools/hashcat formats
- **hashie_ng.py** - Cleaned-up hashie variant co-authored by jayofelony himself; same live pcap->hash conversion, no delete-lonely-pcaps behavior
- **hashieclean.py** - hashie variant that also purges pcaps that can't be converted to a hash
- **hulk.py** - Puts pwnagotchi into an "always aggressive" attack mode
- **instattack.py** - Launches an immediate associate/deauth attack the instant a device is spotted
- **meshpwnstic.py** - Remote deauth/assoc/status control over a Meshtastic LoRa radio; **fix candidate, saved for later** - real functionality, but ships with no sender authentication at all on `/bcap`/`/deauth`/`/assoc`/`/restart` (any device on the mesh can run them), plus a `.pcap`-vs-`.pcapng` GPS-sidecar bug, a `self.nodes['num']` literal-key bug, two non-callable `logging(e)` calls, and an unguarded `self.interface.sendText()`; see Cluster 32 notes
- **mycracked_pw.py** - Grabs all cracked passwords, generates WiFi QR codes and a wordlist
- **neurolyzer.py** - MAC randomization, WIDS/WIPS evasion; well-engineered, no bugs found, but directly overlaps `mac_randomizer.py` (below) - both would fight over the interface's MAC if both are enabled; decision on both deferred, see Cluster 30 notes
- **onlinehashcrack_ng.py** - Uploads handshakes to onlinehashcrack.com (another alternate implementation, alongside better_onlinehashcrack.py; shares the same `.pcap`-only backlog-scan bug, but uses a possibly-more-current download endpoint and the device's real global whitelist)
- **privacy-nightmare.py** - **IN PROGRESS, moved to `plugins-wip`** as `gps-tagger-suite` (renamed `GPSTaggerNG`) - GPS-tags every AP seen and writes a `.gps.json` sidecar next to each handshake, interoperating with `handshakes_dl_ng.py`'s existing sidecar support; see Cluster 30 notes
- **probenpwn.py** - Aggressive handshake/PMKID capture, quiet assoc attacks, WPS PIN extraction, adaptive rate limiting
- **pwn2crack.py** (aka pwnagotchi-to-hashtopolis-plugin) - Converts handshakes to Hashcat 22000 and creates a hashlist in Hashtopolis
- **quick_rides_to_jail.py** / **quick_rides_to_jail_ng.py** - Dictionary-cracks handshakes, then auto-updates wpa_supplicant with results, **but neither form is functional as shipped**: `quick_rides_to_jail.py` has no `class X(plugins.Plugin):` wrapper at all, so it never registers as a plugin and silently never runs; `quick_rides_to_jail_ng.py` fixes that registration but has a second, independent bug (a module-level `OPTIONS` dict that's declared but never populated), so it registers and then `KeyError`s on first real use. See Cluster 20 notes for both fixes.
- **wd_honey_Pot.py** - Honeypot that detects OTHER pwnagotchis performing deauths nearby (defensive, not an attack tool); **not fixable as-is** - calls a nonexistent `self.register_event()` and listens for made-up event names that never fire on this fork, same root-cause class as the already-removed `bluetooth_scanner.py`; decision deferred (rewrite from scratch / drop / fold into another plugin), see Cluster 30 notes
- **woop_woop.py** - Auto-authenticates to known networks, performs internal recon, saves wifi info to wpa_supplicant
- **wpa-cracking-project-with-pwnagotchi** - Uploads handshakes to a companion university-thesis Hashcat web app

## Display / UI

- **clock.py** - Clock/calendar display
- **console.py** - Scrolling status-update console display (one cosmetic bug: a broken diagnostic log line that silently drops its intended content, no functional impact; see Cluster 24 notes)
- **crack_house.py** (+ a "-dev" variant) - Displays the closest cracked network and its password
- **darkmode.py** - Dark theme
- **display-aircrack.py** - Shows whether aircrack is currently running
- **display-password.py** / **display-password-qr.py** / **show_password.py** / **show_pwd.py** - Displays recently cracked passwords (QR variant adds a QR code; show_password.py/show_pwd.py are a separate mirror reading a WPA-SEC potfile rather than a hashcat potfile - show_password.py has a missing-defaults gap on `orientation`, show_pwd.py fixes that but changes "most recent" to mean each network's first-ever crack rather than the literal last line, and drops the empty-result fallback message; see Cluster 22 notes)
- **display-text.py** - Displays custom text on a Waveshare 1.44" LCD screen
- **display_version.py** - Adds the pwnagotchi software version to the display
- **internet-connection.py** - Displays internet connectivity status (also distributed as `wanmon.py` / `internet-conection.py`)
- **more_uptime.py** - Cycling uptime stats display
- **printp.py** - Minimal example plugin that prints to the pwnagotchi screen
- **PWNAGOTCHI-CUSTOM-FACES-MOD** - Custom PNG faces with transparency
- **pwnagotchi_LCD_colorized_darkmode** - Colorized dark-mode LCD/web UI mod
- **PwnagotchiCharacterPlugin** - Change face/voice via the web UI
- **Pwan-Girl** / **Bat-Trinity** - Custom anime/bat character faces
- **pwnagotchi-fallout-faces-mod** - Fallout Vault-Boy themed faces
- **screen_color_invert** - Inverts screen colors
- **screen_refresh.py** - Forces a display refresh after X updates
- **sprite_faces.py** - Cute sprite-based face graphics widget
- **themes.py** - Theme/script kicker plugin
- **timer.py** - Measures how long a handshake capture took
- **tweak_view.py** - Live UI element repositioning/fonts (no guardrails - be careful)
- **viz.py** - Visualizes surrounding APs

## GPS / Location

- **adsbsniffer.py** - ADS-B aircraft data via RTL-SDR
- **f0xtr0t** - Enhanced webgpsmap fork for wardriving
- **gps-plus.py** - GPS logging with configurable position
- **gps_error.py** - Displays an error when GPS isn't running
- **gps_fix.py** - Displays GPS fix quality
- **gps_grid.py** - Shares GPS coordinates with grid peers
- **gps_led.py** - Flashes an LED when GPS has a fix
- **gps_live.py** - Updates GPS coordinates every epoch
- **gps_sat.py** - Displays satellite count
- **gpsdeasy.py** - gpsd-based lat/long reporting + bettercap pcap GPS logging setup (jayofelony's official installer plugin)
- **mygps.py** - GPS via a phone's GPSLogger app - no GPS module hardware needed
- **Pwnagotchi-JSON-to-Wigle-CSV.py** - Standalone script converting handshake JSON files to a WiGLE-compatible CSV
- **pwnagotchi_GPSD-ng** - Multi-device GPSD manager with NTRIP/RTK support
- **pwnaware.py** - Displays nearby-airplane info from dump1090
- **RaspiSyncedTime.py** - Corrects timestamps using a synced-time offset - useful with no RTC/GPS time source
- **rtc_grid.py** - Shares RTC clock with grid peers
- **skyhigh.py** - Aircraft tracking via the OpenSky Network API - no special hardware needed
- **snoopr.py** - Wardriving + surveillance/tracker detection (WiFi/BLE/aircraft)
- **theylive.py** - GPS wardriving with per-handshake location logging
- **tracker.py** - Tracks seen APs/clients, with position if GPS is enabled
- **wardrive.py** - Wardriving log plugin
- **wardriver-pwnagotchi-plugin** / **wardriver_ng.py** - Logs all seen networks, uploads to WiGLE (`wardriver_ng.py` is a real regression vs. itsdarklikehell's own `wardriver.py` mirror - drops the on-screen network-count UI and session-merging entirely, and its directory cleanup lost its file-type filter, a real bug; see Cluster 21 notes for fixes)
- **warwalking_trails_kml.py** / **warwalking_trails_kml_single.py** - Generates KML trail files from wardriving data, for Google Earth
- **webgpsmap_ng.py** - "_ng" rewrite of the webgpsmap concept (f0xtr0t is the enhanced wardriving fork already on the list); **broken as shipped on this fork** - filters `.pcap` throughout its core map-building logic instead of `.pcapng`, so it never finds any of this device's real captures (this fork's own bundled `webgpsmap.py` default already handles `.pcapng` correctly); does add `.paw-gps.json` GPS-source support neither the bundled default nor f0xtr0t has; see Cluster 21 notes for the fix
- **wigle_ng.py** - Automatically uploads collected WiFi to wigle.net; **broken as shipped on this fork** - filters `.pcap` instead of `.pcapng` in its core GPS-to-handshake filename matching, silently skipping every real capture rather than crashing; see Cluster 26 notes for the fix
- **WigleLocator** - Queries WiGLE for AP coordinates, live maps

## Hardware-specific

- **basiclight.py** - GPIO traffic-light-style signal lights
- **blemon_plugin.py** - Counts/tracks max simultaneous BLE devices
- **bluetoothsniffer.py** - Logs nearby Bluetooth MACs/names/counts to a JSON file
- **fix_region.py** - Changes the iw region to unlock additional channels
- **flipperLink.py** - Connects pwnagotchi to a Flipper Zero
- **gpio_buttons_ng.py** - GPIO button support (next-gen/torch variant)
- **gpio_shutdown.py** - GPIO-triggered clean shutdown
- **gsmfake.py** - Feeds bettercap fake GPS coordinates from a GSM/GPRS modem when real GPS is unavailable
- **img2xbm.py** - Converts images to XBM format for a Flipper Zero display
- **mad_hatter.py** - Universal UPS battery monitor with auto-shutdown
- **memtemp-plus.py** / **memtemp_adv.py** / **memtemp_ng.py** - Memory/CPU usage + temperature display, adds CPU frequency (jayofelony's official installer plugin); memtemp_adv.py adds disk usage via psutil but has a real `NameError` bug on one screen/orientation combo (`y_pos` typo for `v_pos`); memtemp_ng.py uses the framework's own mem/cpu helpers, no bugs found, but its default CPU-load field blocks the UI thread ~0.1s per refresh (a non-blocking alternate field exists but isn't the default); see Cluster 25 notes
- **pibat.py** - Voltage indicator for the PiBat I2C UPS/battery hat
- **pisugar2.py** / **pisugar3.py** - Voltage/percentage indicator for PiSugar 2 / PiSugar 3
- **pivoyager.py** - PiVoyager UPS hat support
- **prime_gsm_hat.py** - Feeds bettercap fake GPS coordinates from a GSM hat's fake serial device (companion to gsmfake.py's approach); **not actually a pwnagotchi plugin at all** - no `plugins.Plugin` subclass anywhere in the file, so this fork's loader never registers it; it's a standalone Python-2-era manual setup script using the removed `raw_input()` builtin, which doesn't exist in Python 3; see Cluster 26 notes
- **pwnagotchi-18650** - Case design for an 18650 battery (hardware, not software)
- **pwnagotchi-plugin-pisugar2** - I2C battery data from PiSugar 2
- **pwnagotchi-plugin-pisugar3** - PiSugar 3 support (community "improved" fork)
- **pwnagotchi-WittyPi4L3V7-plugin** - Battery info + button support for WittyPi4L3V7
- **pwndroid.py** - Android/phone tethering integration (jayofelony's official installer plugin)
- **rgb.py** - RGB LED control
- **sigstr.py** - Displays WiFi signal strength as an on-screen bar
- **Touch_UI** - Touchscreen UI support
- **wof.py** - Detects other Flipper Zeros via "Wall of Flippers"

## Maintenance / Backup / Auto-update / Connectivity

- **auto-hotspot.py** - Automatically creates a WiFi hotspot when in manual mode
- **auto-update_ng.py** - Checks for and applies updates when internet is available; detect/notify works, but the actual auto-install feature is silently disabled - four module-level functions (`make_path_for`, `download_and_unzip`, `verify`, `install`) all reference `self.__class__.__name__` despite not being class methods, guaranteeing `NameError` on every call, caught by the caller's own try/except; see Cluster 26 notes for the fix
- **AutoBackup v2.0** - Local backup with a retention policy
- **away_base.py** / **home_base.py** - Watches for known networks and connects when available; `home_base` targets your home network specifically
- **bt-tether.py** - Makes the display reachable over Bluetooth tethering (dropped its exact-duplicate `bt-tether_ng.py` mirror; a `__help__` copy-paste typo remains, cosmetic only, see Cluster 23 notes)
- **ext_wifi.py** / **extWifi.py** - Disables the onboard WiFi chipset to free it for an external adapter
- **fix_brcmfmac.py** - Reloads the brcmfmac WiFi driver module on a hang instead of a full reboot
- **GitHub_Backups** - Syncs config to GitHub/Gitea
- **powerutils.py** / **powerutilscmd.py** - Remote shutdown/restart server, plus a CLI client
- **pwnaget.py** - SFTP-based script that auto-downloads captured handshakes off the pwnagotchi

## Network / Security analysis

- **beaconify.py** - Sends beacon frames more often, restarts pwngrid when it stops listening for other units' beacons
- **beacons.py** - Advertises pwnagotchi state via valid WiFi beacon frames
- **dns_spoof_detector.py** - Detects DNS spoofing/poisoning attempts
- **mac_adress_logger.py** - Logs MAC addresses seen on the network
- **mac_randomizer.py** - Randomizes the device's own MAC address; overlaps `neurolyzer.py`'s MAC rotation (Attack/Capture category) - would conflict if both enabled; not yet independently reviewed, decision deferred alongside neurolyzer.py, see Cluster 30 notes
- **network_intrusion_detector.py** - Detects potential network intrusion attempts
- **network_mapper.py** - Maps/enumerates devices on the local network
- **network_packet_sniffer.py** - Sniffs and logs network packets
- **rogue_ap_detector.py** - Detects rogue/unauthorized access points
- **test_security.py** - "LAN Security Monitor" plugin
- **traffic_sniffer.py** - Sniffs and analyzes network traffic
- **wifi_analyser.py** - Analyzes nearby WiFi networks/signals
- **wifi_jammer.py** - Sends deauth/jamming frames at WiFi networks - active, no scoping mentioned, treat with the same "your own SSIDs only" caution as your own gated plugins
- **wifi_password_cracker.py** - Attempts to crack WiFi passwords from captured handshakes - scoping unclear, redundant with crack-pipeline plugins already on the list

## Notifications / Social / Webhooks

- **apprise-notify.py** - Multi-service notification plugin, covers dozens of destinations via Apprise
- **Discord v3.0.1** - Uploads pcaps, maps locations, tracks sessions, posts to Discord
- **mastodon.py** - Periodically posts status updates to Mastodon
- **mqtt_plugin.py** - Sends pwnagotchi info to an MQTT broker
- **ntfy_msg.py** - Sends push notifications via ntfy
- **PwnSpotify** / **spotify_now_playing.py** - Displays the currently-playing Spotify track
- **pwnspeaker.py** - Text-to-speech announcements of pwning events
- **rss_voice.py** - Replaces canned voice lines with RSS feed content
- **Showerthoughts** - Displays random r/Showerthoughts headlines while idle
- **slack.py** - Posts recent activity to a Slack channel via webhook
- **sound.py** (+ **sound/shutdown_button.py**) - Plays a WAV file on events, plus a shutdown-button companion
- **speak_to_me.py** - Text-to-speech announcements of pwning events
- **TelePwn v2.0** - Advanced Telegram control and notifications
- **terminal2.py** - Browser-based terminal access (WebSSH2)
- **twitter.py** - Posts tweets about recent activity

## Novelty / Games / Personality

- **achievements.py** - Collects achievements for daily challenges
- **age.py** / **agev2.py** - Tracks device "age"/strength stats based on epochs
- **age.py** (AlienMajik variant) - Narrative "cyber-legend" prestige/lore system - same filename, unrelated plugin, naming collision
- **birthday.py** - Shows the age/birthday of your pwnagotchi
- **bitcoin.py** - Displays the current bitcoin price
- **christmas.py** - Holiday countdown theme
- **counter.py** - Tallies assoc/deauth attempts
- **envtune** - Environment-aware personality tuner (EMA smoothing, best-settings memory)
- **expv2.py** - Awards XP for each captured handshake
- **fortune_cookie.py** - Displays random fortune-cookie messages
- **IPDisplay.py** - Displays the device's IP address
- **miyagi.py** - "Training module" novelty plugin, manages brain backups
- **partymode.py** - Novelty party mode
- **spam_peers.py** - Auto-messages newly discovered grid peers
- **Weather.py** - Displays the weather forecast
- **wifi_adventures.py** - Achievement system themed around "WiFi adventures"
- **xp.py** / **xp_grid.py** - XP/leveling system with peer level-sharing (separate implementation from exp.py)

## Original evilsocket bundled (remainder - not superseded by anything jayofelony bundles)

- **net-pos.py** - Network-position (AP-based) geolocation lookup

## Web UI / API / Remote control

- **cmd_server.py** - Command-control plugin for pwnagotchi (a Unix-socket command shell; two real bugs - a NameError on a narrow cleanup-failure path, and a reply-misdirection bug with multiple simultaneous clients; unauthenticated local socket; see Cluster 24 notes)
- **handshaker.py** - Access key pwnagotchi info over an alternate channel when SSH is down
- **httpserver.py** - Simple HTTP server for serving files
- **pwmenu** - Mobile-first field console for captures/cracking/exports/whitelists
- **pwnagotchi-http-module** - Serves handshake pcaps via a simple HTTP server (targets the Bookworm image)
- **pwnmenu.py** / **pwnmenucmd.py** - Popup on-screen menu system, plus a CLI client
- **pwnmothership** - Pushes JSON state data to a "pwnmothership" host
- **pwnwatch.py** - Receives commands from a companion "pwnagotchi-watch" app
- **Pwny-Tailscale** - Tailscale remote connectivity, no port-forwarding needed
- **Pwny-WG** - WireGuard VPN + handshake sync over SSH
- **state-api.py** - JSON state API - a backend building block for menu/dashboard tools
- **web2ssh** - Lightweight web shell-command executor
- **webcfg_ng.py** - Allows the user to make runtime configuration changes (full web-based config.toml editor via webhook; no bugs found, but its `save-config` path fully overwrites the config file with no merge safety net, unlike its own `merge-save-config` path; see Cluster 24 notes)
- **wpa-sec-list.py** - Lists cracked passwords from wpa-sec on a web page; has an `IndexError` risk on a malformed potfile line that breaks the whole page; see Cluster 26 notes for the fix
- **wpa-sec_ng.py** - Not a display plugin despite the similar name - per its own `__description__`, automatically uploads handshakes to https://wpa-sec.stanev.org; shares the same `.pcap`-vs-`.pcapng` backlog-scan bug as the Cluster 6 family; see Cluster 26 notes for the fix

---
*Compiled by Claude · 2026-09-28*
