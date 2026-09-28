# DefaultCredCheck

Identifies a router's likely vendor from its BSSID's OUI (the
vendor-assigned first half of the MAC address, broadcast in every
beacon frame) and flags whether that vendor has a history of default
or predictable credentials - purely passive, no login attempts, no
password guessing.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `DefaultCredCheck.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. For every AP pwnagotchi sees, reads the BSSID's OUI (first 3 bytes)
   and checks it against a small built-in table of common consumer
   router vendors.
2. If there's a match, logs the vendor and a note on what's publicly
   known about that vendor's default-credential or default-SSID
   conventions.
3. If the SSID is on your `my_networks` list, the log line is prefixed
   `OWN NETWORK -` so it's easy to find what's actionable for you.
4. That's it - this plugin never attempts a login, never guesses a
   password, and never touches anything beyond the beacon info
   pwnagotchi already receives.

## Where to get actual default-credential values

This plugin tells you *which vendor/pattern might apply* - it doesn't
ship or guess actual passwords. For real default-credential lists to
test against your **own** router, see
[SecLists' Default-Credentials directory](https://github.com/danielmiessler/SecLists/tree/master/Passwords/Default-Credentials),
organized by vendor.

**Worth knowing**: modern ISP-issued routers (recent Xfinity, Spectrum,
etc.) typically generate a unique per-device key rather than a shared
default - this check is most useful against older or non-ISP consumer
routers, not current ISP-supplied gear.

## Coverage

The built-in vendor table covers a handful of common consumer brands
(Netgear, D-Link, Linksys, TP-Link, ASUS, Ubiquiti) by a sample of
their OUI prefixes - it is intentionally small and not exhaustive.
Extend `OUI_VENDOR_NOTES` in the plugin file with more OUIs as you
encounter unrecognized vendors you want covered (the IEEE's full public
OUI registry is the authoritative source if you want to look one up:
https://standards-oui.ieee.org/).

## Requirements

None - uses only the beacon data pwnagotchi already receives.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp DefaultCredCheck.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/DefaultCredCheck.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep DefaultCredCheck
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `my_networks` | `[]` | Your own SSIDs, flagged more prominently in the log |
| `log_file` | `/home/pi/defaultcredcheck/results.log` | Plain-text log |
| `state_file` | `/home/pi/defaultcredcheck/seen.json` | Every AP checked so far, to avoid re-logging the same one |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Nothing ever logged | Either no AP nearby matches the small built-in vendor table, or none are new since last check (state file dedupes) |
| Own network not flagged as "OWN NETWORK" | SSID spelling in `my_networks` doesn't exactly match (case-insensitive, but check for typos/extra spaces) |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/DefaultCredCheck.py
```
Remove the `main.plugins.DefaultCredCheck.*` block from `config.toml`
and restart.

## Scope note

Purely passive and read-only - applies to every AP pwnagotchi sees
since it never takes any action, just reads and logs already-public
beacon information. Nothing here attempts to access anything.

---
*Author: patrickato · Added via Claude · version 1.0.0*
