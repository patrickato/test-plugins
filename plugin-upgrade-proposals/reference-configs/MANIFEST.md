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

## Exact match - real config found and copied (77)
| Plugin | Reference config | Source |
|---|---|---|
| `achievements.py` | [`achievements.toml`](achievements.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/achievements.toml` |
| `age.py` | [`age.toml`](age.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/age.toml` |
| `age.py` | [`age.toml`](age.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/age.toml` |
| `agev2.py` | [`agev2.toml`](agev2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/agev2.toml` |
| `aircrackonly.py` | [`aircrackonly.toml`](aircrackonly.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/aircrackonly.toml` |
| `apprise-notify.py` | [`apprise-notify.toml`](apprise-notify.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/apprise-notify.toml` |
| `auto-hotspot.py` | [`auto-hotspot.toml`](auto-hotspot.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto-hotspot.toml` |
| `away_base.py` | [`away_base.toml`](away_base.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/away_base.toml` |
| `basiclight.py` | [`basiclight.toml`](basiclight.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/basiclight.toml` |
| `beaconify.py` | [`beaconify.toml`](beaconify.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/beaconify.toml` |
| `beacons.py` | [`beacons.toml`](beacons.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/beacons.toml` |
| `better_apfaker.py` | [`better_apfaker.toml`](better_apfaker.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_apfaker.toml` |
| `better_onlinehashcrack.py` | [`better_onlinehashcrack.toml`](better_onlinehashcrack.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_onlinehashcrack.toml` |
| `better_quickdic.py` | [`better_quickdic.toml`](better_quickdic.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/better_quickdic.toml` |
| `birthday.py` | [`birthday.toml`](birthday.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/birthday.toml` |
| `bitcoin.py` | [`bitcoin.toml`](bitcoin.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/bitcoin.toml` |
| `blemon_plugin.py` | [`blemon_plugin.toml`](blemon_plugin.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/blemon_plugin.toml` |
| `bluetoothsniffer.py` | [`bluetoothsniffer.toml`](bluetoothsniffer.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/bluetoothsniffer.toml` |
| `bt-tether.py` | [`bt-tether.toml`](bt-tether.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/bt-tether.toml` |
| `christmas.py` | [`christmas.toml`](christmas.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/christmas.toml` |
| `clock.py` | [`clock.toml`](clock.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/clock.toml` |
| `counter.py` | [`counter.toml`](counter.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/counter.toml` |
| `crack_house.py` | [`crack_house.toml`](crack_house.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/crack_house.toml` |
| `darkmode.py` | [`darkmode.toml`](darkmode.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/darkmode.toml` |
| `deauth.py` | [`deauth.toml`](deauth.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/deauth.toml` |
| `display-aircrack.py` | [`display-aircrack.toml`](display-aircrack.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display-aircrack.toml` |
| `display-password.py` | [`display-password.toml`](display-password.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display-password.toml` |
| `display_version.py` | [`display_version.toml`](display_version.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display_version.toml` |
| `educational-purposes-only.py` | [`educational-purposes-only.toml`](educational-purposes-only.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/educational-purposes-only.toml` |
| `enterprise.py` | [`enterprise.toml`](enterprise.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/enterprise.toml` |
| `expv2.py` | [`expv2.toml`](expv2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/expv2.toml` |
| `ext_wifi.py` | [`ext_wifi.toml`](ext_wifi.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/ext_wifi.toml` |
| `extWifi.py` | [`extWifi.toml`](extWifi.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/ext_wifi.toml` |
| `f0xtr0t` | [`f0xtr0t.toml`](f0xtr0t.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/f0xtr0t.toml` |
| `fix_region.py` | [`fix_region.toml`](fix_region.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/fix_region.toml` |
| `flipperLink.py` | [`flipperLink.toml`](flipperLink.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/flipperLink.toml` |
| `fortune_cookie.py` | [`fortune_cookie.toml`](fortune_cookie.toml) | `itsdarklikehell/pwnagotchi-plugins/fortune_cookie.toml` |
| `gpio_shutdown.py` | [`gpio_shutdown.toml`](gpio_shutdown.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gpio_shutdown.toml` |
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
| `mastodon.py` | [`mastodon.toml`](mastodon.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/mastodon.toml` |
| `memtemp-plus.py` | [`memtemp-plus.toml`](memtemp-plus.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/memtemp-plus.toml` |
| `more_uptime.py` | [`more_uptime.toml`](more_uptime.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/more_uptime.toml` |
| `mycracked_pw.py` | [`mycracked_pw.toml`](mycracked_pw.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/mycracked_pw.toml` |
| `mygps.py` | [`mygps.toml`](mygps.toml) | `itsdarklikehell/pwnagotchi-plugins/mygps.toml` |
| `net-pos.py` | [`net-pos.toml`](net-pos.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/net-pos.toml` |
| `pisugar2.py` | [`pisugar2.toml`](pisugar2.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pisugar2.toml` |
| `pisugar3.py` | [`pisugar3.toml`](pisugar3.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pisugar3.toml` |
| `pivoyager.py` | [`pivoyager.toml`](pivoyager.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pivoyager.toml` |
| `powerutils.py` | [`powerutils.toml`](powerutils.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/powerutils.toml` |
| `prime_gsm_hat.py` | [`prime_gsm_hat.toml`](prime_gsm_hat.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/prime_gsm_hat.toml` |
| `pwnmenu.py` | [`pwnmenu.toml`](pwnmenu.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnmenu.toml` |
| `pwnspeaker.py` | [`pwnspeaker.toml`](pwnspeaker.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnspeaker.toml` |
| `quick_rides_to_jail.py` | [`quick_rides_to_jail.toml`](quick_rides_to_jail.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/quick_rides_to_jail.toml` |
| `rtc_grid.py` | [`rtc_grid.yml`](rtc_grid.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/rtc_grid.yml` |
| `screen_refresh.py` | [`screen_refresh.toml`](screen_refresh.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/screen_refresh.toml` |
| `show_password.py` | [`show_password.toml`](show_password.toml) | `itsdarklikehell/pwnagotchi-plugins/show_password.toml` |
| `sound.py` | [`sound.toml`](sound.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/sound.toml` |
| `spotify_now_playing.py` | [`spotify_now_playing.toml`](spotify_now_playing.toml) | `itsdarklikehell/pwnagotchi-plugins/spotify_now_playing.toml` |
| `timer.py` | [`timer.toml`](timer.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/timer.toml` |
| `twitter.py` | [`twitter.toml`](twitter.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/twitter.toml` |
| `wardrive.py` | [`wardrive.toml`](wardrive.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `warwalking_trails_kml.py` | [`warwalking_trails_kml.yml`](warwalking_trails_kml.yml) | `pwnagotchi-unofficial/plugins_archive/jd-2006/pwnagotchi-plugins-scripts_JD-2006/warwalking_trails_kml/warwalking_trails_kml.yml` |
| `warwalking_trails_kml_single.py` | [`warwalking_trails_kml_single.yml`](warwalking_trails_kml_single.yml) | `pwnagotchi-unofficial/plugins_archive/jd-2006/pwnagotchi-plugins-scripts_JD-2006/warwalking_trails_kml_single/warwalking_trails_kml_single.yml` |
| `Weather.py` | [`Weather.toml`](Weather.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/Weather.toml` |
| `wpa-sec-list.py` | [`wpa-sec-list.toml`](wpa-sec-list.toml) | `pwnagotchi-unofficial/plugins_archive/dbukovac/pwnagotchi-plugins-contrib/wpa-sec-list.toml` |
| `xp.py` | [`xp.yml`](xp.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/xp.yml` |
| `xp_grid.py` | [`xp_grid.yml`](xp_grid.yml) | `pwnagotchi-unofficial/plugins_archive/Sliim/pwnagotchi-plugins/xp_grid.yml` |

## Partial match - closest sibling config found, verify by hand (32)
| Plugin | Reference config | Source |
|---|---|---|
| `aircrackonly_ng.py` | [`aircrackonly_ng.toml`](aircrackonly_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/aircrackonly.toml` |
| `auto-update_ng.py` | [`auto-update_ng.toml`](auto-update_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto-update.toml` |
| `AutoBackup v2.0` | [`AutoBackup_v2.0.toml`](AutoBackup_v2.0.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/auto_backup.toml` |
| `Discord v3.0.1` | [`Discord_v3.0.1.toml`](Discord_v3.0.1.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/discord.toml` |
| `display-password-qr.py` | [`display-password-qr.toml`](display-password-qr.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/display-password.toml` |
| `gpio_buttons_ng.py` | [`gpio_buttons_ng.toml`](gpio_buttons_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gpio_buttons.toml` |
| `gps_error.py` | [`gps_error.toml`](gps_error.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `gps_grid.py` | [`gps_grid.toml`](gps_grid.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/grid.toml` |
| `gps_live.py` | [`gps_live.toml`](gps_live.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `gpsdeasy.py` | [`gpsdeasy.toml`](gpsdeasy.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/gps.toml` |
| `gsmfake.py` | [`gsmfake.toml`](gsmfake.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/fake.toml` |
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
| `pwnagotchi_LCD_colorized_darkmode` | [`pwnagotchi_LCD_colorized_darkmode.toml`](pwnagotchi_LCD_colorized_darkmode.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/darkmode.toml` |
| `pwnmenucmd.py` | [`pwnmenucmd.toml`](pwnmenucmd.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/pwnmenu.toml` |
| `quick_rides_to_jail_ng.py` | [`quick_rides_to_jail_ng.toml`](quick_rides_to_jail_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/quick_rides_to_jail.toml` |
| `sound/shutdown_button.py` | [`sound-shutdown_button.toml`](sound-shutdown_button.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/sound.toml` |
| `wardriver-pwnagotchi-plugin` | [`wardriver-pwnagotchi-plugin.toml`](wardriver-pwnagotchi-plugin.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `wardriver_ng.py` | [`wardriver_ng.toml`](wardriver_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wardrive.toml` |
| `webcfg_ng.py` | [`webcfg_ng.toml`](webcfg_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/webcfg.toml` |
| `webgpsmap_ng.py` | [`webgpsmap_ng.toml`](webgpsmap_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/webgpsmap.toml` |
| `wigle_ng.py` | [`wigle_ng.toml`](wigle_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wigle.toml` |
| `WigleLocator` | [`WigleLocator.toml`](WigleLocator.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wigle.toml` |
| `wpa-sec_ng.py` | [`wpa-sec_ng.toml`](wpa-sec_ng.toml) | `itsdarklikehell/pwnagotchi-plugins/configs/wpa-sec.toml` |

## Generated from the plugin's own `__defaults__` dict (18)
| Plugin | Reference config | Source |
|---|---|---|
| `educational-purposes-exclusively.py` | [`educational-purposes-exclusively.toml`](educational-purposes-exclusively.toml) | `itsdarklikehell/pwnagotchi-plugins/educational-purposes-exclusively.py` |
| `mad_hatter.py` | [`mad_hatter.toml`](mad_hatter.toml) | `alienmajik/pwnagotchi_plugins/mad_hatter.py` |
| `miyagi.py` | [`miyagi.toml`](miyagi.toml) | `itsdarklikehell/pwnagotchi-plugins/miyagi.py` |
| `mqtt_plugin.py` | [`mqtt_plugin.toml`](mqtt_plugin.toml) | `itsdarklikehell/pwnagotchi-plugins/mqtt_plugin.py` |
| `partymode.py` | [`partymode.toml`](partymode.toml) | `itsdarklikehell/pwnagotchi-plugins/partymode.py` |
| `pwnaware.py` | [`pwnaware.toml`](pwnaware.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnaware.py` |
| `pwnmothership` | [`pwnmothership.toml`](pwnmothership.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnmothership.py` |
| `rgb.py` | [`rgb.toml`](rgb.toml) | `itsdarklikehell/pwnagotchi-plugins/rgb.py` |
| `rss_voice.py` | [`rss_voice.toml`](rss_voice.toml) | `itsdarklikehell/pwnagotchi-plugins/rss_voice.py` |
| `show_pwd.py` | [`show_pwd.toml`](show_pwd.toml) | `itsdarklikehell/pwnagotchi-plugins/show_pwd.py` |
| `slack.py` | [`slack.toml`](slack.toml) | `itsdarklikehell/pwnagotchi-plugins/slack.py` |
| `test_security.py` | [`test_security.toml`](test_security.toml) | `itsdarklikehell/pwnagotchi-plugins/test_security.py` |
| `themes.py` | [`themes.toml`](themes.toml) | `itsdarklikehell/pwnagotchi-plugins/themes.py` |
| `Touch_UI` | [`Touch_UI.toml`](Touch_UI.toml) | `itsdarklikehell/pwnagotchi-plugins/Touch_UI.py` |
| `tracker.py` | [`tracker.toml`](tracker.toml) | `itsdarklikehell/pwnagotchi-plugins/tracker.py` |
| `viz.py` | [`viz.toml`](viz.toml) | `itsdarklikehell/pwnagotchi-plugins/viz.py` |
| `wd_honey_Pot.py` | [`wd_honey_Pot.toml`](wd_honey_Pot.toml) | `itsdarklikehell/pwnagotchi-plugins/wd_honey_Pot.py` |
| `wifi_adventures.py` | [`wifi_adventures.toml`](wifi_adventures.toml) | `itsdarklikehell/pwnagotchi-plugins/wifi_adventures.py` |

## Generated from a scan of `self.options` usage (no `__defaults__`) (17)
| Plugin | Reference config | Source |
|---|---|---|
| `adsbsniffer.py` | [`adsbsniffer.toml`](adsbsniffer.toml) | `alienmajik/pwnagotchi_plugins/adsbsniffer.py` |
| `auto_tune.py` | [`auto_tune.toml`](auto_tune.toml) | `sniffleupagus/pwnagotchi_plugins/auto_tune.py` |
| `console.py` | [`console.toml`](console.toml) | `sniffleupagus/pwnagotchi_plugins/console.py` |
| `meshpwnstic.py` | [`meshpwnstic.toml`](meshpwnstic.toml) | `sniffleupagus/pwnagotchi_plugins/meshpwnstic.py` |
| `neurolyzer.py` | [`neurolyzer.toml`](neurolyzer.toml) | `alienmajik/pwnagotchi_plugins/neurolyzer.py` |
| `ntfy_msg.py` | [`ntfy_msg.toml`](ntfy_msg.toml) | `itsdarklikehell/pwnagotchi-plugins/ntfy_msg.py` |
| `pwn2crack.py` | [`pwn2crack.toml`](pwn2crack.toml) | `pwnagotchi-unofficial/plugins_archive/Brets0150/pwnagotchi-to-hashtopolis-plugin/pwn2crack.py` |
| `pwnwatch.py` | [`pwnwatch.toml`](pwnwatch.toml) | `itsdarklikehell/pwnagotchi-plugins/pwnwatch.py` |
| `Pwny-Tailscale` | [`Pwny-Tailscale.toml`](Pwny-Tailscale.toml) | `wpa-2/pwnagotchi-plugins/tailscale.py` |
| `skyhigh.py` | [`skyhigh.toml`](skyhigh.toml) | `alienmajik/pwnagotchi_plugins/skyhigh.py` |
| `spam_peers.py` | [`spam_peers.toml`](spam_peers.toml) | `pwnagotchi-unofficial/plugins_archive/Sniffleupagus/pwnagotchi_plugins/spam_peers.py` |
| `speak_to_me.py` | [`speak_to_me.toml`](speak_to_me.toml) | `sniffleupagus/pwnagotchi_plugins/speak_to_me.py` |
| `state-api.py` | [`state-api.toml`](state-api.toml) | `pwnagotchi-unofficial/plugins_archive/dipsylala/pwnagotchi-state-api/state-api.py` |
| `TelePwn v2.0` | [`TelePwn_v2.0.toml`](TelePwn_v2.0.toml) | `wpa-2/pwnagotchi-plugins/TelePwn/telepwn.py` |
| `web2ssh` | [`web2ssh.toml`](web2ssh.toml) | `wpa-2/pwnagotchi-plugins/web2ssh.py` |
| `wof.py` | [`wof.toml`](wof.toml) | `itsdarklikehell/pwnagotchi-plugins/wof.py` |
| `woop_woop.py` | [`woop_woop.toml`](woop_woop.toml) | `itsdarklikehell/pwnagotchi-plugins/woop_woop.py` |

## No configurable options detected - `enabled = true` only (12)
| Plugin | Reference config | Source |
|---|---|---|
| `cmd_server.py` | [`cmd_server.toml`](cmd_server.toml) | `sniffleupagus/pwnagotchi_plugins/cmd_server.py` |
| `httpserver.py` | [`httpserver.toml`](httpserver.toml) | `itsdarklikehell/pwnagotchi-plugins/httpserver.py` |
| `img2xbm.py` | [`img2xbm.toml`](img2xbm.toml) | `pwnagotchi-unofficial/plugins_archive/Matt-London/pwnagotchi-flipper/tools/img2xbm.py` |
| `pibat.py` | [`pibat.toml`](pibat.toml) | `pwnagotchi-unofficial/plugins_archive/Andyzug/PiBatPwnagotchi-Plugin/pibat.py` |
| `probenpwn.py` | [`probenpwn.toml`](probenpwn.toml) | `alienmajik/pwnagotchi_plugins/probenpwn.py` |
| `PWNAGOTCHI-CUSTOM-FACES-MOD` | [`PWNAGOTCHI-CUSTOM-FACES-MOD.toml`](PWNAGOTCHI-CUSTOM-FACES-MOD.toml) | `itsdarklikehell/pwnagotchi-plugins/extras/facemod/faces.py` |
| `pwnagotchi-fallout-faces-mod` | [`pwnagotchi-fallout-faces-mod.toml`](pwnagotchi-fallout-faces-mod.toml) | `itsdarklikehell/pwnagotchi-plugins/extras/facemod/faces.py` |
| `RaspiSyncedTime.py` | [`RaspiSyncedTime.toml`](RaspiSyncedTime.toml) | `pwnagotchi-unofficial/plugins_archive/xenDE/pwnagotchi-plugin-timesync/RaspiSyncedTime.py` |
| `sigstr.py` | [`sigstr.toml`](sigstr.toml) | `pwnagotchi-unofficial/plugins_archive/bryzz42o/Pwnagotchi-fsociety-plugins/sigstr.py` |
| `snoopr.py` | [`snoopr.toml`](snoopr.toml) | `alienmajik/pwnagotchi_plugins/snoopr.py` |
| `terminal2.py` | [`terminal2.toml`](terminal2.toml) | `itsdarklikehell/pwnagotchi-plugins/terminal2.py` |
| `theylive.py` | [`theylive.toml`](theylive.toml) | `alienmajik/pwnagotchi_plugins/theylive.py` |

## Not found - no config or source located in this environment (12)
| Plugin |
|---|
| `envtune` |
| `fix_brcmfmac.py` |
| `GitHub_Backups` |
| `pwmenu` |
| `pwnagotchi-18650` |
| `pwnagotchi-http-module` |
| `pwnagotchi-WittyPi4L3V7-plugin` |
| `pwndroid.py` |
| `PwnSpotify` |
| `Pwny-WG` |
| `Showerthoughts` |
| `wpa-cracking-project-with-pwnagotchi` |

## Already handled - moved to `plugins-wip`, not duplicated here (10)
| Plugin | Where |
|---|---|
| `banthex-de.py` | `plugins-wip` suite |
| `discoBoss.py` | `plugins-wip` suite |
| `DiscoHash` | `plugins-wip` suite |
| `handshakes-dl-hashie.py` | `plugins-wip` suite |
| `hashbot.py` | `plugins-wip` suite |
| `hashespwnagotchi.py` | `plugins-wip` suite |
| `internet-connection.py` (+ `wanmon.py`, `internet-conection.py`) | `plugins-wip` suite (internet-connection-suite, InternetConnectionNG) |
| `privacy-nightmare.py` | `plugins-wip` suite |
| `tweak_view.py` | `plugins-wip` suite (tweak-view-suite, TweakViewNG) |
| `wifi_jammer.py` | `plugins-wip` suite (wifi-jammer-suite, WifiJammerNG) |

