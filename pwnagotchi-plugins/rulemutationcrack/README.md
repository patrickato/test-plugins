# RuleMutationCrack

For your own whitelisted networks: tries a plain wordlist crack first,
and if that fails, retries with a hashcat rule file applied on top of
the same wordlist - covering common real-world password mutations
(appended digits, capitalization changes, leetspeak substitutions)
that a flat dictionary pass alone would miss.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `RuleMutationCrack.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. Only acts on SSIDs listed in `targets` (your own) - same scoping as
   ClaudeCrackAuto and HandshakeCompleter. Everything else is left
   completely alone.
2. Converts the handshake to `.hc22000` via `hcxpcapngtool`.
3. Runs a fast plain-wordlist hashcat pass first.
4. If that finds nothing, runs a second pass with `-r <rules_file>`
   applied - hashcat generates mutated variants of each wordlist entry
   on the fly (e.g. `password` → `Password1`, `p4ssword`, `password!`)
   without needing a pre-mutated, much larger wordlist file.
5. Logs which pass (if either) found the password.

## Why rules instead of a bigger wordlist

A rule file lets hashcat apply the same set of realistic mutations to
every word in your list at crack time, rather than you needing a
wordlist that already contains every variant. It's a standard
professional technique - far more efficient than trying to
pre-generate every possible mutation as separate wordlist entries.

## Requirements

```bash
sudo apt install hcxtools hashcat
```
`hashcat` on Debian/Raspberry Pi OS usually ships rule files under
`/usr/share/hashcat/rules/` - check `ls /usr/share/hashcat/rules/` after
installing. If none are present, you can also grab `best64.rule` from
[hashcat's GitHub repo](https://github.com/hashcat/hashcat/tree/master/rules)
directly.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp RuleMutationCrack.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/RuleMutationCrack.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, filling in your
   own SSIDs under `targets` and confirming `rules_file` points to a
   real file on your Pi.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep RuleMutationCrack
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `targets` | `[]` | Your own SSIDs to act on |
| `wordlist` | `/home/pi/wordlists/rockyou.txt` | Base wordlist for both passes |
| `rules_file` | `/usr/share/hashcat/rules/best64.rule` | Rule file applied on the second pass |
| `export_dir` | `/home/pi/rulemutationcrack/exports` | Where `.hc22000` files land |
| `log_file` | `/home/pi/rulemutationcrack/results.log` | Plain-text run log |
| `plain_pass_timeout_secs` | `300` | Timeout for the fast plain pass |
| `rule_pass_timeout_secs` | `1800` | Timeout for the slower rule-based pass |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "rules_file missing, skipping" | `rules_file` path doesn't exist on the Pi - check `ls /usr/share/hashcat/rules/` |
| Rule pass takes a very long time | Expected - rule-based mutation multiplies effective wordlist size significantly; Pi 4 CPU-only hashcat is slow for this. Consider a smaller/faster rule file or offloading to a GPU machine |
| Nothing cracks on either pass | Password isn't in the wordlist even with mutations applied - a good sign for your own network's strength |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/RuleMutationCrack.py
```
Remove the `main.plugins.RuleMutationCrack.*` block from `config.toml`
and restart.

## Scope note

Only ever acts on SSIDs explicitly listed in `targets` - identical
scoping principle to ClaudeCrackAuto and HandshakeCompleter.

---
*Author: patrickato · Added via Claude · version 1.0.0*
