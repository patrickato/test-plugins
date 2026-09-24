# Pwnagotchi Gap Plugins

Original plugins that fill real gaps in the Pwnagotchi ecosystem — see
[`BUILD_LIST.md`](BUILD_LIST.md) for the roadmap (P01–P46).

## Layout
- `reference/` — the real upstream plugin API, copied verbatim (ground truth; don't edit).
- `templates/` — copy `plugin_template.py` + `plugin_template.config.toml` to start a plugin.
- `tests/` — off-Pi test harness (`conftest.py` fakes the `pwnagotchi` package) + tests.
- `<name>.py` / `<name>.config.toml` — plugins land at the top level as they're built.

## Develop
```bash
pip install -r requirements-dev.txt
PYTHONPATH= python -m pytest -q      # run from this directory
```
Read `reference/API_NOTES.md` and the project `CLAUDE.md` before writing a plugin.

## Dependencies & requirements
Install **only** what the plugins you enable need — these are per-plugin, not a global
requirement set. `Pillow`/`numpy` already ship with Pwnagotchi, so plugins that only draw
on the display need nothing extra. "✅" in the last column means the plugin is built and
tested off-Pi.

| Plugin | Python (pip) | System / binary | Hardware | Built |
|--------|--------------|-----------------|----------|:-----:|
| P01 `handshake_janitor` | none | none | none | ✅ |
| P02 `capture_grader` | none | none | none | ✅ |
| P03 `crack_reconciler` | none | none | none | ✅ |
| P04 `capture_retention` | none | none | none | ✅ |
| P05 `own_network_allowlist` | none | none | none | ✅ |
| P06 `doctor` | none | none | none | |
| P07 `sd_wear` | none | none | none | ✅ |
| P12 `battery_historian` | none *(optional `smbus2`)* | none | UPS/PiSugar (optional) | |
| P13 `fan_curve` | `RPi.GPIO` or `gpiozero` | PWM enabled | PWM-capable fan | |
| P14 `thermal_predictor` | none | none | none | |
| P18 `ha_mqtt` | `paho-mqtt` | reachable MQTT broker | none | |
| P20 `mesh_vpn_presence` | none | `tailscale` **or** `wireguard-tools` | none | |
| P21 `channel_occupancy` | none | none | none | |
| P24 `rtl433_ambient` | none | `rtl_433` binary | RTL-SDR | |
| P25 `adsb_ambient` | none | `dump1090` (JSON feed) | RTL-SDR | |
| P29 `offline_reader` | `libzim` *(or `kiwix-tools`)* | none | a `.zim` file | |
| P30 `boot_post` | none | none | none | ✅ |
| P33 `circadian_faces` | none | none | none | ✅ |
| P34 `achievements` | none | none | none | |
| P35 `daily_digest` | none *(Pillow ships already)* | none | none | |
| P36 `conflict_referee` | none | none | none | |
| P37 `eink_ghosting` | none | none | e-ink display | |
| P38 `signal_compass` | none | none | none | |
| P39 `streaks` | none | none | none | ✅ |
| P40 `multi_adapter` | none | `iw` / `ip` (usually present) | 2+ Wi-Fi adapters | |
| P41 `auto_timezone` | *(optional `timezonefinder`)* | `timedatectl` + `gpsd` | GPS | ✅ |
| P42 `wordlist_manager` | none | none | none | |
| P43 `ble_console` | `bleak` *(or `dbus-python`)* | BlueZ | BLE adapter | |
| P44 `env_sensors` | `smbus2` + per-sensor libs | I²C enabled | I²C sensor(s) | |
| P45 `auto_dim` | *(optional `smbus2`)* | backlight sysfs/GPIO | light sensor (optional) | |
| P46 `field_notes` | none | `gpsd` (optional) | GPS (optional) | ✅ |

Each plugin also states its requirements in its module docstring and in a `Requires:` line
at the top of its `config.toml`. Rows without pip/system/hardware needs run on a stock
Jayofelony image as-is.

## License
GPLv3 (see repo `LICENSE`), matching upstream Pwnagotchi.
