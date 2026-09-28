# WPA3Watch

Passively classifies every AP pwnagotchi's radio sees by encryption
type (WPA2, WPA3-SAE-only, mixed WPA2/WPA3, enterprise, open, WEP), and
logs it — useful recon documentation on its own. For your own networks,
it can also recognize when a WPA3-SAE-only AP simply can't be attacked
by handshake-capture methods, and stop pwnagotchi from wasting deauths
on it.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `WPA3Watch.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. On every periodic WiFi scan update pwnagotchi already does (no extra
   scanning traffic), the plugin reads the encryption/authentication/
   cipher fields bettercap already parsed from each AP's beacon and
   classifies it as one of: `wpa3_only`, `wpa2_wpa3` (transition mode),
   `wpa2_psk`, `enterprise`, `open`, `wep`, or `unknown`.
2. Every newly-seen AP, or one whose classification changes, gets
   logged with SSID, BSSID, channel, signal strength, and
   classification.
3. If an SSID is in your `my_networks` list **and** classifies as
   `wpa3_only`, and `auto_whitelist_wpa3 = true`, the plugin adds it to
   pwnagotchi's real `main.whitelist` (live best-effort + persisted to
   `config.toml`) — because pure WPA3-SAE doesn't hand you a crackable
   4-way exchange the way WPA2-PSK does, so there's nothing this
   project's crack pipeline (ClaudeCrackAuto / HandshakeCompleter) can
   do with it. Whitelisting it stops pwnagotchi from continuing to
   deauth an AP it can't usefully make progress against.
4. Anything not in `my_networks` is classified and logged only —
   nothing about pwnagotchi's behavior toward those networks changes.

## Why WPA3-SAE is different

WPA2-Personal's 4-way handshake can be captured and cracked offline
against a wordlist because the exchange is derived directly from the
PSK. WPA3's SAE (Simultaneous Authentication of Equals, aka "Dragonfly")
does not expose that same offline-crackable exchange — an eavesdropper
capturing the SAE exchange doesn't get a usable dictionary-attack
target the way they would with a WPA2 handshake. (There have been
narrower implementation-specific attacks like "Dragonblood" against
buggy SAE implementations, but that's a different, much more involved
line of attack than this project's pipeline — not something this
plugin attempts.) Practically: if your own AP shows up as
`wpa3_only`, classic pwnagotchi handshake-capture is the wrong tool for
testing it, full stop.

## Requirements

```bash
pip3 install toml --break-system-packages   # only needed if auto_whitelist_wpa3 = true
```
No other dependencies — classification uses data bettercap already
collects.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp WPA3Watch.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/WPA3Watch.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml` to
   `/etc/pwnagotchi/config.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep WPA3Watch
   ```
5. Watch classifications come in:
   ```bash
   tail -f /home/pi/wpa3watch/results.log
   ```
   Full running list (including channel/RSSI/first-seen) is in
   `/home/pi/wpa3watch/seen_aps.json`.

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `my_networks` | `[]` | Your own SSIDs — only used for the auto-whitelist behavior |
| `auto_whitelist_wpa3` | `false` | Whitelist your own WPA3-only APs automatically |
| `log_file` | `/home/pi/wpa3watch/results.log` | Plain-text classification log |
| `state_file` | `/home/pi/wpa3watch/seen_aps.json` | Full record of every AP seen and its classification |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Everything classifies as `unknown` | Your bettercap version reports encryption/authentication fields under different key names — check `sudo journalctl -u pwnagotchi | grep WPA3Watch` at debug level for the raw AP dict, then adjust `_classify()` |
| Own WPA3 AP never gets whitelisted | Check `my_networks` spelling matches exactly (case-insensitive), and that `auto_whitelist_wpa3 = true` |
| `toml` import error in log | `pip3 install toml --break-system-packages` |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/WPA3Watch.py
```
Remove the `main.plugins.WPA3Watch.*` block from `config.toml` and
restart. Any SSIDs it already added to `main.whitelist` stay there —
remove by hand if you want pwnagotchi to resume normal behavior toward
them (though as noted above, handshake-capture won't do anything useful
against a true WPA3-SAE-only AP regardless).

## Scope note

Classification is passive and applies to every AP pwnagotchi sees —
that's just organizing information pwnagotchi already picked up from
public beacon broadcasts, same as watching a WiFi signal-strength meter.
The only active behavior (editing `main.whitelist`) is opt-in and
limited strictly to SSIDs you list under `my_networks`.

---
*Author: patrickato · Added via Claude · version 1.0.0*
