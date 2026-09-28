# PMKIDFirst

Prefers the clientless PMKID grab over deauth-based 4-way handshake
capture. An AP only gets a deauth attempt after sitting PMKID-only for
a configurable grace period with no result - and even then, just one
targeted deauth to one client (not a broadcast to everyone connected).

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `PMKIDFirst.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. **Requires a config change**: set `personality.deauth = false` and
   keep `personality.associate = true`. This turns off pwnagotchi's own
   built-in deauth behavior, leaving PMKID association attempts running
   normally on their own. Without this, pwnagotchi's core loop keeps
   deauthing every epoch regardless of what this plugin does.
2. The plugin tracks, per AP, how long it's been seen without producing
   a handshake or PMKID.
3. Once `deauth_grace_period_secs` elapses for an AP with no result,
   the plugin calls the agent's deauth method itself - but only once,
   and only against a single connected client, not a broadcast.
4. If a capture comes in during the PMKID-only window, the AP is marked
   done and no deauth fallback happens at all for it.

## Why this is quieter

Pwnagotchi's default behavior runs both attack strategies against
every AP every epoch. This plugin reorders that: try the
non-disruptive method first, give it real time to work, and only use
deauth as a last resort, targeted rather than broadcast.

## Requirements

No extra packages - this plugin only calls pwnagotchi's own existing
agent methods.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp PMKIDFirst.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/PMKIDFirst.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml` - **including the
   `personality.deauth = false` line**, which is required for this
   plugin to do anything meaningful.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep PMKIDFirst
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `deauth_grace_period_secs` | `300` | Seconds an AP stays PMKID-only before one fallback deauth is attempted |

Also required, outside the plugin's own block:

| Key | Required value | Why |
|---|---|---|
| `personality.associate` | `true` | Keeps PMKID association attempts running |
| `personality.deauth` | `false` | Stops the core loop from deauthing every epoch, so this plugin controls timing |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Deauth still happening every epoch | `personality.deauth` wasn't actually set to `false`, or config wasn't reloaded - restart pwnagotchi after editing |
| Fallback deauth never fires | Grace period hasn't elapsed yet, or the AP has no connected client to target (PMKID-only APs with no clients just stay PMKID-only, which is expected) |
| `deauth fallback failed` in log | Your pwnagotchi version's `agent.deauth()` signature differs - check the logged exception and adjust `_try_deauth_fallback()` |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/PMKIDFirst.py
```
Remove the `main.plugins.PMKIDFirst.*` block from `config.toml`, and
set `personality.deauth` back to `true` if you want pwnagotchi's
default deauth behavior back.

## Scope note

This plugin tunes the *method and timing* of pwnagotchi's existing
default attack behavior (which already runs against any non-whitelisted
AP it encounters, same as stock) - it doesn't expand what pwnagotchi
targets, only makes the existing behavior quieter and more deliberate.

---
*Author: patrickato · Added via Claude · version 1.0.0*
