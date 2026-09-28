# Notes: LED/wardriving "_ng" rewrites cluster

**Status: `led.py`, `led-ng.py`, `morse_code.py`, `morse_code-ng.py`
REMOVED (4). `wardriver-pwnagotchi-plugin`, `wardriver_ng.py`, `f0xtr0t`,
`webgpsmap_ng.py` KEPT (4, findings-only, documented for later fixing).**

Sources: `led.py`, `led-ng.py`, `morse_code.py`, `morse_code-ng.py`,
`wardriver.py` (itsdarklikehell's mirror of `wardriver-pwnagotchi-plugin`),
`wardriver_ng.py`, `webgpsmap_ng.py` all from
`itsdarklikehell/pwnagotchi-plugins`; `f0xtr0t.py` also from
`itsdarklikehell/pwnagotchi-plugins`; the bundled `webgpsmap.py` compared
against is this fork's own default, from
`jayofelony/pwnagotchi/pwnagotchi/plugins/default/`.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced.

## 1. What each pair is and does

1. **`led.py`** / **`led-ng.py`** - blinks a status LED in different
   patterns depending on pwnagotchi events.
2. **`morse_code.py`** / **`morse_code-ng.py`** - flashes the status LED
   in Morse code.
3. **`wardriver-pwnagotchi-plugin`** / **`wardriver_ng.py`** - logs all
   seen networks to CSV session files and uploads them to WiGLE once
   internet is available.
4. **`f0xtr0t`** / **`webgpsmap_ng.py`** - builds a browsable
   OpenStreetMap page of AP/handshake positions from GPS-tagged capture
   data.

## 2. `led.py` / `led-ng.py` - removed, real regression bug in the rewrite

`led-ng.py`'s `__init__` correctly updates the default LED path to the
modern Raspberry Pi name (`/sys/class/leds/PWR/brightness`, vs. the
original's older `led0`), but `on_loaded` immediately overwrites that
good default:

```python
# led.py (works, if "led" option is a numeric index)
self._led_file = "/sys/class/leds/led%d/brightness" % self.options["led"]

# led-ng.py (regression - drops the "led" prefix)
self._led_file = "/sys/class/leds/%d/brightness" % self.options["led"]
```

`led-ng.py`'s version would produce a path like `/sys/class/leds/0/brightness`
- not a real sysfs device name on any Raspberry Pi (real ones are named
`led0`, `PWR`, `ACT`, never a bare digit), so writes to it would fail
with `FileNotFoundError` once the plugin loads. Both files also share
the pre-existing gap of requiring `self.options["led"]`/
`self.options["delay"]` to be set explicitly in `config.toml` (no
working fallback either way, on this fork).

**Fix, documented for reference even though removed:** restore the
`"led"` prefix in `led-ng.py`'s format string:
```python
self._led_file = "/sys/class/leds/led%d/brightness" % self.options["led"]
```

**Removed rather than fixed** per the user's decision this round.

## 3. `morse_code.py` / `morse_code-ng.py` - removed, cosmetic-only rewrite

Diffed directly - every difference between the two is logging-format
cleanup (f-strings, class-name-based log tags via
`f"[{self.__class__.__name__}]"` instead of hardcoded `"[Morse]"`) and a
renamed class (`MorseCode` -> `MorseCodeNG`). No behavioral change
either direction, no bugs found in either file, no new bugs introduced
by the rewrite.

**Removed rather than kept** per the user's decision this round - not
because of any defect, both were clean.

## 4. `wardriver-pwnagotchi-plugin` / `wardriver_ng.py` - kept, the rewrite is a real regression

Diffed itsdarklikehell's own `wardriver.py` mirror (of the already-listed
`wardriver-pwnagotchi-plugin`, by CyberArtemio) against `wardriver_ng.py`.
Three losses and one new bug in the "_ng" version:

**Loss 1 - drops the on-screen UI entirely.** The original adds a
`LabeledValue` UI element showing the live network count
(`on_ui_setup`/`on_ui_update`/`on_unload`); `wardriver_ng.py` has none of
these hooks at all - yet its `__defaults__` block still declares
`ui.enabled`, `ui.position.x`, `ui.position.y`, none of which are ever
read anywhere in the file. Dead configuration left over from an
incomplete strip-down.

**Loss 2 - drops session-merging.** The original can consolidate all
past wardriving sessions into one deduplicated database CSV
(`DATABASE_NAME = 'wardriver_db.csv'`, gated by a `merge_sessions`
option) so repeated sightings of the same network across sessions aren't
duplicated. `wardriver_ng.py`'s `_clean_csv_directory` is a stripped-down
version that only deletes short/empty session files - no merging, no
database file, no deduplication.

**Loss 3 / new bug - directory cleanup lost its file-type filter.** The
original's cleanup filters strictly:
```python
sessions = [ os.path.join(self.__csv_path, file) for file in os.listdir(self.__csv_path)
             if os.path.isfile(os.path.join(self.__csv_path, file)) and file.endswith(".csv")
             and file != self.DATABASE_NAME ]
```
`wardriver_ng.py` drops all of that:
```python
sessions = [os.path.join(self.__csv_path, file)
            for file in os.listdir(self.__csv_path)]
```
This lists and then tries to open *every* entry in the CSV directory as
a text session file - a subdirectory would raise `IsADirectoryError`,
and any non-CSV file present would be read and its line count
misinterpreted as a session file's.

**Fix, if ever prioritized:**
```python
# restore the filter in wardriver_ng.py's cleanup:
sessions = [os.path.join(self.__csv_path, file)
            for file in os.listdir(self.__csv_path)
            if os.path.isfile(os.path.join(self.__csv_path, file))
            and file.endswith(".csv")]
```
Re-adding the UI hooks and session-merging logic would mean porting them
back from the original `wardriver.py` - more work, not applied, noted
for whenever this plugin is prioritized. Not applied this round - kept
per broad-scope philosophy since none of these are crash bugs, just
feature loss plus one directory-listing edge case.

## 5. `f0xtr0t` / `webgpsmap_ng.py` - kept, broken as shipped, redundant with a working bundled default

**Major context, not a bug in either kept file:** this jayofelony fork
already bundles its own `webgpsmap.py` as a default plugin (confirmed in
`jayofelony/pwnagotchi/pwnagotchi/plugins/default/`) - which is *why*
plain `webgpsmap.py` is correctly excluded from this master list under
the project's standing "minus jayofelony-bundled defaults" rule, with
only `f0xtr0t` (a genuinely enhanced fork, by sixt0o) listed separately.
The bundled default has already been updated to search `*.pcapng`
throughout its own source.

**Bug - `webgpsmap_ng.py` uses `.pcap` everywhere instead of `.pcapng`.**
Confirmed by direct comparison against the bundled default:

```python
# jayofelony's bundled webgpsmap.py (already correct on this fork)
- search for *.pcapng files in your /handshakes/ dir
...
filename_pcap.removesuffix('.pcapng')
...
check_for = os.path.basename(pos_file).split(".")[0] + ".pcapng.cracked"

# webgpsmap_ng.py (regressed)
- search for *.pcap files in your /handshakes/ dir
...
if filename.endswith(".pcap")
...
filename_base = filename_pcap[:-5]  # remove ".pcap"
...
password_file_path = base_filename + ".pcap.cracked"
```

Unlike most `.pcap`-vs-`.pcapng` bugs elsewhere in this project (which
usually only break a secondary startup backlog scan while a live
per-event path still works), this filter drives `webgpsmap_ng.py`'s
*entire* map-population logic - there's no separate live-event path that
bypasses it. On this device, it would never find any real capture files
at all; the plugin's core feature is dead on arrival as shipped.

**One genuine addition, not present in the bundled default or `f0xtr0t`:**
explicit `.paw-gps.json` GPS-source file support:
```python
if self._file.endswith(".paw-gps.json"):
    ...  # an old paw-gps format: {"long": ..., "lat": ...}
```
Only useful if `paw-gps.py`/`paw-gps_ng.py` (also found in this project's
audit, not selected for review this round - see Group 34) are ever
installed alongside this plugin, since those are what would actually
produce `.paw-gps.json` files.

**Fix:** global `.pcap` -> `.pcapng` swap throughout `webgpsmap_ng.py` -
the backlog-scan filter, the base-filename stripping, and the
cracked-password lookup suffix. Same fix shape as the recurring
`.pcap`/`.pcapng` pattern documented throughout this project (Clusters
5/6, etc.). Not applied this round - kept per broad-scope philosophy,
documented for whenever this plugin (or its `.paw-gps.json` support
specifically) is prioritized.

## 6. Dependencies (kept plugins)

`wardriver-pwnagotchi-plugin`/`wardriver_ng.py`: `scapy` (pip, declared
but unused - same boilerplate pattern seen elsewhere), a writable CSV
directory (default `/home/pi/wardriver`), and (optionally) a WiGLE API
key for uploads. `f0xtr0t`/`webgpsmap_ng.py`: no special hardware beyond
GPS-tagged capture data already being produced by another GPS plugin;
`webgpsmap_ng.py` specifically benefits from `paw-gps.py` if that's ever
installed, for its `.paw-gps.json` support to have anything to read.
