# ClaudeCrackAuto

A pwnagotchi plugin for testing the password strength of **your own** Wi-Fi
networks in a home lab. It is deliberately scoped by an SSID whitelist so
it never touches, converts, or cracks a handshake for anything you haven't
explicitly listed as yours.

This folder is self-contained — everything for this one plugin lives here,
separate from the other tools in this repo (e.g. PwnDoctor).

## Files in this folder

| File | Purpose |
|---|---|
| `ClaudeCrackAuto.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. Not a standalone file the plugin reads. |
| `README.md` | This file. |

## What it does

1. Watches for new handshakes pwnagotchi captures (`on_handshake`).
2. Checks the SSID against a **whitelist you configure**. If the SSID
   isn't on the list, the plugin does nothing to it at all — no
   conversion, no cracking, no touching the file. This keeps the
   automation scoped to networks you actually own, even though the
   pwnagotchi radio passively hears anything nearby.
3. For a whitelisted SSID, runs `hcxpcapngtool` to confirm the capture
   actually contains a full/crackable handshake or PMKID, and converts it
   to the modern `.hc22000` format.
4. Depending on `run_local`:
   - `true` — runs `hashcat -m 22000` directly on the Pi 4 against a
     wordlist you provide (CPU-only, slow, fine for testing weak/dictionary
     passwords).
   - `false` — leaves the converted `.hc22000` file in the export folder
     for you to grab and crack elsewhere (e.g. a PC with a GPU).
   - Both modes always produce and keep the `.hc22000` export, so even
     with `run_local = true` you still have the file if you want to
     re-run it somewhere faster later.
5. Logs every step (skip, validate, convert, crack attempt, result) to a
   plain-text log file, and can optionally push a notification (ntfy or
   Discord webhook) when a result comes in.
6. Shows a short status field (`CCA`) on the pwnagotchi display —
   `idle`, `validating`, `cracking`, `cracked!`, `not found`, etc.

## Requirements

**On the Pi (required):**
```bash
sudo apt update
sudo apt install hcxtools     # provides hcxpcapngtool — required, no fallback
```

**On the Pi (only if `run_local = true`):**
```bash
sudo apt install hashcat
```
Raspberry Pi 4 hashcat is CPU-only (no GPU backend), so it's realistically
useful for short/weak/dictionary-word passwords, not brute-forcing strong
ones. That's normal and fine for testing your own network's baseline
strength — if it doesn't crack quickly here, that's a good sign, not a
plugin failure.

**On the Pi (only if notifications are enabled):**
```bash
pip3 install requests --break-system-packages
```

**A wordlist (only if `run_local = true`):**
The stock jayofelony pwnagotchi image does **not** ship rockyou.txt or any
other wordlist — you have to supply one. Options:
- Download a copy of `rockyou.txt` (widely available, ~14M entries, a
  good general baseline) and `scp` it to the Pi.
- Build a small custom list targeted at your own household's actual
  password habits/patterns with a tool like `crunch` — often more
  realistic for a home-network test than a huge generic list.
- Point `wordlist` in the config at wherever you put it; no default path
  is assumed on your system.

If `run_local = true` but `hashcat` or the wordlist is missing, the
plugin logs a clear warning and falls back to export-only for that
handshake — it won't silently fail or hang.

## Install

1. **Copy the plugin to the Pi.** From your Windows PC (PowerShell):
   ```powershell
   scp ClaudeCrackAuto.py pi@pwnagotchi.local:/tmp/
   ```
   Then SSH into the Pi and move it into pwnagotchi's custom plugins
   directory (create it if it doesn't exist):
   ```bash
   sudo mkdir -p /usr/local/share/pwnagotchi/custom-plugins/
   sudo mv /tmp/ClaudeCrackAuto.py /usr/local/share/pwnagotchi/custom-plugins/
   ```

2. **Install dependencies** (see Requirements above).

3. **Add the config block.** Copy the contents of `config-example.toml`
   into `/etc/pwnagotchi/config.toml` (append it — don't replace the
   whole file) and edit the values for your setup, especially:
   - `whitelist` — your own SSID(s), and nothing else
   - `run_local` — `true` or `false`
   - `wordlist` — path to your wordlist, if using `run_local = true`

4. **Restart pwnagotchi:**
   ```bash
   sudo systemctl restart pwnagotchi
   ```

5. **Verify it loaded**, before waiting on a real handshake:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep ClaudeCrackAuto
   ```
   You should see a line like:
   ```
   [ClaudeCrackAuto] plugin loaded, whitelist=['yourhomenetwork'], run_local=True
   ```
   If instead you see the `hcxpcapngtool not found` error, dependencies
   weren't installed correctly — go back to step 2.

6. **Watch it work** once a whitelisted handshake comes in:
   ```bash
   tail -f /home/pi/claudecrackauto/results.log
   ```
   or filter the main pwnagotchi log:
   ```bash
   sudo journalctl -u pwnagotchi -f | grep ClaudeCrackAuto
   ```

## Config quick reference

Full block with inline comments is in `config-example.toml`. Summary:

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate the plugin |
| `whitelist` | `[]` | SSIDs (yours only) this plugin is allowed to act on. Case-insensitive. Empty = plugin loads but does nothing. |
| `run_local` | `false` | `true` = crack on the Pi with hashcat, `false` = export `.hc22000` only |
| `wordlist` | `/home/pi/wordlists/rockyou.txt` | Path to your wordlist (only used when `run_local = true`) |
| `export_dir` | `/home/pi/claudecrackauto/exports` | Where converted `.hc22000` files are written (always, in both modes) |
| `log_file` | `/home/pi/claudecrackauto/results.log` | Plain-text run log |
| `hashcat_timeout_secs` | `900` | Max seconds to let a local hashcat run go before giving up |
| `notify_enabled` | `false` | Turn on push notifications |
| `notify_method` | `"ntfy"` | `"ntfy"` or `"discord"` |
| `ntfy_url` | — | Your ntfy topic URL |
| `discord_webhook` | — | Your Discord webhook URL |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Nothing happens on a capture you expected to trigger it | SSID isn't an exact case-insensitive match to an entry in `whitelist` — check for typos, extra spaces, or a `-5G` suffix that's actually a separate SSID |
| `hcxpcapngtool not found` in the log | `hcxtools` not installed — `sudo apt install hcxtools` |
| Status stuck at `no wordlist` | `wordlist` path in config doesn't exist on the Pi, or `run_local` is on but you haven't put a wordlist there yet |
| Status stuck at `no hashcat` | `hashcat` not installed but `run_local = true` — either install it or set `run_local = false` |
| Notifications never arrive | `notify_enabled = true` but `ntfy_url`/`discord_webhook` empty, or `requests` isn't installed (`pip3 install requests --break-system-packages`) |
| Cracking takes a very long time / never finishes | Expected on Pi 4 CPU-only hashcat against a large wordlist — this is a hardware limit, not a bug. Consider `run_local = false` and cracking on a faster machine instead |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/ClaudeCrackAuto.py
```
Then remove the `main.plugins.ClaudeCrackAuto.*` block from
`/etc/pwnagotchi/config.toml` and restart pwnagotchi. Exported
`.hc22000` files and the log file under `/home/pi/claudecrackauto/` are
left in place — delete that folder manually if you want them gone too.

## Scope note

This plugin is intentionally gated by the SSID whitelist and does not
touch anything outside it. It's built for a home lab where you're
testing your own equipment's real-world password resilience — not for
running against networks you don't own or don't have explicit
permission to test.

---
*Author: patrickato · Added via Claude · version 1.0.0*
