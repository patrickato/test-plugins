# Reference configs manifest

One config file per still-tracked plugin in `MASTER_PLUGIN_LIST.md`
(everything not already removed), fetched from wherever its real source
repo actually keeps it, or built from the plugin's own source code when
no shipped sample config exists. Generated 2026-09-28, cross-referenced
against: `itsdarklikehell/pwnagotchi-plugins` (+ its own `configs/`
folder), `sniffleupagus/pwnagotchi_plugins`, `alienmajik/pwnagotchi_plugins`,
`energydrinksjunkie`, `fmatray`, `pwnagotchi-unofficial/plugins_archive`
(the older mirror-archive), and `wpa-2/pwnagotchi-plugins`.

**The 6 plugin suites already moved to `plugins-wip` are NOT duplicated
here** (`privacy-nightmare.py`, `hashespwnagotchi.py`, `banthex-de.py`,
`handshakes-dl-hashie.py`, `discohash.py`/`hashbot.py`/`discoBoss.py`,
`wifi_jammer.py`) - their configs were compared against upstream and
finalized directly in their own suites; see each suite's own
`config.toml` + `NOTES.md`.

## How to read the status column

- **exact match** - a real config file shipped with this exact plugin
  was found and copied here (format/extension preserved: `.toml`,
  `.yml`/`.yaml`, `.json`). Any line that looked like a real API
  key/token/password (not a placeholder) was redacted to
  `REDACTED_SEE_UPSTREAM_HAD_REAL_VALUE` - the original repos' sample
  configs sometimes contain the author's own real, live-looking
  credentials, which shouldn't be propagated. Fill in your own value in
  place of the redaction.
- **partial match (closest available)** - no config was shipped for
  this *exact* plugin, but a near-identical sibling plugin's config was
  found and copied as the closest reference (e.g. `display-password-qr.py`
  using `display-password.py`'s sample). Verify against the actual
  plugin's own option names before using as-is - these are a starting
  point, not guaranteed to be a perfect match.
- **generated from `__defaults__`** - no shipped sample config existed
  anywhere searched, but the plugin's own Python source declares a
  `__defaults__` dict with real default values - a `config.toml` was
  built directly from that dict. This is the plugin author's own
  documented defaults, just never packaged as a separate sample file.
- **generated from usage scan** - no `__defaults__` dict either; every
  `self.options.get(...)`/`self.options[...]` call in the plugin's
  source was scanned instead. Options with an inline default in the
  code got that value; options read with no inline default are listed
  commented-out with `set a real value` - the plugin will need that
  option set for that code path to work, but no safe default could be
  inferred. Treat these as a documented starting skeleton, not a
  verified-complete config.
- **no options detected, enabled-only** - the plugin's source was
  found, but it reads no `self.options` at all (or none could be
  detected) - `enabled = true` is genuinely the only thing this plugin
  needs. Common for simple display/UI plugins with no configurable
  behavior.
- **not found in this environment** - neither a config file nor the
  plugin's own Python source could be located in any of the source
  repos cloned into this environment. Usually plugins reviewed earlier
  in this project by description/README only, without their source
  ever being cloned here (themes, hardware-specific mods, and a few
  standalone off-pi tools). Nothing to fetch or generate without
  cloning the actual source first.

All generated files were checked for real TOML/YAML/JSON syntax
validity (Python `True`/`False`/`None` literals converted to
`true`/`false`/commented-out, non-literal Python expressions such as
`self.DEFAULT_WIDS` or a Python regex dict commented out rather than
copied as invalid syntax) - every `.toml` file here parses cleanly.

---

## Exact match - real config found and copied (52)
| Plugin | Reference config | Source |
|---|---|---|
| `achievements.py` | [`achievements.toml`](achievements.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/achievements.toml` |
| `age.py` | [`age.toml`](age.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/age.toml` |
| `age.py` | [`age.toml`](age.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/age.toml` |
| `agev2.py` | [`agev2.toml`](agev2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/agev2.toml` |
| `aircrackonly.py` | [`aircrackonly.toml`](aircrackonly.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/aircrackonly.toml` |
| `auto-hotspot.py` | [`auto-hotspot.toml`](auto-hotspot.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto-hotspot.toml` |
| `away_base.py` | [`away_base.toml`](away_base.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/away_base.toml` |
| `beaconify.py` | [`beaconify.toml`](beaconify.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/beaconify.toml` |
| `beacons.py` | [`beacons.toml`](beacons.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/beacons.toml` |
| `better_apfaker.py` | [`better_apfaker.toml`](better_apfaker.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_apfaker.toml` |
| `better_onlinehashcrack.py` | [`better_onlinehashcrack.toml`](better_onlinehashcrack.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_onlinehashcrack.toml` |
| `better_quickdic.py` | [`better_quickdic.toml`](better_quickdic.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_quickdic.toml` |
| `bt-tether.py` | [`bt-tether.toml`](bt-tether.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/bt-tether.toml` |
| `counter.py` | [`counter.toml`](counter.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/counter.toml` |
| `deauth.py` | [`deauth.toml`](deauth.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/deauth.toml` |
| `display-password.py` | [`display-password.toml`](display-password.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display-password.toml` |
| `educational-purposes-only.py` | [`educational-purposes-only.toml`](educational-purposes-only.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/educational-purposes-only.toml` |
| `enterprise.py` | [`enterprise.toml`](enterprise.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/enterprise.toml` |
| `expv2.py` | [`expv2.toml`](expv2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/expv2.toml` |
| `ext_wifi.py` | [`ext_wifi.toml`](ext_wifi.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/ext_wifi.toml` |
| `extWifi.py` | [`extWifi.toml`](extWifi.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/ext_wifi.toml` |
| `f0xtr0t` | [`f0xtr0t.toml`](f0xtr0t.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/f0xtr0t.toml` |
| `flipperLink.py` | [`flipperLink.toml`](flipperLink.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/flipperLink.toml` |
| `gps-plus.py` | [`gps-plus.toml`](gps-plus.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps-plus.toml` |
| `gps_fix.py` | [`gps_fix.yml`](gps_fix.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/gps_fix.yml` |
| `gps_led.py` | [`gps_led.yml`](gps_led.yml) | `pwnagotchi-unofficial/plugins_archive/jd-2006/pwnagotchi-plugins-scripts_JD-2006/gps_led/gps_led.yml` |
| `gps_sat.py` | [`gps_sat.yml`](gps_sat.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/gps_sat.yml` |
| `handshaker.py` | [`handshaker.toml`](handshaker.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/handshaker.toml` |
| `hashie-hcxpcapngtool.py` | [`hashie-hcxpcapngtool.toml`](hashie-hcxpcapngtool.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/hashie-hcxpcapngtool.toml` |
| `hashieclean.py` | [`hashieclean.toml`](hashieclean.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/hashieclean.toml` |
| `home_base.py` | [`home_base.toml`](home_base.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/home_base.toml` |
| `hulk.py` | [`hulk.toml`](hulk.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/hulk.toml` |
| `instattack.py` | [`instattack.toml`](instattack.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/instattack.toml` |
| `IPDisplay.py` | [`IPDisplay.toml`](IPDisplay.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/IPDisplay.toml` |
| `memtemp-plus.py` | [`memtemp-plus.toml`](memtemp-plus.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/memtemp-plus.toml` |
| `mycracked_pw.py` | [`mycracked_pw.toml`](mycracked_pw.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/mycracked_pw.toml` |
| `mygps.py` | [`mygps.toml`](mygps.toml) | `itsdarklikehell/pwnagotchi-plugins/mygps.toml` |
| `net-pos.py` | [`net-pos.toml`](net-pos.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/net-pos.toml` |
| `powerutils.py` | [`powerutils.toml`](powerutils.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/powerutils.toml` |
| `prime_gsm_hat.py` | [`prime_gsm_hat.toml`](prime_gsm_hat.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/prime_gsm_hat.toml` |
| `pwnmenu.py` | [`pwnmenu.toml`](pwnmenu.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnmenu.toml` |
| `pwnspeaker.py` | [`pwnspeaker.toml`](pwnspeaker.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnspeaker.toml` |
| `quick_rides_to_jail.py` | [`quick_rides_to_jail.toml`](quick_rides_to_jail.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/quick_rides_to_jail.toml` |
| `rtc_grid.py` | [`rtc_grid.yml`](rtc_grid.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/rtc_grid.yml` |
| `show_password.py` | [`show_password.toml`](show_password.toml) | `itsdarklikehell/pwnagotchi-plugins/show_password.toml` |
| `spotify_now_playing.py` | [`spotify_now_playing.toml`](spotify_now_playing.toml) | `itsdarklikehell/pwnagotchi-plugins/spotify_now_playing.toml` |
| `wardrive.py` | [`wardrive.toml`](wardrive.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `warwalking_trails_kml.py` | [`warwalking_trails_kml.yml`](warwalking_trails_kml.yml) | `pwnagotchi-unofficial/plugins_archive/jd-2006/pwnagotchi-plugins-scripts_JD-2006/warwalking_trails_kml/warwalking_trails_kml.yml` |
| `warwalking_trails_kml_single.py` | [`warwalking_trails_kml_single.yml`](warwalking_trails_kml_single.yml) | `pwnagotchi-unofficial/plugins_archive/jd-2006/pwnagotchi-plugins-scripts_JD-2006/warwalking_trails_kml_single/warwalking_trails_kml_single.yml` |
| `wpa-sec-list.py` | [`wpa-sec-list.toml`](wpa-sec-list.toml) | `pwnagotchi-unofficial/plugins_archive/dbukovac/pwnagotchi-plugins-contrib/wpa-sec-list.toml` |
| `xp.py` | [`xp.yml`](xp.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/xp.yml` |
| `xp_grid.py` | [`xp_grid.yml`](xp_grid.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/xp_grid.yml` |

## Partial match - closest sibling config found, verify by hand (27)
| Plugin | Reference config | Source |
|---|---|---|
| `aircrackonly_ng.py` | [`aircrackonly_ng.toml`](aircrackonly_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/aircrackonly.toml` |
| `auto-update_ng.py` | [`auto-update_ng.toml`](auto-update_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto-update.toml` |
| `AutoBackup v2.0` | [`AutoBackup_v2.0.toml`](AutoBackup_v2.0.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto_backup.toml` |
| `display-password-qr.py` | [`display-password-qr.toml`](display-password-qr.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display-password.toml` |
| `gps_error.py` | [`gps_error.toml`](gps_error.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `gps_grid.py` | [`gps_grid.toml`](gps_grid.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/grid.toml` |
| `gps_live.py` | [`gps_live.toml`](gps_live.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `gpsdeasy.py` | [`gpsdeasy.toml`](gpsdeasy.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `hashie_ng.py` | [`hashie_ng.toml`](hashie_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/hashie.toml` |
| `memtemp_adv.py` | [`memtemp_adv.toml`](memtemp_adv.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/memtemp.toml` |
| `memtemp_ng.py` | [`memtemp_ng.toml`](memtemp_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/memtemp.toml` |
| `onlinehashcrack_ng.py` | [`onlinehashcrack_ng.toml`](onlinehashcrack_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/onlinehashcrack.toml` |
| `powerutilscmd.py` | [`powerutilscmd.toml`](powerutilscmd.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/powerutils.toml` |
| `pwnaget.py` | [`pwnaget.toml`](pwnaget.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/age.toml` |
| `Pwnagotchi-JSON-to-Wigle-CSV.py` | [`Pwnagotchi-JSON-to-Wigle-CSV.toml`](Pwnagotchi-JSON-to-Wigle-CSV.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wigle.toml` |
| `pwnagotchi-plugin-pisugar2` | [`pwnagotchi-plugin-pisugar2.toml`](pwnagotchi-plugin-pisugar2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pisugar2.toml` |
| `pwnagotchi-plugin-pisugar3` | [`pwnagotchi-plugin-pisugar3.toml`](pwnagotchi-plugin-pisugar3.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pisugar3.toml` |
| `pwnagotchi_GPSD-ng` | [`pwnagotchi_GPSD-ng.toml`](pwnagotchi_GPSD-ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `pwnmenucmd.py` | [`pwnmenucmd.toml`](pwnmenucmd.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnmenu.toml` |
| `quick_rides_to_jail_ng.py` | [`quick_rides_to_jail_ng.toml`](quick_rides_to_jail_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/quick_rides_to_jail.toml` |
| `wardriver-pwnagotchi-plugin` | [`wardriver-pwnagotchi-plugin.toml`](wardriver-pwnagotchi-plugin.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `wardriver_ng.py` | [`wardriver_ng.toml`](wardriver_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `webcfg_ng.py` | [`webcfg_ng.toml`](webcfg_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/webcfg.toml` |
| `webgpsmap_ng.py` | [`webgpsmap_ng.toml`](webgpsmap_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/webgpsmap.toml` |
| `wigle_ng.py` | [`wigle_ng.toml`](wigle_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wigle.toml` |
| `WigleLocator` | [`WigleLocator.toml`](WigleLocator.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wigle.toml` |
| `wpa-sec_ng.py` | [`wpa-sec_ng.toml`](wpa-sec_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wpa-sec.toml` |

## Generated from the plugin's own `__defaults__` dict (8)
| Plugin | Reference config | Source |
|---|---|---|
| `educational-purposes-exclusively.py` | [`educational-purposes-exclusively.toml`](educational-purposes-exclusively.toml) | `itsdarklikehell/pwnagotchi-plugins/educational-purposes-exclusively.py` |
| `pwnaware.py` | [`pwnaware.toml`](pwnaware.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnaware.py` |
| `pwnmothership` | [`pwnmothership.toml`](pwnmothership.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnmothership.py` |
| `rss_voice.py` | [`rss_voice.toml`](rss_voice.toml) | `itsdarklikehell/pwnagotchi-plugins/rss_voice.py` |
| `show_pwd.py` | [`show_pwd.toml`](show_pwd.toml) | `itsdarklikehell/pwnagotchi-plugins/show_pwd.py` |
| `test_security.py` | [`test_security.toml`](test_security.toml) | `itsdarklikehell/pwnagotchi-plugins/test_security.py` |
| `tracker.py` | [`tracker.toml`](tracker.toml) | `itsdarklikehell/pwnagotchi-plugins/tracker.py` |
| `wd_honey_Pot.py` | [`wd_honey_Pot.toml`](wd_honey_Pot.toml) | `itsdarklikehell/pwnagotchi-plugins/wd_honey_Pot.py` |

## Generated from a scan of `self.options` usage (no `__defaults__`) (13)
| Plugin | Reference config | Source |
|---|---|---|
| `adsbsniffer.py` | [`adsbsniffer.toml`](adsbsniffer.toml) | `alienmajik/pwnagotchi_plugins/adsbsniffer.py` |
| `auto_tune.py` | [`auto_tune.toml`](auto_tune.toml) | `sniffleupagus/pwnagotchi_plugins/auto_tune.py` |
| `console.py` | [`console.toml`](console.toml) | `sniffleupagus/pwnagotchi_plugins/console.py` |
| `meshpwnstic.py` | [`meshpwnstic.toml`](meshpwnstic.toml) | `sniffleupagus/pwnagotchi_plugins/meshpwnstic.py` |
| `neurolyzer.py` | [`neurolyzer.toml`](neurolyzer.toml) | `alienmajik/pwnagotchi_plugins/neurolyzer.py` |
| `pwn2crack.py` | [`pwn2crack.toml`](pwn2crack.toml) | `pwnagotchi-unofficial/plugins_archive/Brets0150/pwnagotchi-to-hashtopolis-plugin/pwn2crack.py` |
| `pwnwatch.py` | [`pwnwatch.toml`](pwnwatch.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnwatch.py` |
| `Pwny-Tailscale` | [`Pwny-Tailscale.toml`](Pwny-Tailscale.toml) | `wpa-2/pwnagotchi-plugins/tailscale.py` |
| `skyhigh.py` | [`skyhigh.toml`](skyhigh.toml) | `alienmajik/pwnagotchi_plugins/skyhigh.py` |
| `speak_to_me.py` | [`speak_to_me.toml`](speak_to_me.toml) | `sniffleupagus/pwnagotchi_plugins/speak_to_me.py` |
| `state-api.py` | [`state-api.toml`](state-api.toml) | `pwnagotchi-unofficial/plugins_archive/dipsylala/pwnagotchi-state-api/state-api.py` |
| `wof.py` | [`wof.toml`](wof.toml) | `itsdarklikehell/pwnagotchi-plugins/wof.py` |
| `woop_woop.py` | [`woop_woop.toml`](woop_woop.toml) | `itsdarklikehell/pwnagotchi-plugins/woop_woop.py` |

## No configurable options detected - `enabled = true` only (8)
| Plugin | Reference config | Source |
|---|---|---|
| `cmd_server.py` | [`cmd_server.toml`](cmd_server.toml) | `sniffleupagus/pwnagotchi_plugins/cmd_server.py` |
| `httpserver.py` | [`httpserver.toml`](httpserver.toml) | `itsdarklikehell/pwnagotchi-plugins/httpserver.py` |
| `probenpwn.py` | [`probenpwn.toml`](probenpwn.toml) | `alienmajik/pwnagotchi_plugins/probenpwn.py` |
| `PWNAGOTCHI-CUSTOM-FACES-MOD` | [`PWNAGOTCHI-CUSTOM-FACES-MOD.toml`](PWNAGOTCHI-CUSTOM-FACES-MOD.toml) | `itsdarklikehell/pwnagotchi-plugins/extras/facemod/faces.py` |
| `pwnagotchi-fallout-faces-mod` | [`pwnagotchi-fallout-faces-mod.toml`](pwnagotchi-fallout-faces-mod.toml) | `itsdarklikehell/pwnagotchi-plugins/extras/facemod/faces.py` |
| `RaspiSyncedTime.py` | [`RaspiSyncedTime.toml`](RaspiSyncedTime.toml) | `pwnagotchi-unofficial/plugins_archive/xenDE/pwnagotchi-plugin-timesync/RaspiSyncedTime.py` |
| `snoopr.py` | [`snoopr.toml`](snoopr.toml) | `alienmajik/pwnagotchi_plugins/snoopr.py` |
| `theylive.py` | [`theylive.toml`](theylive.toml) | `alienmajik/pwnagotchi_plugins/theylive.py` |

## Not found - no config or source located in this environment (9)
| Plugin |
|---|
| `fix_brcmfmac.py` |
| `GitHub_Backups` |
| `pwmenu` |
| `pwnagotchi-18650` |
| `pwnagotchi-http-module` |
| `pwnagotchi-WittyPi4L3V7-plugin` |
| `pwndroid.py` |
| `Pwny-WG` |
| `wpa-cracking-project-with-pwnagotchi` |

## Already handled - moved to `plugins-wip`, not duplicated here (33)
| Plugin | Where |
|---|---|
| `apprise-notify.py` | `plugins-wip` suite (apprise-notify-suite, AppriseNotifyNG) |
| `banthex-de.py` | `plugins-wip` suite |
| `birthday.py` | `plugins-wip` suite (birthday-suite, BirthdayNG) |
| `blemon_plugin.py` | `plugins-wip` suite (bluetooth-recon-suite, BluetoothReconNG - merged with bluetoothsniffer.py) |
| `bluetoothsniffer.py` | `plugins-wip` suite (bluetooth-recon-suite, BluetoothReconNG - merged with blemon_plugin.py) |
| `mad_hatter.py` | `plugins-wip` suite (mad-hatter-suite, MadHatterNG - feature upgrade, file MadHatterNG.py) |
| `fix_region.py` | `plugins-wip` suite (fix-region-suite, FixRegionNG, file fix_region_ng.py) |
| `sigstr.py` | `plugins-wip` suite (sigstr-suite, SigStrNG, file sigstr_ng.py) |
| `web2ssh` | `plugins-wip` suite (web2ssh-suite, Web2SSHNG, file web2ssh_ng.py) |
| `clock.py` | `plugins-wip` suite (clock-suite, ClockNG) |
| `crack_house.py` | `plugins-wip` suite (crack-house-suite, CrackHouseNG) |
| `discoBoss.py` | `plugins-wip` suite |
| `Discord v3.0.1` | `plugins-wip` suite (discord-suite, DiscordNG) |
| `display-aircrack.py` | `plugins-wip` suite (display-aircrack-suite, DisplayAircrackNG) |
| `display_version.py` | `plugins-wip` suite (display-version-suite, DisplayVersionNG) |
| `DiscoHash` | `plugins-wip` suite |
| `fortune_cookie.py` | `plugins-wip` suite (fortune-cookie-suite, FortuneCookieNG) |
| `handshakes-dl-hashie.py` | `plugins-wip` suite |
| `hashbot.py` | `plugins-wip` suite |
| `hashespwnagotchi.py` | `plugins-wip` suite |
| `internet-connection.py` (+ `wanmon.py`, `internet-conection.py`) | `plugins-wip` suite (internet-connection-suite, InternetConnectionNG) |
| `more_uptime.py` | `plugins-wip` suite (more-uptime-suite, MoreUptimeNG) |
| `privacy-nightmare.py` | `plugins-wip` suite |
| `Showerthoughts` | `plugins-wip` suite (showerthoughts-suite, ShowerThoughtsNG - built from scratch, no source existed) |
| `spam_peers.py` | `plugins-wip` suite (spam-peers-suite, SpamPeersNG) |
| `terminal2.py` | `plugins-wip` suite (terminal-suite, TerminalNG) |
| `timer.py` | `plugins-wip` suite (timer-suite, TimerNG) |
| `Touch_UI` | `plugins-wip` suite (touch-ui-suite, TouchUING) |
| `tweak_view.py` | `plugins-wip` suite (tweak-view-suite, TweakViewNG) |
| `viz.py` | `plugins-wip` suite (viz-suite, VizNG) |
| `Weather.py` | `plugins-wip` suite (weather-suite, WeatherNG) |
| `wifi_adventures.py` | `plugins-wip` suite (wifi-adventures-suite, WifiAdventuresNG) |
| `wifi_jammer.py` | `plugins-wip` suite (wifi-jammer-suite, WifiJammerNG) |

