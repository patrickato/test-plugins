# Master Plugin List

Everything found across both research rounds, minus jayofelony-bundled
defaults, your own custom plugins, and everything already cut for being
either superseded-by-bundled or (in one case) a pure name/architecture
non-issue. One bullet per plugin, by category, alphabetical within each
category. Ready for the next removal round.

A few plugins are genuinely the same file re-hosted by several people
(this ecosystem re-mirrors constantly) - those are one bullet with the
aliases noted, not one bullet per mirror.

## Elimination log

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

---

## Attack / Capture behavior

- **aircrackonly.py** - Verifies a pcap actually contains a handshake/PMKID; deletes it if not
- **apfaker.py** - Creates fake APs
- **banthex.py** / **banthex-de.py** - Auto-uploads handshakes to banthex.de
- **better_apfaker.py** - Creates fake APs (alternate implementation)
- **better_onlinehashcrack.py** - Uploads handshakes to onlinehashcrack.com (alternate implementation)
- **better_quickdic.py** - Quick dictionary scan; optionally sends found passwords as QR code/text to a Telegram bot
- **cuffs.py** - Restricts the pwnagotchi to only attack specified APs
- **deauth.py** - Counts successful deauth attacks for the session
- **discoBoss.py** - Configurable rule engine for managing deauth ("disco") behavior
- **DiscoHash** - Converts pcaps to hashcat 22000 format, analyzes them, grabs GPS, posts results to Discord
- **dropbox_ul.py** - Auto-uploads handshakes to a Dropbox app
- **educational-purposes-exclusively.py** / **educational-purposes-only.py** - Auto-authenticates to known networks and performs internal network recon (no target scoping)
- **enable_assoc.py** / **enable_deauth.py** - Toggles assoc/deauth behavior live without a restart
- **enterprise.py** - Attempts to obtain credentials from enterprise networks when bored
- **handshakes-dl-hashie.py** - Downloads handshake captures from the web UI and converts them in one step
- **handshakes-dl.py** - Downloads handshake captures from the web UI (also distributed as jayofelony's official installer plugin)
- **hashbot.py** - Discord bot companion to DiscoHash; dumps hashes for N APs on request
- **hashespwnagotchi.py** - Uploads handshakes to hashes.pw
- **hashie-hcxpcapngtool.py** - Converts pcaps to crackable hash formats via hcxpcapngtool, updated for modern hcxtools/hashcat formats
- **hashieclean.py** - hashie variant that also purges pcaps that can't be converted to a hash
- **hp_educational-purposes.py** - Combined honeypot + auto network-authentication plugin
- **hulk.py** - Puts pwnagotchi into an "always aggressive" attack mode
- **instattack.py** - Launches an immediate associate/deauth attack the instant a device is spotted
- **meshpwnstic.py** - Remote deauth/assoc/status control over a Meshtastic LoRa radio
- **mycracked_pw.py** - Grabs all cracked passwords, generates WiFi QR codes and a wordlist
- **neurolyzer.py** - MAC randomization, WIDS/WIPS evasion
- **nextcloud.py** - Auto-uploads handshakes to a Nextcloud WebDAV endpoint
- **potfilesorter.py** - Sorts a hashcat potfile into a usable wpa_supplicant.conf
- **privacy-nightmare.py** - Passive metadata "eavesdropping" plugin - provocatively named, read the source before trusting
- **probenpwn.py** - Aggressive handshake/PMKID capture, quiet assoc attacks, WPS PIN extraction, adaptive rate limiting
- **pwn2crack.py** (aka pwnagotchi-to-hashtopolis-plugin) - Converts handshakes to Hashcat 22000 and creates a hashlist in Hashtopolis
- **pwnagotchi_fast_dictionary** - Improved version of quickdic.py, per its own README
- **quick_rides_to_jail.py** - Dictionary-cracks handshakes, then auto-updates wpa_supplicant with results
- **quickdic.py** - Runs a quick dictionary scan against captured handshakes
- **wd_honey_Pot.py** - Honeypot that detects OTHER pwnagotchis performing deauths nearby (defensive, not an attack tool)
- **woop_woop.py** - Auto-authenticates to known networks, performs internal recon, saves wifi info to wpa_supplicant
- **wpa-cracking-project-with-pwnagotchi** - Uploads handshakes to a companion university-thesis Hashcat web app

## Display / UI

- **clock.py** / **clock_wav_v3.py** - Clock/calendar display
- **crack_house.py** (+ a "-dev" variant) - Displays the closest cracked network and its password
- **darkmode.py** - Dark theme
- **dashboard.py** / **dashboard2.py** - Consolidated status display (clock, deauth counter, memtemp, cracked-handshake counter, internet status)
- **display-aircrack.py** - Shows whether aircrack is currently running
- **display-password.py** / **display-password-qr.py** - Displays recently cracked passwords (QR variant adds a QR code)
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
- **wardriver-pwnagotchi-plugin** - Logs all seen networks, uploads to WiGLE
- **warwalking_trails_kml.py** / **warwalking_trails_kml_single.py** - Generates KML trail files from wardriving data, for Google Earth
- **WigleLocator** - Queries WiGLE for AP coordinates, live maps

## Hardware-specific

- **basiclight.py** - GPIO traffic-light-style signal lights
- **blemon_plugin.py** - Counts/tracks max simultaneous BLE devices
- **bluetooth_scanner.py** - Scans for and logs nearby Bluetooth devices
- **bluetoothsniffer.py** - Logs nearby Bluetooth MACs/names/counts to a JSON file
- **fix_region.py** - Changes the iw region to unlock additional channels
- **flipperLink.py** - Connects pwnagotchi to a Flipper Zero
- **gpio_buttons_ng.py** - GPIO button support (next-gen/torch variant)
- **gpio_shutdown.py** - GPIO-triggered clean shutdown
- **gsmfake.py** - Feeds bettercap fake GPS coordinates from a GSM/GPRS modem when real GPS is unavailable
- **img2xbm.py** - Converts images to XBM format for a Flipper Zero display
- **mad_hatter.py** - Universal UPS battery monitor with auto-shutdown
- **memtemp-plus.py** - Memory/CPU usage + temperature display, adds CPU frequency (jayofelony's official installer plugin)
- **morse_code.py** - Flashes the status LED in Morse code
- **pibat.py** - Voltage indicator for the PiBat I2C UPS/battery hat
- **pisugar2.py** / **pisugar3.py** - Voltage/percentage indicator for PiSugar 2 / PiSugar 3
- **pivoyager.py** - PiVoyager UPS hat support
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
- **auto_backup_ng.py** - Backs up files when internet is available, with retention/garbage collection
- **AutoBackup v2.0** - Local backup with a retention policy
- **away_base.py** / **home_base.py** - Watches for known networks and connects when available; `home_base` targets your home network specifically
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
- **mac_randomizer.py** - Randomizes the device's own MAC address
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
- **pwnassistant.py** - Voice control commands via a connected microphone
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
- **exp.py** / **expv2.py** - Awards XP for each captured handshake
- **Experience-Plugin-Pwnagotchi** - XP/experience system
- **fortune_cookie.py** - Displays random fortune-cookie messages
- **IPDisplay.py** - Displays the device's IP address
- **miyagi.py** - "Training module" novelty plugin, manages brain backups
- **partymode.py** - Novelty party mode
- **spam_peers.py** - Auto-messages newly discovered grid peers
- **voice_gamer.py** - Downloads and replaces voice.py with a custom version
- **Weather.py** - Displays the weather forecast
- **wifi_adventures.py** - Achievement system themed around "WiFi adventures"
- **xp.py** / **xp_grid.py** - XP/leveling system with peer level-sharing (separate implementation from exp.py)

## Original evilsocket bundled (remainder - not superseded by anything jayofelony bundles)

- **led.py** - Status LED control
- **net-pos.py** - Network-position (AP-based) geolocation lookup

## Web UI / API / Remote control

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

---
*Compiled by Claude · 2026-09-28*
