# HashFormatDetector

Inspects each capture and routes it to the correct cracking pathway,
instead of assuming every capture is a modern `hashcat -m 22000` job.
WEP gets flagged for `aircrack-ng` (a completely different attack
method), WPA/WPA2/PMKID gets converted and confirmed for hashcat mode
22000, and open networks get flagged as nothing to crack at all.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `HashFormatDetector.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. On every `on_handshake` event, checks the AP's broadcast encryption
   field first:
   - **WEP** → routed to `aircrack-ng` (WEP is a statistical
     initialization-vector attack, not a hash to crack with hashcat at
     all - completely different tool and method)
   - **No encryption** → routed as `none`, nothing to crack
   - **WPA/WPA2/WPA3-transition** → runs `hcxpcapngtool` to confirm
     there's actual crackable handshake/PMKID material, and converts
     it to `.hc22000` for hashcat mode 22000 (the current unified mode
     - older modes like 2500/16800 are deprecated on recent hashcat
     and this plugin doesn't bother with them)
2. Writes a `.route` sidecar file next to the original capture stating
   what was detected and what to do with it, so you (or another
   plugin) don't have to re-inspect it later.
3. Logs every classification.

## What this plugin does NOT do

It doesn't run `hashcat` or `aircrack-ng` itself - it only classifies
and prepares the right input format. Actually running the crack is
ClaudeCrackAuto's job for the WPA/PMKID path; WEP cracking with
aircrack-ng isn't automated by any plugin in this repo yet (it's a
different, IV-collection-based attack that behaves quite differently
from a wordlist crack).

## Requirements

```bash
sudo apt install hcxtools
```

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp HashFormatDetector.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/HashFormatDetector.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep HashFormatDetector
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `output_dir` | `/home/pi/hashformatdetector/routed` | Where converted `.hc22000` files land |
| `log_file` | `/home/pi/hashformatdetector/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Everything routes to `unknown` | `hcxtools` not installed |
| WEP AP not detected as WEP | Your bettercap version reports the encryption field differently than expected - check the raw `access_point` dict at debug level |
| `.route` sidecar missing | Check file write permissions on the handshake directory |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/HashFormatDetector.py
```
Remove the `main.plugins.HashFormatDetector.*` block from `config.toml`
and restart. `.route` sidecar files and converted `.hc22000` files are
left in place.

## Scope note

Purely classification/routing of captures pwnagotchi already wrote to
disk from its own normal operation - takes no action on any network
itself.

---
*Author: patrickato · Added via Claude · version 1.0.0*
