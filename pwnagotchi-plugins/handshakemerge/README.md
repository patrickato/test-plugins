# HandshakeMerge

Archives every capture snapshot for an AP and merges all of them
(across sessions, not just the current one) into one combined pcap -
so pieces of a handshake caught on different days can add up to a
complete exchange instead of needing one lucky session to catch it all
at once.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `HandshakeMerge.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. Every time `on_handshake` fires, the plugin copies a timestamped
   snapshot of that capture into an archive folder specific to that
   AP's BSSID - nothing is ever overwritten.
2. Once there are 2+ snapshots for an AP, it runs `mergecap` to combine
   all of them into one file in the merged output folder.
3. That merged file is what you'd hand to HandshakeCompleter,
   ClaudeCrackAuto, or `hcxpcapngtool` directly - it has the best shot
   at containing a complete handshake, pulling pieces from every
   capture attempt ever made against that AP.

## A note on assumptions

This plugin assumes pwnagotchi writes/overwrites a single pcap file
per AP rather than automatically keeping every session's capture
separately. Check your actual handshake directory structure before
relying on this - if your build already preserves distinct per-session
files, the archiving step here may be redundant with what you already
have, though the merge step is still useful either way.

## Requirements

```bash
sudo apt install wireshark-common
```
(If prompted about allowing non-root packet capture, answer however
you prefer - it's unrelated to this plugin, which only uses the
`mergecap` command-line tool, not live capture.)

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp HandshakeMerge.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/HandshakeMerge.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep HandshakeMerge
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `archive_dir` | `/home/pi/handshakemerge/archive` | Timestamped snapshots, one subfolder per BSSID |
| `merged_dir` | `/home/pi/handshakemerge/merged` | Combined pcap per AP |
| `log_file` | `/home/pi/handshakemerge/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `mergecap not found` in log | `wireshark-common` not installed |
| "only 1 snapshot(s), nothing to merge yet" | Normal on the first capture for a new AP - it'll merge from the second capture onward |
| Merged file doesn't seem more complete than individual snapshots | mergecap combines packets but can't fabricate missing ones - if no single snapshot ever caught a given EAPOL message, the merge won't have it either |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/HandshakeMerge.py
```
Remove the `main.plugins.HandshakeMerge.*` block from `config.toml` and
restart. Archived snapshots and merged files are left in place - delete
those folders by hand if you want them gone too.

## Scope note

This only ever archives and merges captures pwnagotchi already wrote
to disk from its normal operation - it doesn't change what pwnagotchi
targets or attacks.

---
*Author: patrickato · Added via Claude · version 1.0.0*
