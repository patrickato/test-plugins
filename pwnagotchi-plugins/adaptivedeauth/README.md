# AdaptiveDeauth

Backs off deauth attempts against an AP that isn't responding, instead
of pwnagotchi hitting it the same way every epoch forever. A working AP
is never throttled - only ones that repeatedly fail to produce a
handshake get a cooldown, which doubles each time they keep failing.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `AdaptiveDeauth.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. Counts deauth attempts per AP via `on_deauthentication`.
2. Once an AP hits `initial_attempts` with no resulting handshake, it
   enters a backoff window.
3. **How the backoff is actually enforced**: pwnagotchi's core automata
   decides on its own when to call deauth - a plugin can't directly
   veto that call. So this plugin works around it by temporarily adding
   the AP's SSID to the live, in-memory whitelist for the duration of
   the backoff window (NOT persisted to `config.toml` - this is a
   short-lived hold, not a permanent change), which makes pwnagotchi's
   own core loop skip it naturally. When the window expires, the
   temporary hold is removed automatically.
4. Each time an AP fails through another full backoff cycle, the next
   cooldown doubles (up to `max_backoff_secs`), so a truly unresponsive
   AP gets left alone for longer and longer instead of endlessly
   retried.
5. The instant a handshake comes in for an AP, all backoff state for it
   is cleared immediately - success always takes priority.

## Requirements

No extra packages - uses the same live-whitelist mechanism already
used by HandshakeCompleter and WPA3Watch.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp AdaptiveDeauth.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/AdaptiveDeauth.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep AdaptiveDeauth
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `initial_attempts` | `3` | Deauth attempts allowed before backoff starts |
| `base_backoff_secs` | `300` | First cooldown length |
| `max_backoff_secs` | `3600` | Ceiling the doubling cooldown can grow to |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| AP still getting deauthed every epoch despite backoff | Live whitelist update path didn't match your pwnagotchi version's Agent config attribute - check debug log |
| Backoff never clears | `on_wifi_update` isn't firing (unlikely, it's a core event) - check the plugin loaded correctly |
| Cooldown resets to base unexpectedly | Plugin was restarted (state is in-memory only, not persisted across a pwnagotchi restart) |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/AdaptiveDeauth.py
```
Remove the `main.plugins.AdaptiveDeauth.*` block from `config.toml` and
restart. Any temporary whitelist holds are in-memory only and clear
automatically on restart regardless.

## Scope note

This throttles the *pace* of pwnagotchi's existing default deauth
behavior against whatever it already targets - it doesn't expand scope
to new APs, and its whitelist use is always temporary/in-memory, never
persisted to `config.toml`.

---
*Author: patrickato · Added via Claude · version 1.0.0*
