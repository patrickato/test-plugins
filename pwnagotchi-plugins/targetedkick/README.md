# TargetedKick

Deauths exactly one connected client per AP at a time, cycling through
clients with a cooldown between attempts - instead of pwnagotchi's
default, which can effectively knock every client on an AP offline at
once. Useful for testing reconnection behavior device-by-device without
disrupting your whole household's WiFi in one shot.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `TargetedKick.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. **Requires `personality.deauth = false`** (same as PMKIDFirst) -
   this plugin needs to be the sole source of deauth activity to
   guarantee it's ever only targeting one client.
2. For each AP with connected clients, it picks the next client in
   rotation and deauths only that one.
3. Waits `per_client_cooldown_secs` before deauthing again on that same
   AP - whether that's the same client (if there's only one) or moving
   to the next one in the list.
4. Logs how many distinct clients on that AP have been tried so far,
   so you can see rotation progress.

## Requirements

No extra packages - uses pwnagotchi's own existing agent deauth method.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp TargetedKick.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/TargetedKick.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, **including
   `personality.deauth = false`**.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep TargetedKick
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `per_client_cooldown_secs` | `60` | Minimum seconds between deauth attempts against the same AP |

Also required, outside the plugin's own block:

| Key | Required value | Why |
|---|---|---|
| `personality.associate` | `true` | Keeps normal PMKID capture running |
| `personality.deauth` | `false` | Lets this plugin be the only source of deauth so it can enforce one-at-a-time |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Multiple clients seem to drop at once | `personality.deauth` wasn't actually set to `false` - the core loop is still deauthing independently of this plugin |
| Nothing ever gets deauthed | AP has no clients in the list bettercap reports, or cooldown hasn't elapsed |
| `deauth failed` in log | Your pwnagotchi version's `agent.deauth()` signature differs - check the logged exception |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/TargetedKick.py
```
Remove the `main.plugins.TargetedKick.*` block from `config.toml`, and
set `personality.deauth` back to `true` if you want default behavior.

## Scope note

This changes *how many clients get hit per deauth event*, not which
APs get targeted - it operates on the same set of APs pwnagotchi would
already be attacking by default.

---
*Author: patrickato · Added via Claude · version 1.0.0*
