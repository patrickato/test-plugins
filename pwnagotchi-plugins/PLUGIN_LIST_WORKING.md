# Plugin List - Working Copy (Round 1 + Round 2 additions)

Starting point: the raw census (`FULL_PLUGIN_CENSUS_RAW.md`), minus
jayofelony-bundled defaults and your own custom plugins.

This round's cuts: anything made for a 32-bit image, and anything dead/
superseded because a jayofelony-bundled plugin already does the same job.

## Removed this round

| Plugin | Reason |
|---|---|
| `onlinehashcrack.py` (evilsocket) | Superseded - jayofelony bundles `ohcapi.py`, its own rewrite of the same Online Hash Crack integration |
| `paw-gps.py` (evilsocket) | Superseded - jayofelony bundles `gps.py` and offers `gpsdeasy.py`, both doing the same basic GPS job |
| `watchdog.py` (evilsocket) | Superseded - jayofelony bundles `fix_services.py`, which covers the restart-on-hang role |
| `pwnagotchi-plugin-gpsd` (kellertk) | Duplicate of bundled `gps.py` - "shows GPS location from GPSD," no feature beyond what's already bundled |
| `gps_more.py` (Sniffleupagus) | Duplicate of bundled `gps.py`'s core job (log/update location) - no distinct feature stated beyond "until fix" |
| UPS Lite v1.3 (gist, LouDnl) | Superseded - that exact functionality now ships as the bundled `ups_lite.py` default plugin |

**On the 32-bit question specifically:** nothing in the census was found
explicitly built for a 32-bit-only image. Pwnagotchi plugins are plain
Python against the same `Plugin` API regardless of architecture - the
32-bit/64-bit split lives in the OS image and bettercap binary, not in
individual plugin `.py` files. The only 32-bit-specific thing on record
is `jayofelony/pwnagotchi-bullseye` itself (the legacy image, not a
plugin) - so there's nothing to remove here without guessing. If you run
into a plugin later that turns out to need an armhf-only binary, flag it
and I'll pull it.

Two borderline cases I did **not** cut, flagged instead of guessed on:
- `quickdic.py` - possibly redundant against the bundled `pwncrack.py`
  (both look like basic local dictionary crackers by name), but I don't
  have a confirmed feature breakdown of `pwncrack.py` to prove it's a
  real duplicate rather than something different. Left in.
- `pwnagotchi-WittyPi4L3V7-plugin` - jayofelony bundles a generic
  `wittypi.py`, but this one targets a specific WittyPi sub-model
  (L3V7) that may need distinct I2C handling the generic version
  doesn't cover. Left in rather than assumed redundant.

## What's left

### Original evilsocket bundled plugins (remainder)
| Plugin | Description |
|---|---|
| `led.py` | Status LED control |
| `net-pos.py` | Network-position (geolocation via visible APs) lookup |

### jayofelony/pwnagotchi-torch-plugins (official installer repo)
`bluetoothsniffer.py`, `gpsdeasy.py`, `handshakes-dl.py`, `internet-connection.py`, `memtemp-plus.py`, `pwndroid.py`

### Display / UI
`clock.py`, `darkmode.py`, `dashboard.py`/`dashboard2.py`, `display-password.py`, `display-text.py`/`display_version.py`, `tweak_view.py`, `screen_refresh.py`, `screen_color_invert`, `Fancygotchi`, `pwnagotchi_LCD_colorized_darkmode`, `PWNAGOTCHI-CUSTOM-FACES-MOD`, `PwnagotchiCharacterPlugin`, `Pwan-Girl`, `Bat-Trinity`, `pwnagotchi-fallout-faces-mod`, `more_uptime.py`

### GPS / Location
`gps-plus.py`, Sliim's set (`gps_error.py`, `gps_fix.py`, `gps_grid.py`, `gps_live.py`, `gps_sat.py`, `rtc_grid.py`, `tracker.py`, `xp_grid.py`, `xp.py`, `waveshare_v3_touch.py`), `pwnagotchi_GPSD-ng`, `wardriver-pwnagotchi-plugin`, `f0xtr0t`, `WigleLocator`, `theylive.py`, `snoopr.py`, `skyhigh.py`, `adsbsniffer.py`

### Notifications / Webhooks / Social
`discord.py`, `pwng2discord`, `pwnagotchi-discord-plugin`, `telegram.py` (dadav), `telegram.py` (wpa-2 standalone), `TelePwn` v2.0, `twitter.py`, `mastodon.py`, `Discord` v3.0.1, `DiscoHash`, `PwnSpotify`, `rss_voice.py`, `Showerthoughts`, `speak_to_me.py`

### Attack / Capture behavior
`aircrackonly.py`, `quickdic.py`, `pwnagotchi_fast_dictionary`, `quick_rides_to_jail`, `hashie.py`, `hashie-hcxpcapngtool.py`, `handshakes-dl-hashie.py`, `deauth.py`, `hulk.py`, `apfaker.py`, `enable_assoc.py`/`enable_deauth.py`, `cuffs.py`, `probenpwn.py`, `neurolyzer.py`, `wpa-cracking-project-with-pwnagotchi`, `pwnagotchi-to-hashtopolis-plugin`, `crack_house.py`, `meshpwnstic.py`

### Web UI / API / Remote control
`web2ssh`, `Pwny-WG`, `Pwny-Tailscale`, `pwnagotchi-http-module`, `pwmenu`, `pwnmothership`, `GitHub_Backups`

### Auto-update / Maintenance / Backup
`auto_backup_ng.py`, `AutoBackup` v2.0, `fix_brcmfmac.py`, `event_multithreading_for_plugins`, `pwnagotchi-postinstall`, `monstart`/`monstop`

### Hardware-specific
`gpio_buttons_ng.py`, `gpio_shutdown.py`, `buttonshim.py`, `pwnagotchi-plugin-pisugar2`, `pwnagotchi-plugin-pisugar3` (+ fork), `pisugar3.py`, `pwnagotchi-WittyPi4L3V7-plugin`, `mad_hatter.py`, `Pwnagotchi_Waveshare_2.66inch`, `Pwnagotchi-WS-V3-V4`, `Pwnagotchi-Waveshare-V3-Fix`, `Pwnagotchi-on-waveshare-v4`, `Touch_UI`, `gsmfake`, `blemon_plugin.py`, `bluetoothsniffer.py`, `morse_code.py`, `fix_region.py`, `pwnagotchi-18650` (case, hardware only)

### Novelty / Games / Personality
`age.py`/`agev2.py` (itsdarklikehell), `age.py` (AlienMajik, different plugin), `exp.py`/`expv2.py`, `achievements.py`, `counter.py`, `christmas.py`, `fortune_cookie.py`, `birthday.py`, `Weather.py`, `IPDisplay.py`, `Experience-Plugin-Pwnagotchi`, `miyagi.py`, `envtune`

### Network / Security analysis
`beacons.py`, `banthex.py`, `dropbox_ul.py`, `beaconify.py`, `instattack.py`, `pwnaware.py`, `auto-hotspot.py`

### Aggregator repos (source of many above)
itsdarklikehell, kizeren, evilsocket-contrib, xfox64x, AlienMajik, wpa-2, Sniffleupagus, Pwnagotchi-Unofficial, Teraskull, crahan, PwnPeter, SHUR1K-N, rohanday3, avipars, Deus73, Sliim, hannadiamond, vanshksingh, gallis-local

### Misc/uncategorized
RasTacsko build guides, Th4ntis CyberSecNotes, Pnwcomputers cheatsheet (guides referencing plugins, not plugin repos themselves)

---

## Round 2: what the first sweep missed

The first research pass explicitly flagged that it only got a **partial**
sample of the two largest aggregator repos - `itsdarklikehell/pwnagotchi-plugins`
(231 `.py` files) and `Pwnagotchi-Unofficial/plugins_archive` (349 `.py` files
across 71 mirrored contributor folders). This round is a full, exhaustive
file-by-file listing of both (via `git clone`, not sampling), applying the
same two Round-1 filters (32-bit-only, superseded-by-jayofelony-bundled) to
whatever's new.

Files that are just "_ng" (torch-renamed) copies of a plugin already listed,
or the same plugin mirrored verbatim across many contributor forks (this
ecosystem re-hosts the same handful of files constantly), are folded into
one entry rather than re-listed per mirror.

### Removed this round

| Plugin | Reason |
|---|---|
| `gpsd.py` (all mirrors: kellertk, k4n3d4-sh0t4r0 V1/V2) | Duplicate of bundled `gps.py`, no added feature - same reasoning as Round 1's `pwnagotchi-plugin-gpsd` cut |
| `upload.py` (Terminatoror) | Identical function to bundled `wpa-sec.py` ("automatically uploads handshakes to wpa-sec.stanev.org") |
| `RestartPlugin.py` / `prototype.py` (Terminatoror) | "Restarts pwnagotchi if bettercap crashes" is the same job as bundled `fix_services.py` |

Also excluded as **not plugins at all** (support/library files pulled in by
the "every .py file" sweep, not standalone pwnagotchi plugins): `fake.py`
(gpsfake test-double classes), the Waveshare `epd.py`/`epdconfig.py` low-level
display drivers, and the various Fancygotchi/Fancytools internal backend/UI
modules (`backend.py`, `components.py`, `state.py`, `view.py`, etc. under
V0r-T3x's folders) - `Fancygotchi` itself is already listed once as a plugin
in Round 1.

**32-bit:** still nothing found explicitly built 32-bit-only, same as Round 1.

### New plugins found - by category

**Notifications / Social**
`apprise-notify.py` (multi-service notification framework - one plugin, dozens of possible destinations via Apprise), `slack.py` (Slack webhook posting - notably absent from Round 1), `discord_notify.py` (Lehniii, simpler Discord alternative), `ntfy_msg.py` (ntfy.sh push notifications), `mqtt_plugin.py` (MQTT integration), `neonbot.py` (Telegram QR/control bot), `sound.py` + `sound/shutdown_button.py` (WAV playback on events, plus a shutdown button), `pwnspeaker.py` (TTS, similar to `speak_to_me.py`), `pwnassistant.py` (voice control via connected mic), `terminal2.py` (WebSSH2 - browser-based terminal access)

**GPS / Location**
`mygps.py` (GPS via a phone's GPSLogger app - no GPS module hardware needed), `gps_led.py` (flashes an LED when GPS has a fix), `warwalking_trails_kml.py` / `warwalking_trails_kml_single.py` (KML trail generation for Google Earth from wardriving data), `Pwnagotchi-JSON-to-Wigle-CSV.py` (standalone JSON→WiGLE CSV converter script), `wardrive.py` (itsdarklikehell's own wardriving log plugin), `RaspiSyncedTime.py` (corrects timestamps using a synced-time offset - useful if you have no RTC or GPS time source)

**Attack / Capture behavior - several flagged for the same scoping caution as your own gated plugins**
`enterprise.py` (attempts to obtain credentials from enterprise networks when bored), `educational-purposes-exclusively.py` / `educational-purposes-only.py` / `hp_educational-purposes.py` / `woop_woop.py` (auto-authenticate to known networks + internal network recon - broad/active, no target scoping mentioned), `discoBoss.py` (configurable deauth rule engine), `privacy-nightmare.py` ("eavesdropping metadata" plugin - provocatively named, worth reading the source yourself before trusting), `wd_honey_Pot.py` (honeypot that *detects other pwnagotchis* deauthing nearby - defensive, not an attack tool), `potfilesorter.py` (utility: sorts a hashcat potfile into a usable `wpa_supplicant.conf`), `hashieclean.py` (hashie variant that also purges unconvertable "lonely" pcaps), `hashbot.py` (Discord bot companion to DiscoHash), `hashespwnagotchi.py` (uploads handshakes to hashes.pw - another cloud-crack destination), `pwn2crack.py` (Brets0150's actual filename for the Hashtopolis integration found in Round 1)

**Web UI / Remote control**
`state-api.py` (JSON state API - a backend building block for menu/dashboard tools), `pwnmenu.py` / `pwnmenucmd.py` (popup menu system + CLI client), `powerutils.py` / `powerutilscmd.py` (remote shutdown/restart server + CLI client), `httpserver.py` (another simple HTTP server plugin, separate from `pwnagotchi-http-module`), `pwnwatch.py` (receives commands from a companion "pwnagotchi-watch" app), `ext_wifi.py` / `extWifi.py` (disables the onboard WiFi chipset to free it for an external adapter - directly relevant to the external-adapter setup discussed earlier in this project), `handshaker.py` (access key pwnagotchi info over an alternate channel when SSH is down)

**Hardware-specific**
`basiclight.py` (GPIO traffic-light-style signal lights), `fireworks.py` (Pimoroni Button Shim light show), `rgb.py` (RGB LED control), `lcdhat.py` / `lcdhatcontrols.py` (LCD HAT display support), `display_settings.py` (backlight control, Pimoroni Display HAT Mini only), `pivoyager.py` (PiVoyager UPS hat), `pibat.py` (PiBat I2C UPS/battery hat), `sigstr.py` (signal-strength bar display), and a Flipper Zero integration family: `PwnZero.py`, `flipperLink.py`, `wof.py` ("Wall of Flippers" detector), `img2xbm.py` (image conversion helper)

**Novelty**
`bitcoin.py` (bitcoin price display), `partymode.py`, `pwna-template-testing.py` (activates an "egirl-pwnagotchi" visual theme), `wifi_adventures.py` (achievement system), `spam_peers.py` (auto-messages newly discovered grid peers), `clock_wav_v3.py` (another clock variant), `sprite_faces.py` (sprite-based face graphics)

**Network / Security analysis - new category, several need real scoping caution**
`dns_spoof_detector.py`, `network_intrusion_detector.py`, `network_mapper.py`, `network_packet_sniffer.py`, `rogue_ap_detector.py`, `traffic_sniffer.py`, `wifi_analyser.py`, `mac_adress_logger.py`, `mac_randomizer.py`, `test_security.py` (all from Deus73's collection - passive/analytical, look fine at face value but unverified). Two are explicitly active/attack tools and should be treated with the same "your own SSIDs only" caution as your own gated plugins, not run as-is: **`wifi_jammer.py`** (sends deauth/jamming frames, no target scoping mentioned in its description) and **`wifi_password_cracker.py`** (redundant with the crack-pipeline plugins already on the list, scoping unclear).

---
*Compiled by Claude · 2026-09-28*
