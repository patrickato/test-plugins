# Full Plugin Census (Raw, Uncondensed)

Every third-party pwnagotchi plugin found in the sweep, minus:
- anything bundled directly in the jayofelony image (`auto-update`, `auto_backup`,
  `bt-tether`, `example`, `fix_services`, `gpio_buttons`, `gps`, `grid`, `logtail`,
  `memtemp`, `ohcapi`, `pisugarx`, `pwncrack`, `session-stats`, `switcher`,
  `ups_lite`, `webcfg`, `webgpsmap`, `wigle`, `wittypi`, `wpa-sec`)
- your own custom plugins already in this repo (ClaudeCrackAuto, HandshakeCompleter,
  WPA3Watch, RFComplianceGuide, PMKIDFirst, AdaptiveDeauth, TargetedKick,
  HandshakeMerge, DefaultCredCheck, HashFormatDetector, RuleMutationCrack,
  PassiveOnlyMode, GPSModeSwitch, DeauthGeofence, SpeedAdaptiveScan,
  DeadZoneFeedback, WaypointCoverage, LocationLogSuite, FailedCaptureCleanup)

No deduplication, no filtering, no scoring applied here on purpose - this is the
raw list for you to work from. Duplicate/lesser-vs-better judgment calls from the
audit doc are not applied here.

---

## Original evilsocket/pwnagotchi bundled plugins (not carried into jayofelony's image)

| Plugin | Description |
|---|---|
| `led.py` | Status LED control |
| `net-pos.py` | Network-position (geolocation via visible APs) lookup |
| `onlinehashcrack.py` | Uploads handshakes to onlinehashcrack.com |
| `paw-gps.py` | Alternate GPS plugin |
| `watchdog.py` | Restarts pwnagotchi on hang |

## jayofelony/pwnagotchi-torch-plugins (official installer repo, separate from what's pre-bundled)

| Plugin | Description |
|---|---|
| `bluetoothsniffer.py` | Logs nearby Bluetooth devices |
| `gpsdeasy.py` | Simplified gpsd-based GPS plugin |
| `handshakes-dl.py` | Web UI download of handshake files |
| `internet-connection.py` | Displays internet connectivity status |
| `memtemp-plus.py` | Enhanced memtemp with CPU frequency |
| `pwndroid.py` | Android/phone tethering integration |

## Display / UI

| Plugin | Source | Description |
|---|---|---|
| `clock.py` | dadav / kizeren | Time/calendar display |
| `darkmode.py` | Sliim (via kizeren) | Dark theme |
| `dashboard.py` / `dashboard2.py` | itsdarklikehell | Consolidated status displays |
| `display-password.py` | evilsocket-contrib, dadav, Sniffleupagus | Shows cracked passwords (Sniffleupagus version adds QR code) |
| `display-text.py`, `display_version.py` | itsdarklikehell, Teraskull | Text/version display |
| `tweak_view.py` | Sniffleupagus | Live UI element repositioning/fonts |
| `screen_refresh.py` | evilsocket-contrib, dadav | Forces display refresh |
| `screen_color_invert` | tPayne0647 | Inverts screen colors |
| `Fancygotchi` | V0r-T3x | Theme manager/GUI framework ("[In development]") |
| `pwnagotchi_LCD_colorized_darkmode` | V0r-T3x | Colorized dark-mode LCD/web UI mod |
| `PWNAGOTCHI-CUSTOM-FACES-MOD` | roodriiigooo | Custom PNG faces with transparency |
| `PwnagotchiCharacterPlugin` | CounterChicken | Change face/voice via web UI |
| `Pwan-Girl`, `Bat-Trinity` | CounterChicken | Custom anime/bat character faces |
| `pwnagotchi-fallout-faces-mod` | JD-2006 | Fallout Vault-Boy themed faces |
| `more_uptime.py` | Sniffleupagus | Cycling uptime stats display |

## GPS / Location

| Plugin | Source | Description |
|---|---|---|
| `gps-plus.py` | crahan | Enhanced GPS, configurable position, based on unmerged upstream PR |
| `gps_error.py`, `gps_fix.py`, `gps_grid.py`, `gps_live.py`, `gps_sat.py`, `rtc_grid.py`, `tracker.py`, `xp_grid.py`, `xp.py`, `waveshare_v3_touch.py` | Sliim (via kizeren) | Assorted GPS/status display set |
| `gps_more.py` | Sniffleupagus | Updates location every epoch until fix |
| `pwnagotchi-plugin-gpsd` (`gpsd.py`) | kellertk | Shows GPS location from GPSD |
| `pwnagotchi_GPSD-ng` | fmatray | Multi-device GPSD manager, NTRIP/RTK support |
| `wardriver-pwnagotchi-plugin` | cyberartemio | Logs all seen networks + uploads to WiGLE |
| `f0xtr0t` | sixt0o | Enhanced webgpsmap fork for wardriving |
| `WigleLocator` | wpa-2 | Queries WiGLE for coordinates, live maps |
| `theylive.py` | AlienMajik | GPS wardriving w/ per-handshake location logging |
| `snoopr.py` | AlienMajik | Wardriving + surveillance/tracker detection (WiFi/BLE/aircraft) |
| `skyhigh.py` | AlienMajik | Aircraft tracking via OpenSky Network API |
| `adsbsniffer.py` | itsdarklikehell / xfox64x | ADS-B aircraft data via RTL-SDR |

## Notifications / Webhooks / Social

| Plugin | Source | Description |
|---|---|---|
| `discord.py` | evilsocket-contrib, dadav | Discord notifications |
| `pwng2discord` | LOCOSP | Discord notifications |
| `pwnagotchi-discord-plugin` | charagarlnad | Discord notifications (open README issue) |
| `telegram.py` | evilsocket-contrib, dadav | Telegram notifications |
| `telegram.py` (standalone) | wpa-2 | "Simple interactive" Telegram plugin |
| `TelePwn` v2.0 | wpa-2 | Advanced Telegram control and notifications |
| `twitter.py` | evilsocket-contrib, dadav | Twitter posting |
| `mastodon.py` | evilsocket-contrib, dadav | Mastodon posting |
| `Discord` v3.0.1 | wpa-2 | Uploads pcaps, maps locations, tracks sessions |
| `DiscoHash` | flamebarke | Converts pcaps to hashcat 22000, analyzes, grabs GPS, posts to Discord |
| `PwnSpotify` | itsOwen | Displays currently-playing Spotify track |
| `rss_voice.py` | Sniffleupagus | Replaces canned voice lines with RSS feed content |
| `Showerthoughts` | NoxiousKarn | Random r/Showerthoughts RSS headlines while idle |
| `speak_to_me.py` | Sniffleupagus | TTS announcements of pwning events |

## Attack / Capture behavior

| Plugin | Source | Description |
|---|---|---|
| `aircrackonly.py` | evilsocket-contrib, dadav | Verifies valid handshake via aircrack before keeping pcap |
| `quickdic.py` | evilsocket-contrib, dadav | Dictionary cracking driver |
| `pwnagotchi_fast_dictionary` | nothingbutlucas | "Improved version of quickdic.py" |
| `quick_rides_to_jail` | xfox64x | Adds cracked APs to wpa_supplicant config automatically |
| `hashie.py` | evilsocket-contrib, dadav | Handshake→hash conversion |
| `hashie-hcxpcapngtool.py` | PwnPeter | Updated for 2021 hcxtools + new hashcat formats |
| `handshakes-dl-hashie.py` | PwnPeter | Downloads + converts in one step |
| `deauth.py` | dadav | Deauth behavior |
| `hulk.py` | dadav | Network stress-testing |
| `apfaker.py` | dadav | AP spoofing/faking |
| `enable_assoc.py` / `enable_deauth.py` | Sniffleupagus | Toggle assoc/deauth personality behavior live without restart |
| `cuffs.py` | itsdarklikehell | Restricts attacks to a whitelist of APs |
| `probenpwn.py` | AlienMajik | Aggressive handshake/PMKID capture, quiet assoc attacks, WPS PIN extraction, adaptive rate limiting |
| `neurolyzer.py` | AlienMajik | MAC randomization, WIDS/WIPS evasion |
| `wpa-cracking-project-with-pwnagotchi` | energydrinksjunkie | University thesis project, uploads handshakes to a companion Hashcat web app |
| `pwnagotchi-to-hashtopolis-plugin` | Brets0150 | Hashtopolis integration |
| `crack_house.py` | itsdarklikehell / V0r-T3x variants | Displays nearest cracked network |
| `meshpwnstic.py` | Sniffleupagus | Remote control (deauth/assoc/status) over Meshtastic LoRa |

## Web UI / API / Remote control

| Plugin | Source | Description |
|---|---|---|
| `web2ssh` | wpa-2 | Lightweight web shell-command executor |
| `Pwny-WG` | wpa-2 | WireGuard VPN + handshake sync over SSH |
| `Pwny-Tailscale` | wpa-2 | Tailscale remote connectivity, no port-forwarding needed |
| `pwnagotchi-http-module` | qLJB | Serves handshake pcaps via simple HTTP server on port 8000 (targets Bookworm image) |
| `pwmenu` (`A_pwmenu.py`) | newfpv | Mobile-first field console for captures/cracking/exports/whitelists |
| `pwnmothership` | ad | (description not visible) |
| `GitHub_Backups` | wpa-2 | Syncs config to GitHub/Gitea |

## Auto-update / Maintenance / Backup

| Plugin | Source | Description |
|---|---|---|
| `auto_backup_ng.py` | evilsocket-contrib, dadav, itsdarklikehell | Adds retention/garbage collection over baseline auto_backup |
| `AutoBackup` v2.0 | wpa-2 | Retention policy backups |
| `fix_brcmfmac.py` | Sniffleupagus | Reloads brcmfmac kernel module instead of full reboot on WiFi driver hangs |
| `event_multithreading_for_plugins` | xfox64x | Core plugin-system patch adding multithreading/event queueing |
| `pwnagotchi-postinstall` | HugeFrog24 | Shell scripts: usbnet SSH patch, package freeze, screen-settings enforcement, BT tether enforcement, fastfetch install |
| `monstart` / `monstop` | xfox64x | Start/stop monitor-mode scripts (hardcoded interface names) |

## Hardware-specific (e-paper/LCD/fan/battery/GPIO)

| Plugin | Source | Description |
|---|---|---|
| `gpio_buttons_ng.py`, `gpio_shutdown.py` | dadav / itsdarklikehell | GPIO button/shutdown handling |
| `buttonshim.py` | evilsocket-contrib, dadav | Pimoroni Button SHIM support |
| UPS Lite v1.3 (gist) | LouDnl | UPS Lite plugin |
| `pwnagotchi-plugin-pisugar2` | kellertk | I2C battery data from PiSugar 2 |
| `pwnagotchi-plugin-pisugar3` | nullm0ose ("improved"), fork by taiyonemo (orig. pwny0) | PiSugar 3 support |
| `pisugar3.py` | V0r-T3x (via kizeren) | PiSugar 3 support |
| `pwnagotchi-WittyPi4L3V7-plugin` | smackanoodle | Battery info + button support for WittyPi4L3V7 |
| `mad_hatter.py` | AlienMajik | Universal UPS battery monitor w/ auto-shutdown |
| `Pwnagotchi_Waveshare_2.66inch` | kuzmin-no | Waveshare 2.66" e-paper (B) patch, 296x152, SPI |
| `Pwnagotchi-WS-V3-V4` | N3tm4t3 | Waveshare V3/V4 e-ink support |
| `Pwnagotchi-Waveshare-V3-Fix` | Jona-Walpert | Fix guide for Waveshare 2.13" hat |
| `Pwnagotchi-on-waveshare-v4` | Arnxb007 | Waveshare V4 e-ink + web interface enabled |
| `Touch_UI` | Sniffleupagus | Touchscreen UI support |
| `gsmfake` | xfox64x | Waveshare GSM/GPRS/GNSS Bluetooth Hat + gpsfake |
| `blemon_plugin.py` | Sniffleupagus | Counts/tracks max simultaneous BLE devices |
| `bluetoothsniffer.py` | jayofelony-torch (listed above too) | Logs nearby Bluetooth MACs/names |
| `morse_code.py` | Sniffleupagus | Flashes LED status via Morse code |
| `fix_region.py` | V0r-T3x (via kizeren) | Regulatory-region fix |
| `pwnagotchi-18650` (case design) | gb1035 | 18650 battery case - hardware, not software |

## Novelty / Games / Personality

| Plugin | Source | Description |
|---|---|---|
| `age.py` / `agev2.py` | dadav / itsdarklikehell | Tracks device "age"/strength |
| `age.py` (different plugin, same name) | AlienMajik | Narrative "cyber-legend" prestige/lore system |
| `exp.py` / `expv2.py` | itsdarklikehell | XP for captured handshakes |
| `achievements.py` | itsdarklikehell | Achievement badges |
| `counter.py` | itsdarklikehell | Tallies assoc/deauth attempts |
| `christmas.py` | evilsocket-contrib, dadav | Holiday theme |
| `fortune_cookie.py` | itsdarklikehell | Random fortune messages |
| `birthday.py` | itsdarklikehell; standalone by nullm0ose | Displays device creation date/age |
| `Weather.py` | itsdarklikehell | Weather display |
| `IPDisplay.py` | itsdarklikehell | IP address display |
| `Experience-Plugin-Pwnagotchi` | GaelicThunder | XP/experience system |
| `miyagi.py` | Sniffleupagus | "Training module," reduces laziness, manages brain backups |
| `envtune` | adi170-alt | Environment-aware personality tuner (EMA smoothing, reward-revert, best-settings memory) |

## Network / Security analysis (misc analytical)

| Plugin | Source | Description |
|---|---|---|
| `beacons.py` | itsdarklikehell | Broadcasts pwnagotchi state via WiFi beacon frames |
| `banthex.py` | V0r-T3x | Auto-uploads handshakes to banthex.de |
| `dropbox_ul.py` | itsdarklikehell | Uploads handshakes to Dropbox |
| `beaconify.py`, `instattack.py`, `pwnaware.py` | itsdarklikehell | (partial descriptions only) |
| `auto-hotspot.py` | itsdarklikehell | Creates a WiFi hotspot in manual mode |

## Aggregator / multi-plugin repos (broad collections - many plugins above are pulled from these)

| Repo | Notes |
|---|---|
| itsdarklikehell/pwnagotchi-plugins | 80+ plugin files, one of the largest single collections |
| kizeren/pwnagotchi-plugins | Curated re-hosting organized by original author |
| evilsocket/pwnagotchi-plugins-contrib | Official-adjacent, dormant; mirrored (ZTube, Gitea) |
| xfox64x/pwnagotchi_plugins | 7 distinct plugins |
| AlienMajik/pwnagotchi_plugins | 8 advanced plugins |
| wpa-2/Pwnagotchi-Plugins | AutoBackup v2, GitHub_Backups, Discord v3.0.1, Pwny-WG, Pwny-Tailscale, TelePwn v2.0, web2ssh, WigleLocator |
| Sniffleupagus/pwnagotchi_plugins | 13 utility plugins |
| Pwnagotchi-Unofficial/plugins_archive | Meta-archive aggregating 80+ contributors' repos by folder |
| Teraskull/pwnagotchi-community-plugins | Newer unification effort (autocrack.py, clock.py, display_version.py), 79 stars |
| crahan/pwnagotchi-plugins | gps-plus, memtemp-plus (unmerged upstream PRs) |
| PwnPeter/pwnagotchi-plugins | hashie-hcxpcapngtool.py, handshakes-dl-hashie.py |
| SHUR1K-N/Project-Pwnag0dchi (+ fork ingui-n/pwnagotchi) | Customized plugins & configurations + guides |
| rohanday3/pwnagotchi-plugins (+ duplicate pwnagotchi_plugins-1) | Personal collection |
| avipars/Pwnagotchi-Plugins-2 | Companion to avipars/pwn-to-own guide repo |
| Deus73/pwnagotchi-plugins | Custom Pwnagotchi python scripts |
| Sliim/pwnagotchi-plugins | Source for many entries re-hosted by kizeren |
| hannadiamond/pwnagotchi-plugins | Personal collection |
| vanshksingh/Pwnagotchi_Plugins | Plugins for V4 display |
| gallis-local/pwnagotchi-plugins | "Bring them all together" |

## Misc / uncategorized (surfaced but not fully inspected)

| Item | Notes |
|---|---|
| RasTacsko/DubRecen-PwnGang-Build-Guides | Settings/config/plugins collection, build-guide oriented |
| Th4ntis/CyberSecNotes | Wardriving/pwnagotchi.md guide referencing plugins, not a plugin repo itself |
| Pnwcomputers/ULTIMATE-CYBERSECURITY-MASTER-GUIDE | pwnagotchi_cheatsheet.md, guide referencing wpa-sec plugin |

---

This is the unfiltered list. Tell me what to cut and I'll condense it down to
whatever's left.

---
*Compiled by Claude · 2026-09-28*
