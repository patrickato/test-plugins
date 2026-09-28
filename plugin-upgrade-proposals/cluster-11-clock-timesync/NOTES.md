# Notes: clock / time-sync plugin cluster

**Status: `clock_wav_v3.py` REMOVED. `clock.py`, `rtc_grid.py`,
`RaspiSyncedTime.py` KEPT.**

## `clock_wav_v3.py` - removed, redundant + broken on user's hardware

Same author (LoganMD) and same job as `clock.py` - both display a
date/time `LabeledValue` element on screen. The difference is
`clock_wav_v3.py` adds a `memtemp`-aware position offset, but gates
the whole UI-element creation behind `ui.is_waveshare_v3()`:

```python
if ui.is_waveshare_v3():
    pos = (130, 80) if memenable else (200, 80)
    ui.add_element('clock', LabeledValue(...))
```

User is on an MPI3501 TFT, not a Waveshare v3 panel, so on this
hardware `on_ui_setup()` creates nothing. `on_ui_update()` still runs
unconditionally every cycle:

```python
def on_ui_update(self, ui):
    now = datetime.datetime.now()
    time_rn = now.strftime(self.date_format + "\n%I:%M %p")
    ui.set('clock', time_rn)
```

`ui.set()` against an element that was never created is the same
failure pattern found in `wardrive.py` (Cluster 9) - not a load-time
crash, but a broken/erroring plugin on this exact display. Since
`clock.py` does the same core job with no screen-type gate at all (a
hardcoded fixed position that draws on any screen), there's no reason
to keep the broken, screen-locked version around - removed rather
than documented-and-kept, since this is a clean superseded-by-another-
kept-plugin case, not a "needs its own fix" case.

## `clock.py` - kept

Hardcoded fixed positions (`clock1` at (100,0), `clock2` at
(100,95)), no screen-type check, so it draws on any display including
the MPI3501 TFT. Simple `datetime.now()` formatting, no external
dependencies beyond the standard pwnagotchi UI imports. No bugs
found. The two fixed positions may not be ideal for the small
MPI3501 screen specifically and could be worth nudging if they ever
overlap another plugin's UI elements, but that's a config/position
tweak, not a code fix.

## `rtc_grid.py` - kept

Requires a physical I2C real-time-clock module at bus address `0x68`
(checked via `smbus.SMBus(1).read_byte(0x68)` in `on_ready`) - not
present on this build. Every hook wraps its body in try/except and
logs cleanly when the RTC isn't found or grid mesh peers aren't
available, so it's safe to leave enabled dormant. One real gap: needs
the `smbus` pip package, which isn't declared anywhere in
`__dependencies__` (only lists `scapy`, unused boilerplate like most
of this author's other plugins). If ever installed on a system without
`smbus` already present, the plugin would fail to import entirely
(top-level `import smbus`), not just fail gracefully at runtime - so
if this is ever actually wired up with a real RTC module,
`__dependencies__` should be updated to include `smbus` (apt package
`python3-smbus` or pip `smbus`).

## `RaspiSyncedTime.py` - kept, misfiled but harmless

Not a real pwnagotchi plugin - a standalone `RaspiSyncedTime` utility
class (offset-based clock correction for boards with no
battery-backed RTC, syncing off `/var/lib/systemd/timesync/clock`),
meant to be imported by other code. Ships with its own companion
`on-boot.sh` and `test.py` in its source repo, not designed to run as
a plugin on its own. Unlike `gsmfake.py` (Cluster 8) or
`Pwnagotchi-JSON-to-Wigle-CSV.py` (Cluster 9), it has **no risky
top-level code** - just class/method definitions - so if the plugin
loader ever imports this file looking for a `plugins.Plugin`
subclass, it will find none and move on silently. No crash risk, just
dead weight sitting in the plugin folder. Kept per broad-scope
philosophy since it costs nothing to leave in, unlike the two flagged
scripts in earlier clusters.

## Dependencies

`rtc_grid.py` needs `smbus` (undeclared gap, see above) plus a
physical I2C RTC module at address 0x68. `clock.py` and
`RaspiSyncedTime.py` need nothing beyond the standard library /
pwnagotchi's own UI modules.
