# WaypointCoverage

Program a patrol route as named waypoints, and this plugin tracks live
- as you walk, not after the fact - which ones you've actually reached,
so you can confirm a perimeter test genuinely covered the whole route.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `WaypointCoverage.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. You define a list of waypoints in config: name, lat, lon, and an
   arrival radius (how close counts as "reached").
2. A background thread checks your current GPS position against every
   uncovered waypoint every `check_interval_secs`.
3. The instant you come within a waypoint's radius, it's marked
   covered immediately, timestamped, and logged - live feedback, not a
   summary generated after the session ends.
4. The on-screen display shows a running `WP N/M` counter so you can
   see progress at a glance while walking.
5. When every waypoint is covered, it logs a clear "route complete"
   line.

## Requirements

gpsd running and reachable (default `localhost:2947`).

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp WaypointCoverage.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/WaypointCoverage.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml` and fill in your
   actual waypoint coordinates.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep WaypointCoverage
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `waypoints` | `[]` | List of `{name, lat, lon, radius_meters}` |
| `check_interval_secs` | `10` | How often to check position |
| `gpsd_host` / `gpsd_port` | `localhost` / `2947` | gpsd connection |
| `log_file` | `/home/pi/waypointcoverage/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Waypoint never marked covered | GPS accuracy may not be good enough for a tight radius - try increasing `radius_meters`, or check GPS fix quality with `cgps` |
| Counter resets on restart | Coverage state is in-memory only, not persisted - restarting pwnagotchi resets progress for a fresh session by design |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/WaypointCoverage.py
```
Remove the `main.plugins.WaypointCoverage.*` block from `config.toml`
and restart.

## Scope note

Purely a location/coverage tracker - doesn't affect pwnagotchi's
attack behavior toward any network.

---
*Author: patrickato · Added via Claude · version 1.0.0*
