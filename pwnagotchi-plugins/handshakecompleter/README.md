# HandshakeCompleter

An "assembly line" plugin for pwnagotchi: point it at a list of your own
APs, and it works through them one at a time, moving each to
pwnagotchi's built-in whitelist (so pwnagotchi stops attacking it) the
moment it gets a full 4-way handshake - freeing pwnagotchi's attention
for whatever's still on the list.

This folder is self-contained, separate from ClaudeCrackAuto and
everything else in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `HandshakeCompleter.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it works

1. You list your own SSIDs under `targets` in the config - these are
   APs you've deliberately left **off** pwnagotchi's normal
   `main.whitelist`, so pwnagotchi is already attacking them as part of
   your testing.
2. Every time pwnagotchi writes a handshake file for one of those
   targets, this plugin runs it through `hcxpcapngtool` and classifies
   it: **full 4-way handshake**, **PMKID only**, or **incomplete**.
3. If it's incomplete, the plugin does nothing further - pwnagotchi's
   own normal loop already keeps retrying non-whitelisted APs on its
   own each epoch, so the target just stays "in progress."
4. Once a target is classified complete (full 4-way, or PMKID too if
   you set `accept_pmkid_as_complete = true`), the plugin:
   - Adds that SSID to pwnagotchi's **real** `main.whitelist` - the
     same built-in setting pwnagotchi already uses to protect networks
     it shouldn't attack. This is what actually stops pwnagotchi from
     continuing to deauth/associate with it.
   - Tries to update the *live*, already-running agent's config so the
     change takes effect immediately.
   - Always writes the change to `/etc/pwnagotchi/config.toml` too, so
     it's permanent even if the live update doesn't apply cleanly on
     your version (see **Version note** below).
   - Logs the event and updates the on-screen `HSC N/M` counter.
5. Nothing outside your `targets` list is touched by this plugin at
   all - not classified, not logged, not whitelisted. Pwnagotchi's
   normal behavior toward everything else is unaffected.

## Requirements

```bash
sudo apt update
sudo apt install hcxtools                          # provides hcxpcapngtool - required
pip3 install toml --break-system-packages           # required to persist whitelist changes
pip3 install requests --break-system-packages       # only if using notifications
```

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp HandshakeCompleter.py pi@pwnagotchi.local:/tmp/
   ```
   Then on the Pi:
   ```bash
   sudo mv /tmp/HandshakeCompleter.py /usr/local/share/pwnagotchi/custom-plugins/
   ```

2. Add the config block from `config-example.toml` to
   `/etc/pwnagotchi/config.toml`, and fill in your own SSIDs under
   `targets`. **Double check none of them are already in your
   `main.whitelist`** - if they are, pwnagotchi's never attacking them
   to begin with, so this plugin has nothing to do for them.

3. Restart pwnagotchi:
   ```bash
   sudo systemctl restart pwnagotchi
   ```

4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep HandshakeCompleter
   ```
   You should see something like:
   ```
   [HandshakeCompleter] plugin loaded, targets=['yourhomenetwork', ...], 0/3 already complete
   ```

5. Watch progress:
   ```bash
   tail -f /home/pi/handshakecompleter/results.log
   ```
   The display also shows a running `HSC 1/3` style counter.

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `targets` | `[]` | Your own SSIDs to work through, in order pwnagotchi happens to encounter them. Must not already be whitelisted elsewhere. |
| `accept_pmkid_as_complete` | `false` | If `true`, a PMKID capture alone counts as "done" for a target |
| `state_file` | `/home/pi/handshakecompleter/state.json` | Tracks per-target progress across restarts |
| `log_file` | `/home/pi/handshakecompleter/results.log` | Plain-text run log |
| `notify_enabled` / `notify_method` / `ntfy_url` / `discord_webhook` | — | Optional push alerts on completion |

## Version note on live whitelist updates

Pwnagotchi's internal agent config structure has changed a bit across
releases, so this plugin tries a best-effort in-memory update to make a
completed target stop being attacked *immediately*. If your version's
internals don't match what the plugin tries, that live update silently
does nothing - but the `config.toml` write always happens regardless,
so the change is guaranteed to take effect on the next restart even in
the worst case. Check the log line after a completion event; it tells
you whether the live update succeeded (`live update: True/False`).

If you want completions to take effect without any restart at all on
your specific jayofelony build, that may need a small tweak to the
`_whitelist_live` method to match your version's actual agent config
attribute - happy to adjust it once you see what the log reports.

## Checking overall progress

```bash
cat /home/pi/handshakecompleter/state.json
```
Shows every target's current status (`in_progress` / `complete`), last
classification, and completion timestamp.

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/HandshakeCompleter.py
```
Then remove the `main.plugins.HandshakeCompleter.*` block from
`config.toml` and restart. Note that any SSIDs this plugin already
added to `main.whitelist` stay there - remove them by hand from
`main.whitelist` if you want pwnagotchi to resume attacking those APs.

## Scope note

This plugin only ever adds entries to your whitelist, and only for
SSIDs you explicitly listed in `targets`. It never expands its own
reach beyond that list, and it never removes anything from your
existing whitelist. It's built for working through your own home
network's APs one at a time - not for managing targeting against
anything you don't own.

---
*Author: patrickato · Added via Claude · version 1.0.0*
