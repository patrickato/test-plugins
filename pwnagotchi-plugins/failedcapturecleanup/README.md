# FailedCaptureCleanup

Detects when an attack attempt produced an empty or junk `.pcap`
(a silent failure - something fired but nothing usable landed on
disk) and cleans it up, instead of letting dead files pile up per AP
in the handshakes directory.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `FailedCaptureCleanup.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. A background thread sweeps the handshakes directory every
   `sweep_interval_secs`, rather than only reacting to `on_handshake`
   - a truly silent failure (nothing captured at all) never fires
   that hook, so the junk file just sits there unless something
   actively looks for it.
2. Any `.pcap` smaller than `min_valid_bytes` is treated as a silent
   failure and handled immediately.
3. If `deep_check` is enabled, files that pass the size check are
   also run through `hcxpcapngtool` (the same conversion tool used
   elsewhere in this repo) - if nothing convertible comes out, it's
   junk too. This is slower (a subprocess per file) but catches
   pcaps that recorded some traffic but never a useful frame.
4. Files younger than `min_file_age_secs` are skipped on every sweep,
   so a capture still being written mid-attack is never mistaken for
   a dead file.
5. By default, junk files are **quarantined** - moved into
   `quarantine_dir`, never deleted - so you can review what's getting
   flagged before trusting it. Set `hard_delete = true` once you're
   confident, and junk files are removed permanently instead.
6. The on-screen `JUNK` counter shows a running total of
   quarantined + deleted files for the session.

## Why quarantine by default

Consistent with how `HandshakeMerge` in this repo never overwrites
files, this plugin defaults to the reversible option. A false
positive in `min_valid_bytes` or a flaky `hcxpcapngtool` run
shouldn't be able to silently destroy a real capture - quarantining
first gives you a chance to notice and fix the config before turning
on permanent deletion.

## Requirements

- No extra packages required for the basic (size-only) check.
- `hcxpcapngtool` (part of `hcxtools`) only if `deep_check = true`:
  ```bash
  sudo apt install hcxtools
  ```
  If it's missing, `deep_check` fails open (leaves the file alone)
  rather than quarantining files it couldn't actually verify.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp FailedCaptureCleanup.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/FailedCaptureCleanup.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep FailedCaptureCleanup
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `handshakes_dir` | `/home/pi/handshakes` | Where captures are written |
| `quarantine_dir` | `<handshakes_dir>/failedcapturecleanup_quarantine` | Where junk files go (when not hard-deleting) |
| `min_valid_bytes` | `200` | Files smaller than this are junk |
| `deep_check` | `false` | Also verify via `hcxpcapngtool`, not just size |
| `hcxpcapngtool_path` | `hcxpcapngtool` | Override if not on PATH |
| `hard_delete` | `false` | Permanently delete junk instead of quarantining |
| `sweep_interval_secs` | `120` | How often the directory is swept |
| `min_file_age_secs` | `30` | Ignore files younger than this (still being written) |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Good captures getting quarantined | `min_valid_bytes` set too high for your setup, or `deep_check` flagging real-but-small captures - raise `min_valid_bytes`/leave `deep_check` off and check `quarantine_dir` manually first |
| Nothing ever gets flagged | Check `sweep_interval_secs` isn't too long for a short test session, and confirm `handshakes_dir` matches your actual pwnagotchi config |
| `deep_check` seems to do nothing | `hcxpcapngtool` not installed - it fails open by design rather than quarantining files it can't verify |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/FailedCaptureCleanup.py
```
Remove the `main.plugins.FailedCaptureCleanup.*` block from
`config.toml` and restart. Anything already in `quarantine_dir` is
left in place either way.

## Scope note

Purely housekeeping on pwnagotchi's own local capture files -
doesn't change what pwnagotchi targets or attacks, and (by default)
never permanently deletes anything without you opting in.

---
*Author: patrickato · Added via Claude · version 1.0.0*
