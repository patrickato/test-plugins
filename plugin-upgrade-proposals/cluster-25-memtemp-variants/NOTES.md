# Notes: memtemp variants cluster

**Status: both KEPT (`memtemp_adv.py`, `memtemp_ng.py`), alongside the
already-listed `memtemp-plus.py`. Findings-only.**

Sources: both from `itsdarklikehell/pwnagotchi-plugins`.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced.

## 1. What each one is and does

1. **`memtemp_adv.py`** - displays CPU load, memory usage, disk usage,
   and CPU temperature (optionally frequency), using `psutil` for its
   system readings.
2. **`memtemp_ng.py`** - displays memory usage, CPU load, CPU
   temperature (optionally frequency, optionally a non-blocking
   "since-last-check" CPU load variant), using the framework's own
   built-in `pwnagotchi.mem_usage()`/`pwnagotchi.cpu_load()` helpers
   instead of `psutil`.

Both are configurable multi-field displays (pick which stats show, in
what order, horizontal or vertical) descended from the same lineage as
the already-listed `memtemp-plus.py` (credited in `memtemp_ng.py`'s own
changelog comments to spees/crahan/xenDE). `memtemp_adv.py` adds disk
usage and psutil-based readings on top of that lineage; `memtemp_ng.py`
adds the non-blocking CPU-load variant.

## 2. `memtemp_adv.py` - one real bug, one missing-defaults gap

**Bug - `NameError` on a specific screen/orientation combination:**
```python
elif ui.is_waveshare_v3():
    h_pos = (178, 85)
    y_pos = (197, 75)      # BUG: should be v_pos, not y_pos
```
This is inside the fallback position logic that only runs when no
explicit `position` option is set. If the screen is detected as
`waveshare_v3` *and* `orientation == "vertical"` *and* no explicit
`position` is configured, `v_pos` is never assigned in this branch (only
the misspelled `y_pos` is). The code later does:
```python
v_pos_x = v_pos[0]   # NameError: name 'v_pos' is not defined
```
A one-character typo (`y` instead of `v`) with a real crash consequence
for that specific combination.

**Fix:**
```python
elif ui.is_waveshare_v3():
    h_pos = (178, 85)
    v_pos = (197, 75)
```

**Gap:** `cpu_temp()` reads `self.options["scale"]` directly:
```python
def cpu_temp(self):
    if self.options["scale"] == "fahrenheit":
        ...
```
but this file's own `__defaults__` block only declares
`{"enabled": False, "orientation": "horizontal"}` - `"scale"` isn't
declared even in the file's own stated intent, separate from the
broader project-wide fact that `__defaults__` is never read on this
fork at all (Group 31's correction) - this is a gap even by the file's
own internal logic, since `memtemp_ng.py`'s equivalent block does
include it (see below).

**Fix:** add `"scale": "celsius"` to `__defaults__` for internal
consistency, and/or set it explicitly in `config.toml` (the fix that
actually matters on this fork either way).

## 3. `memtemp_ng.py` - no crash bugs, one real design trade-off

Its `__defaults__` declares `"scale": "celsius"` alongside
`"orientation"` - more complete than `memtemp_adv.py`'s own defaults
block, though still irrelevant to whether it actually works on this
fork (same project-wide correction applies). No `waveshare_v3` branch -
uses `is_waveshare2in7()` instead, a different, non-overlapping screen
check; not a bug, just different hardware coverage than `memtemp_adv.py`.

**Design trade-off, not a bug:** the default "cpu" field calls:
```python
def cpu_load(self):
    return f"{int(pwnagotchi.cpu_load() * 100)}%"
```
Confirmed by reading the framework source (`pwnagotchi/__init__.py`)
that `cpu_load()` called with no `tag` argument does:
```python
def cpu_load(tag=None):
    if tag and tag in _cpu_stats.keys():
        parts0 = _cpu_stats[tag]
    else:
        parts0 = _cpu_stat()
        time.sleep(0.1)     # only need to sleep when no tag
    ...
```
- an internal `time.sleep(0.1)` as part of its instantaneous-sampling
approach when called without a tag. Since `memtemp_ng.py`'s "cpu" field
is in `DEFAULT_FIELDS` and calls this untagged, every UI refresh that
includes it blocks the UI-update thread for roughly 0.1 seconds.

The plugin does offer an alternative, non-blocking field ("cpus", via
its own `cpu_load_since()` method, tracking `/proc/stat` deltas itself
between calls without the framework's blocking helper) - but it's not
the default. `memtemp_adv.py`'s `psutil.cpu_percent()` call, by
contrast, is non-blocking by nature (returns the delta since psutil's
own last internal call) - no equivalent cost there.

**Fix, if UI responsiveness matters:** swap the default "cpu" field for
"cpus" in `DEFAULT_FIELDS`, or document the trade-off so a user
configuring `fields` explicitly knows "cpu" costs a brief per-refresh
delay while "cpus" doesn't. Not applied - kept as-is per broad-scope
philosophy, this is a minor performance note rather than a defect.

## 4. Dependencies (both kept plugins)

`memtemp_adv.py`: `psutil` (pip, `sudo pip3 install psutil==5.4.7` per
its own header comment - a pinned older version, worth checking
compatibility with this fork's Python version if ever installed), plus
`scapy` (pip, declared but unused - same boilerplate pattern seen
elsewhere in this project). `memtemp_ng.py`: `scapy` (pip, same unused
boilerplate) - no other dependencies, uses only the framework's own
built-in system-stat helpers.
