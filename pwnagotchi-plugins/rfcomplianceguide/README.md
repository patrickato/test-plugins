# RFComplianceGuide

Checks that the Pi's actual WiFi regulatory domain matches the country
you tell it you're really operating in, and helps correct it toward
your real location if it doesn't — not to unlock more channels, but to
make sure the unit is actually staying within the rules of wherever it
really is.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `RFComplianceGuide.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## What this is NOT

There's already a community plugin (`fix_region`) that lets you set the
Pi's regulatory domain to whatever country you want, purely to unlock
more channels or higher power than your actual country allows. That's
a legal gray area the moment the country you set isn't the one you're
actually transmitting in — spectrum rules are tied to physical
location, not what your OS believes.

**This plugin does the opposite job**: it assumes you want to stay
correctly inside your own country's real limits, checks whether the Pi
currently agrees, and only ever offers to correct *toward* your real,
declared location — never toward a looser one you pick for more range.

## How it works

1. On load, runs `iw reg get` to read the Pi's current regulatory
   domain.
2. Compares it to `real_country_code`, which you set to wherever this
   Pi is actually physically operating.
3. If they match: logs "OK" and does nothing further.
4. If they don't match: logs a clear warning. That's all it does by
   default (`auto_correct = false`) — it won't touch anything without
   you opting in.
5. If `auto_correct = true`: runs `iw reg set <real_country_code>` to
   correct the live regulatory domain, and logs whether that succeeded.
6. If `auto_correct` succeeded **and** `write_channels_to_config =
   true`: writes the legal 2.4GHz channel list for your real country
   into `config.toml`'s `personality.channels`, so pwnagotchi's own
   channel-hopping behavior stays inside those channels going forward.

## Coverage

The plugin ships a small built-in table of common regulators' legal
2.4GHz channel ranges (US/FCC, Canada/ISED, UK/Ofcom, Germany/France/
generic-EU under ETSI, Japan/ARIB, Australia/ACMA) — this is the same
kind of publicly published spectrum-allocation information that ships
in any WiFi chipset datasheet or OS driver, nothing sensitive. 5GHz is
intentionally left out since it's heavily DFS-restricted and far more
complex to table correctly; if you need that too, say so and I'll add
it properly rather than guess.

If your country isn't in the table, the mismatch check and warning
still work — you'd just need to add your own entry to
`REGION_CHANNELS_24GHZ` in the plugin for the channel-writing step.

## Requirements

```bash
# 'iw' is part of the standard wireless-tools chain and is normally
# already installed on pwnagotchi images. If it's missing:
sudo apt install iw

pip3 install toml --break-system-packages   # only needed if write_channels_to_config = true
```

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp RFComplianceGuide.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/RFComplianceGuide.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, and set
   `real_country_code` to wherever you actually are.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Check the result immediately:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep RFComplianceGuide
   ```
   or:
   ```bash
   cat /home/pi/rfcomplianceguide/results.log
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `real_country_code` | *(required)* | Two-letter code for where the Pi actually is |
| `auto_correct` | `false` | Actually run `iw reg set` to fix a mismatch |
| `write_channels_to_config` | `false` | Also persist the legal channel list to `personality.channels` |
| `log_file` | `/home/pi/rfcomplianceguide/results.log` | Plain-text log |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `no iw` status / "Could not read current regulatory domain" | `iw` isn't installed — `sudo apt install iw` |
| Mismatch logged but nothing changes | Expected — `auto_correct` defaults to `false` on purpose |
| `auto_correct` succeeds but channels aren't written | `write_channels_to_config` is still `false`, or your `real_country_code` isn't in `REGION_CHANNELS_24GHZ` |
| `toml` import error | `pip3 install toml --break-system-packages` |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/RFComplianceGuide.py
```
Remove the `main.plugins.RFComplianceGuide.*` block from `config.toml`
and restart. Any regulatory domain change or `personality.channels`
edit it already made stays in place — revert those by hand if wanted.

## Scope note

This plugin only ever nudges the Pi's settings toward the country you
declare as your real, actual physical location. It does not offer a
way to select a different country for more channels or power, and the
built-in reference table only reflects standard public regulatory
allowances, not a way around them.

---
*Author: patrickato · Added via Claude · version 1.0.0*
