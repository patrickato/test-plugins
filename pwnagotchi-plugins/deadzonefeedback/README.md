# DeadZoneFeedback

Real-time GPIO buzzer/LED feedback on signal strength toward one
specific target AP - the weaker the signal, the slower the beep/blink;
the stronger, the faster. Immediate "warmer/colder" feedback while
physically walking around with the unit, instead of reviewing a log
afterward.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `DeadZoneFeedback.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## Hardware needed

A passive buzzer and/or an LED, each wired to a GPIO pin + ground -
basic GPIO output wiring, same as any beginner Pi project. Not
included or assumed; wire it up yourself before using this plugin. If
you only have one of the two, leave the other pin commented out in the
config and this plugin will just skip it.

## How it works

1. Tracks one specific `target_ssid` (your own AP) via `on_wifi_update`.
2. When it's visible, reads its current RSSI and maps it onto a pulse
   interval between `min_pulse_secs` (strongest, at `strong_rssi_dbm`)
   and `max_pulse_secs` (weakest, at `weak_rssi_dbm`).
3. Drives the buzzer/LED in a continuous short-pulse pattern at that
   interval - faster pulsing means you're picking up a stronger
   signal, slower means weaker.
4. If the target AP isn't currently visible at all, both outputs stay
   off.

## Requirements

```bash
pip3 install gpiozero --break-system-packages
```
(`gpiozero` is often already present on Raspberry Pi OS images - check
`python3 -c "import gpiozero"` before installing.)

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp DeadZoneFeedback.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/DeadZoneFeedback.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, set `target_ssid`,
   and confirm your GPIO pin numbers match your wiring (BCM numbering).
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep DeadZoneFeedback
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `target_ssid` | — | The one AP to give feedback for |
| `buzzer_pin` / `led_pin` | — | BCM GPIO pin numbers; leave either unset if not wired |
| `weak_rssi_dbm` / `strong_rssi_dbm` | `-85` / `-40` | RSSI range mapped to slow↔fast pulsing |
| `min_pulse_secs` / `max_pulse_secs` | `0.15` / `1.5` | Pulse interval bounds |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "could not initialize GPIO device(s)" in log | `gpiozero` not installed, wrong pin number, or pin already claimed by another plugin/process |
| Never pulses | `target_ssid` not visible from your current location, or spelling doesn't match exactly |
| Pulsing feels backwards (fast when far, slow when close) | Your hardware's actual RSSI range may differ from the defaults - adjust `weak_rssi_dbm`/`strong_rssi_dbm` to match what you observe in the log at known distances |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/DeadZoneFeedback.py
```
Remove the `main.plugins.DeadZoneFeedback.*` block from `config.toml`
and restart.

## Scope note

Purely a feedback/UI plugin - reads signal strength for one AP you
specify and drives output hardware. Takes no action on any network.

---
*Author: patrickato · Added via Claude · version 1.0.0*
