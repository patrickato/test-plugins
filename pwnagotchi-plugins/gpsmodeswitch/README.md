# GPSModeSwitch

Automatically drops pwnagotchi to fully dormant the moment GPS shows
it's left your property boundary, and resumes normal operation once
it's back inside. Boundary can be a simple center point + radius, or a
polygon for a more precise irregular shape.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `GPSModeSwitch.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. A background thread reads position directly from **gpsd** (the
   standard GPS daemon your GPS HAT already runs through) every
   `check_interval_secs`, independent of pwnagotchi's own GPS plugin
   internals.
2. Checks the position against your configured boundary - either
   distance from a center point (`radius_meters`), or, if
   `boundary_polygon` is set, a proper point-in-polygon test for a
   more precise irregular shape.
3. **When it leaves the boundary**: runs the bettercap command
   `wifi.recon off` directly through the agent - this is the same
   mechanism pwnagotchi's own core automata uses to drive bettercap,
   and it stops channel hopping and all recon/attack activity outright.
4. **When it re-enters**: runs `wifi.recon on` to resume normal
   operation.
5. Every transition is logged.

## Why this approach instead of toggling personality settings

`personality.deauth`/`personality.associate` are only read once at
pwnagotchi startup (see PassiveOnlyMode's README) - they can't be
flipped live from a plugin. Calling `wifi.recon off/on` directly is a
real, live lever: without recon running, there's nothing for
pwnagotchi to associate or deauth against at all, so it's a genuinely
effective dormancy switch rather than a setting that only takes effect
after a restart.

## Requirements

gpsd must be running and reachable - already the case on essentially
every pwnagotchi GPS HAT setup by default (`localhost:2947`). No
additional Python packages needed; this plugin talks to gpsd directly
over its JSON socket protocol rather than requiring the `gps` Python
library.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp GPSModeSwitch.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/GPSModeSwitch.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml` and set your actual
   property coordinates (radius is simplest to start with).
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep GPSModeSwitch
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `center_lat` / `center_lon` | — | Center point for radius boundary |
| `radius_meters` | `200` | Radius around center point |
| `boundary_polygon` | `[]` | List of `[lat, lon]` pairs; if set, overrides the radius option |
| `check_interval_secs` | `30` | How often to check position |
| `gpsd_host` / `gpsd_port` | `localhost` / `2947` | gpsd connection |
| `log_file` | `/home/pi/gpsmodeswitch/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Never triggers | No GPS fix yet (check `cgps` or `gpsmon` on the Pi to confirm gpsd is actually getting a fix), or boundary coordinates are wrong |
| `agent.run(...) failed` in log | Your pwnagotchi version's Agent class may not expose `run()` the same way - check the logged exception and adjust `_set_dormant()` |
| Doesn't resume after returning | Check `check_interval_secs` isn't too long, and confirm the log shows a "re-entered" line |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/GPSModeSwitch.py
```
Remove the `main.plugins.GPSModeSwitch.*` block from `config.toml` and
restart. If the unit was dormant at uninstall time, restart pwnagotchi
to guarantee normal operation resumes.

## Scope note

This is a blanket activity switch tied to physical location, not to
any specific network - it doesn't change which APs pwnagotchi targets
when active, only whether it's active at all based on where the unit
physically is.

---
*Author: patrickato · Added via Claude · version 1.0.0*
