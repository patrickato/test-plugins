# PassiveOnlyMode

A hard switch for the quietest possible test run, with two levels:
`quiet` (PMKID collection stays on, deauth off) and `silent` (fully
passive - pwnagotchi sends nothing at all, just listens to beacon
frames). Also shows a `QUIET`/`SILENT` indicator on the display so it's
obvious at a glance the unit is in a reduced-activity mode.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `PassiveOnlyMode.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## How it actually works - read this part

`personality.deauth` and `personality.associate` are read by
pwnagotchi's core automata **once, at startup, before any plugin gets
a chance to run.** That means this plugin **cannot flip those settings
for you live** - it can only verify and loudly log what `config.toml`
needs to say. **The `personality.*` lines in `config-example.toml` are
what actually enforce the mode** - the plugin's own job is just
confirmation and the on-screen indicator.

- **`mode = "quiet"`**: requires `personality.associate = true`,
  `personality.deauth = false`. PMKID association attempts still
  happen (lightweight, no client needed), but no deauth traffic at
  all.
- **`mode = "silent"`**: requires `personality.associate = false`,
  `personality.deauth = false`. Fully passive - pwnagotchi transmits
  nothing, it only listens to beacon frames already being broadcast.

## Requirements

None.

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp PassiveOnlyMode.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/PassiveOnlyMode.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml` - **set BOTH the
   `personality.*` lines AND `main.plugins.PassiveOnlyMode.mode` to
   match each other.**
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm the mode and requirement are logged:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep PassiveOnlyMode
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `mode` | `"quiet"` | `"quiet"` (PMKID on, deauth off) or `"silent"` (fully passive) |

Also required, outside the plugin's own block - see table in "How it
actually works" above for which values each mode needs.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| pwnagotchi still deauthing in `quiet`/`silent` mode | `personality.deauth` wasn't actually set to `false` in `config.toml` - this plugin can only detect and log the mismatch, not fix it live |
| PMKID attempts happening in `silent` mode | `personality.associate` wasn't set to `false` |
| Display shows nothing | UI element position may conflict with another plugin's - adjust the `position` value in the plugin file if needed |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/PassiveOnlyMode.py
```
Remove the `main.plugins.PassiveOnlyMode.*` block from `config.toml`,
and revert the `personality.*` lines to your normal settings.

## Scope note

This plugin doesn't target or affect any specific network - it's a
global activity-level switch for pwnagotchi itself, verified and
displayed rather than actively enforced (since personality settings
are read before plugins can run).

---
*Author: patrickato · Added via Claude · version 1.0.0*
