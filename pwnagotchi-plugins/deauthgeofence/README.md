# DeauthGeofence

A more surgical companion to GPSModeSwitch: instead of stopping
everything outside a boundary, this plugin keeps passive recon and
PMKID collection running everywhere, and only **arms deauth**
specifically while GPS shows the unit inside your configured property
boundary - disarming just that one capability outside it.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `DeauthGeofence.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How this differs from GPSModeSwitch

| | GPSModeSwitch | DeauthGeofence |
|---|---|---|
| Outside boundary | Everything stops (`wifi.recon off`) | Recon/PMKID keep running normally |
| Inside boundary | Everything resumes | Deauth becomes available |
| Use when | You want the unit fully idle away from home | You want continuous passive monitoring everywhere, but an absolute guarantee deauth only happens in your zone |

## How it works

1. **Requires `personality.deauth = false`** - this plugin needs to be
   the sole source of deauth activity so it can gate it by location.
2. A background thread reads position from gpsd and checks it against
   your boundary (radius or polygon), same mechanism as GPSModeSwitch.
3. When inside the boundary: deauth is armed, and the plugin will
   deauth one client per AP with a basic `per_ap_cooldown_secs` safety
   cooldown (for finer per-AP throttling/targeting, combine this with
   AdaptiveDeauth or TargetedKick rather than relying on this plugin's
   location gate alone).
4. When outside: deauth is disarmed entirely - `on_wifi_update` does
   nothing, and normal recon/PMKID via the core automata continues
   uninterrupted.

## Requirements

gpsd running and reachable (default `localhost:2947`) - same as
GPSModeSwitch, no extra Python packages.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp DeauthGeofence.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/DeauthGeofence.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, **including
   `personality.deauth = false`**, and set your real boundary.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep DeauthGeofence
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `center_lat` / `center_lon` / `radius_meters` | — / — / `200` | Radius boundary |
| `boundary_polygon` | `[]` | Overrides radius if set |
| `check_interval_secs` | `30` | How often to check position |
| `per_ap_cooldown_secs` | `60` | Minimum seconds between deauth attempts against the same AP while armed |
| `gpsd_host` / `gpsd_port` | `localhost` / `2947` | gpsd connection |
| `log_file` | `/home/pi/deauthgeofence/results.log` | Plain-text log |

Also required: `personality.associate = true`, `personality.deauth = false`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Deauth happening outside the boundary | `personality.deauth` wasn't actually set to `false` |
| Never arms | No GPS fix, or boundary coordinates wrong - check with `cgps`/`gpsmon` |
| Deauth too aggressive when armed | Raise `per_ap_cooldown_secs`, or layer AdaptiveDeauth on top for smarter backoff |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/DeauthGeofence.py
```
Remove the `main.plugins.DeauthGeofence.*` block from `config.toml`,
and set `personality.deauth` back to `true` if you want default
behavior.

## Scope note

This gates *whether deauth is available at all* by physical location -
it doesn't change which APs pwnagotchi targets otherwise, and outside
the boundary it's strictly quieter than pwnagotchi's default, never
more aggressive.

---
*Author: patrickato · Added via Claude · version 1.0.0*
