# ClaudeCrackAuto

A pwnagotchi plugin for testing the password strength of **your own** Wi-Fi
networks. Built for a home-lab / student pen-testing setup.

## What it does

1. Watches for new handshakes pwnagotchi captures (`on_handshake`).
2. Checks the SSID against a **whitelist you configure** - if the SSID
   isn't on the list, the plugin does nothing to it at all. This keeps
   the automation scoped to networks you actually own, even though the
   pwnagotchi radio itself passively hears anything nearby.
3. For a whitelisted SSID, runs `hcxpcapngtool` to confirm the capture
   actually has a full/crackable handshake or PMKID, and converts it to
   the modern `.hc22000` format.
4. Depending on `run_local`:
   - `true` - runs `hashcat -m 22000` directly on the Pi against a
     wordlist you provide.
   - `false` - just leaves the converted `.hc22000` file in the export
     folder for you to grab and crack on a PC/GPU.
5. Logs every step to a results file, and can optionally push a
   notification (ntfy or Discord) when a result comes in.

## Requirements on the Pi

```
sudo apt update
sudo apt install hcxtools          # provides hcxpcapngtool - required
sudo apt install hashcat           # only needed if run_local = true
pip3 install requests --break-system-packages   # only needed for notifications
```

## Install

1. Copy `ClaudeCrackAuto.py` to pwnagotchi's custom plugins directory
   on the Pi. On the jayofelony image that's usually:

   ```
   /usr/local/share/pwnagotchi/custom-plugins/
   ```

   (create it if it doesn't exist)

   From your Windows PC:
   ```powershell
   scp ClaudeCrackAuto.py pi@pwnagotchi.local:/tmp/
   ```
   then on the Pi (SSH in):
   ```
   sudo mv /tmp/ClaudeCrackAuto.py /usr/local/share/pwnagotchi/custom-plugins/
   ```

2. Add the config block from `config-example.toml` to
   `/etc/pwnagotchi/config.toml` (edit it to match your setup - see
   comments in that file for what each setting does).

3. Restart pwnagotchi:
   ```
   sudo systemctl restart pwnagotchi
   ```

4. Watch the log:
   ```
   tail -f /home/pi/claudecrackauto/results.log
   ```
   or the main pwnagotchi log for `[ClaudeCrackAuto]` lines:
   ```
   sudo journalctl -u pwnagotchi -f | grep ClaudeCrackAuto
   ```

## Config quick reference

See `config-example.toml` for the full block with comments. The
essentials:

| Key | Meaning |
|---|---|
| `whitelist` | List of SSIDs (yours only) this plugin is allowed to act on |
| `run_local` | `true` = crack on the Pi, `false` = export only |
| `wordlist` | Path to your wordlist (rockyou.txt or your own) |
| `export_dir` | Where `.hc22000` files land |
| `log_file` | Plain-text run log |
| `notify_enabled` / `notify_method` / `ntfy_url` / `discord_webhook` | Optional push alerts |

## Scope note

This plugin is intentionally gated by SSID whitelist and does not touch
anything outside that list. It's meant for a home lab where you're
testing your own equipment's real-world password resilience - not for
running against networks you don't own or have explicit permission to
test.
