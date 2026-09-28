# Plugin List - Working Copy (Round 1)

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
*Compiled by Claude · 2026-09-28*
