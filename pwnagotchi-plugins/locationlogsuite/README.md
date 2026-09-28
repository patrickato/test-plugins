# LocationLogSuite

Combines four related GPS-logging ideas into one plugin, since they
all share the same underlying GPS read and reinforce each other:
**Handshake Heatmap Log**, **GPX Session Track Recorder**, **AP
First-Seen Location Log**, and **GPS Fix-Quality Log**. Built as one
plugin instead of four, per the note in the plugin ideas backlog.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `LocationLogSuite.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## What it produces (all under `base_dir`)

| Output file | What's in it |
|---|---|
| `handshake_heatmap.csv` | One row per capture: timestamp, SSID, BSSID, lat, lon, RSSI, plus fix quality (HDOP, satellite count, 2D/3D mode) |
| `ap_first_seen.csv` | One row per newly-discovered AP: timestamp, SSID, BSSID, lat, lon, plus fix quality |
| `fix_quality.csv` | A standalone periodic log of fix quality on its own cadence, independent of handshake/AP events |
| `session_track.gpx` | The physical path walked, as a standard GPX track - open it in Google Earth or any mapping tool |
| `known_bssids.json` | Internal state tracking which BSSIDs have already been logged as "first seen", so restarts don't re-log the same AP |

## How it works

1. A background thread keeps a **persistent** connection to gpsd
   (rather than reconnecting per-event like some of the simpler GPS
   plugins in this repo) and continuously updates the latest position,
   speed, and fix quality from gpsd's TPV (position) and SKY
   (HDOP/satellite) reports.
2. On every handshake, if a GPS fix is available, appends a row to the
   heatmap CSV with the current position, that capture's RSSI, and fix
   quality context.
3. On every WiFi scan update, any BSSID not already in the known set
   gets a row in the AP first-seen CSV with its discovery location and
   fix quality, then gets added to the known set (persisted to disk so
   it survives restarts).
4. Every `track_interval_secs`, the current position is appended to an
   in-memory GPX track, which gets written to disk every
   `gpx_flush_interval_secs` and again on shutdown.
5. Every `fix_quality_log_interval_secs`, an independent fix-quality
   row is logged regardless of any other event, for anyone who wants
   pure fix-quality history over time on its own.

## Why fix-quality is embedded everywhere

Cheap consumer GPS modules can drift meaningfully, so a tagged position
is only as trustworthy as the fix that produced it. Embedding HDOP/
satellite count/fix mode alongside every heatmap and AP-location entry
means you can filter out or discount low-quality fixes later, rather
than treating every tagged point as equally reliable.

## Requirements

gpsd running and reachable (default `localhost:2947`) - no additional
Python packages needed.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp LocationLogSuite.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/LocationLogSuite.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep LocationLogSuite
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `base_dir` | `/home/pi/locationlogsuite` | Where all output files live |
| `gpsd_host` / `gpsd_port` | `localhost` / `2947` | gpsd connection |
| `track_interval_secs` | `20` | How often a GPX track point is added |
| `gpx_flush_interval_secs` | `300` | How often the GPX file is written to disk |
| `fix_quality_log_interval_secs` | `60` | How often a standalone fix-quality row is logged |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| CSVs stay empty | No GPS fix yet - check `cgps`/`gpsmon` on the Pi |
| GPX file missing after a short test | It only writes every `gpx_flush_interval_secs` or on clean shutdown - lower the interval for a short test session, or expect it on `sudo systemctl restart pwnagotchi` |
| Same AP logged as "first seen" again after a restart | `known_bssids.json` wasn't preserved - check file permissions on `base_dir` |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/LocationLogSuite.py
```
Remove the `main.plugins.LocationLogSuite.*` block from `config.toml`
and restart. Output files and state are left in place.

## Scope note

Purely observational logging of GPS position alongside pwnagotchi's
own normal capture/scan activity - doesn't change what pwnagotchi
targets or attacks.

---
*Author: patrickato · Added via Claude · version 1.0.0*
