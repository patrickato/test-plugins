# SpeedAdaptiveScan

Adjusts bettercap's channel-hop dwell time live based on GPS-derived
speed: dwell longer per channel while stationary for more thorough
scanning, hop faster while moving so a walking/driving perimeter loop
doesn't miss APs by lingering too long on any one channel.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `SpeedAdaptiveScan.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. A background thread reads speed from gpsd's TPV reports every
   `check_interval_secs`.
2. Compares it to `speed_threshold_mps` to decide stationary vs. moving.
3. On a mode change, runs `set wifi.hopping.period <ms>` through the
   agent - a live bettercap module option, which (unlike
   `personality.*` settings) takes effect immediately without a
   restart, making continuous adjustment actually possible.
4. Logs every mode change with the speed reading that triggered it.

## A version note

The exact bettercap option name for hop timing has been
`wifi.hopping.period` in recent versions. If your pwnagotchi/bettercap
version uses a different name (some older docs reference
`wifi.hop.period`), the log will show the `set` command failing -
adjust `_apply_dwell()` to match what your version actually accepts
(check `bettercap -helpers` or the WiFi module's option list via the
bettercap web UI/API for the exact current name).

## Requirements

gpsd running and reachable (default `localhost:2947`).

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp SpeedAdaptiveScan.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/SpeedAdaptiveScan.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep SpeedAdaptiveScan
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `stationary_dwell_ms` | `500` | Dwell time while stationary |
| `moving_dwell_ms` | `150` | Dwell time while moving |
| `speed_threshold_mps` | `1.0` | Speed (m/s) above which "moving" mode kicks in |
| `check_interval_secs` | `15` | How often to check GPS speed |
| `gpsd_host` / `gpsd_port` | `localhost` / `2947` | gpsd connection |
| `log_file` | `/home/pi/speedadaptivescan/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "set wifi.hopping.period failed" in log | Your bettercap version uses a different option name - check and adjust `_apply_dwell()` |
| Never switches modes | No GPS fix, or `speed_threshold_mps` set too high/low for your actual walking pace |
| Mode flaps rapidly | Lower `check_interval_secs` isn't the fix here - raise `speed_threshold_mps` slightly, or add hysteresis if you find this happening a lot (not built in by default) |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/SpeedAdaptiveScan.py
```
Remove the `main.plugins.SpeedAdaptiveScan.*` block from `config.toml`
and restart.

## Scope note

This only adjusts scan timing/dwell - it doesn't change which APs
pwnagotchi targets or add any attack behavior.

---
*Author: patrickato · Added via Claude · version 1.0.0*
