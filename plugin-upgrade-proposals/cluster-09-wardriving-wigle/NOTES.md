# Notes: wardriving / WiGLE plugin cluster

**Status: all 10 KEPT on the master list.** 3 confirmed broken as
shipped (fixes documented, not applied), 2 have a dependency/design
note worth knowing, 5 are clean with no issues found.

Source repos used for this cluster (beyond the two already cloned for
earlier clusters): `AlienMajik/pwnagotchi_plugins` (`snoopr.py`,
`theylive.py`), `fmatray/pwnagotchi_GPSD-ng`, `wpa-2/Pwnagotchi-Plugins`
(`wiglelocator.py`).

## Broken as shipped

### `f0xtr0t` - fatal, only trigger path

`load_gps_from_dir()` - the function that populates its whole
webgpsmap-based map - scans the handshake directory with:

```python
all_pcap_files = [
    os.path.join(handshake_dir, filename)
    for filename in all_files
    if filename.endswith(".pcap")
]
```

then strips exactly 5 characters (`filename_pcap[:-5]`) to get the
base name for locating `.gps.json`/`.geo.json`/`.paw-gps.json`
companions, and separately builds a `<base>.pcap.cracked` path to
look up passwords. This image only ever writes `.pcapng` - so
`all_pcap_files` is always empty here, and the entire map/position
feature never populates a single point, ever. This is the plugin's
only path to data (no live/`on_handshake` fallback), so it's fatal,
not partial, the same class of bug as Cluster 6's cloud-upload
plugins.

**Fix:**

```python
# before
all_pcap_files = [
    os.path.join(handshake_dir, filename)
    for filename in all_files
    if filename.endswith(".pcap")
]
...
filename_base = filename_pcap[:-5]  # remove ".pcap"

# after
all_pcap_files = [
    os.path.join(handshake_dir, filename)
    for filename in all_files
    if filename.endswith(".pcap") or filename.endswith(".pcapng")
]
...
filename_base = filename_pcap[:-7] if filename_pcap.endswith(".pcapng") \
                else filename_pcap[:-5]
```

The `.pcap.cracked` password-file lookup (`os.path.basename(pos_file)
.split(".")[0] + ".pcap.cracked"`) also needs the same
extension-awareness if the cracked-password feature is to work
post-fix.

### `Pwnagotchi-JSON-to-Wigle-CSV.py` - not a plugin, real crash risk

No `plugins.Plugin` subclass, no `on_*` hooks - a standalone CLI
script meant to be run by hand: `python
Pwnagotchi-JSON-to-Wigle-CSV.py /home/pi/loot`. Its own header comment
even says so ("Usage $ python ... /home/pi/loot").

Unlike `gsmfake.py` (Cluster 8) or this same author's other
standalone scripts, this one is a real hazard if it ever ends up
somewhere pwnagotchi's plugin loader scans it (currently it's filed
under a `Scripts/` subfolder in the source repo, not directly in the
plugins folder, but the master list treats it as a plugin candidate,
so it's worth flagging clearly). The last four lines run
unconditionally at import time, not inside an `if __name__ ==
"__main__":` guard:

```python
if len(sys.argv) != 2:
    print("Usage: python Test-JSON-toCSV.py <json_folder_path>")
    sys.exit(1)

json_folder_path = sys.argv[1]
convert_json_to_csv(json_folder_path)
```

If the pwnagotchi process ever imports this file as a module (`sys.argv`
inside a running daemon won't have exactly 2 elements), this calls
`sys.exit(1)` **inside the live pwnagotchi process**. `SystemExit`
does not inherit from `Exception`, so a loader that only wraps each
plugin's import in `except Exception` would NOT catch it - this could
take down the whole agent, not just fail to load one plugin.

**Fix:**

```python
# before
if len(sys.argv) != 2:
    print("Usage: python Test-JSON-toCSV.py <json_folder_path>")
    sys.exit(1)

json_folder_path = sys.argv[1]
convert_json_to_csv(json_folder_path)

# after
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python Test-JSON-toCSV.py <json_folder_path>")
        sys.exit(1)

    json_folder_path = sys.argv[1]
    convert_json_to_csv(json_folder_path)
```

Also worth noting per the author's own comment: "Currently does not
work with the Tracker plugin's JSON's" - it expects the
`ssid_bssid.json` naming pattern that `mygps.py`/`gps-plus.py`-style
plugins produce, not `tracker.py`'s `hostname_mac.json` naming.

### `wardrive.py` - fatal on load, and wrong screen target even if fixed

`on_ui_setup()` calls `os.path.exists("/etc/pwnagotchi/config.toml")`
but the file never imports `os` anywhere (only `datetime`, `toml`,
`yaml`, `json`, `logging`, `pwnagotchi`, `subprocess`, `threading.Lock`
are imported). This is a guaranteed `NameError` the moment
`on_ui_setup` runs, on every screen type, not a config-dependent bug.

Separately, even fixed, the UI-element-creation block is wrapped in
`if ui.is_waveshare_v2():` with no `else` - on any other display
(including the user's MPI3501 TFT), no elements ("clock", "wardriver",
"latitude", "longitude", "altitude") ever get created, yet
`on_ui_update()` unconditionally calls `ui.set("clock", ...)` and
`ui.set("wardriver", ...)` every cycle - likely raising each cycle
against elements that don't exist.

**Fix (minimal):**

```python
# add near the top
import os
```

For the screen-targeting issue, either add an `else` branch computing
generic default positions (matching the pattern most other plugins in
this project use - checking `ui.is_waveshare_v2()` /
`is_waveshare_v1()` / `is_inky()` / etc. with a final generic
fallback), or accept that this plugin is Waveshare-v2-only as shipped.

## Works, but shares the known `.pcap`/`.pcapng` bug

### `pwnagotchi_GPSD-ng` (fmatray) - not the same project as Cluster 8's `gpsdeasy.py`

Worth being clear this is a different, more actively developed
project (v1.9.8, dataclass-based, ships its own `ntrip-selector.py`
companion for RTK correction sources) than `gpsdeasy.py` (rai68,
Cluster 8) despite the conceptual overlap (both talk to a `gpsd`
daemon). Same underlying bug pattern found elsewhere in this project,
in three places:

```python
# on_handshake - filename mangling, same as gps-plus.py/gpsdeasy.py/mygps.py
gps_filename = filename.replace(".pcap", ".gps.json")

# backlog scan - .pcap-only, same class of bug as Cluster 5
pcap_filenames = glob(os.path.join(self.handshake_dir, "*.pcap"))

# cracked-password lookup - also .pcap-only
pcap_filename = os.path.join(self.handshake_dir, f"{hostname}_{mac}.pcap")
```

Same fix pattern as documented in Cluster 5/8's notes applies to all
three call sites: check/strip `.pcapng` before falling back to
`.pcap`.

## Clean - no issues found

- **`snoopr.py`** (AlienMajik, v7.1.0) - large WiFi/BLE/ADS-B
  surveillance-detection plugin (rogue-device geofencing,
  trilateration, OpenSky integration, mesh alerts, SQLite
  persistence). Doesn't reference `.pcap`/handshake filenames
  anywhere - gets its GPS fix from `agent.session()['gps']` directly
  (same as `gps-plus.py`), not from a `"gps"`-named plugin lookup, and
  doesn't touch capture files at all. No `__dependencies__` declared
  in the code; README documents `requests` (always required) plus
  optional `bleak`, `cryptography`, `scipy` for BLE/crypto/advanced
  features.
- **`theylive.py`** (AlienMajik, forked from rai68's `gpsdeasy.py`,
  v2.2.2) - the header comment states it was explicitly "Verified
  against jayofelony Pwnagotchi 2.9.5.8 (handshakes are .pcapng...)"
  and the code backs that up: `on_handshake` checks
  `for suffix in (".pcapng", ".pcap"):` before building the GPS
  filename. This is a direct, already-fixed alternative to Cluster
  8's `gpsdeasy.py` for anyone using a `gpsd`-daemon GPS setup -
  worth remembering if `gpsdeasy.py` is ever revisited.
- **`wardriver-pwnagotchi-plugin`** (CyberArtemio, v2.0) - actively
  maintained, uploads seen networks to WiGLE. Uses
  `on_unfiltered_ap_list` (live AP data), never touches handshake
  filenames - immune to the pcap/pcapng bug class entirely. (Note:
  this is the current upstream version of the same author's plugin;
  older forks `wardriver.py`/`wardriver_ng.py` exist in
  itsdarklikehell's repo but were never added to the master list, so
  no action needed there.)
- **`warwalking_trails_kml_single.py`** - accumulates one continuous
  KML trail file across the whole session (appends a `Placemark` per
  epoch to a single XML document) - does what "trail" implies.
  Depends on a plugin registered as `"gps"` (see below).
- **`WigleLocator`** (wpa-2, v2.2.1) - queries the WiGLE API for AP
  coordinates by BSSID, not by filename - immune to the pcap bug.
  Rate-limited, cached, handles WiGLE's 429 responses and daily quota
  properly. Requires the user's own WiGLE API key.

## Dependency/design notes (not bugs, not blockers)

### `tracker.py` and `warwalking_trails_kml.py` depend on a `"gps"`-named plugin

Same architecture note as Cluster 8: both call
`plugins.loaded["gps"]` and only do anything once a plugin literally
registered as `"gps"` is active - the same open question from Cluster
8 about whether `gps-plus.py` satisfies that name applies here too.

### `warwalking_trails_kml.py` (the non-`_single` one) - design flaw, not a crash

Creates a brand-new single-point KML file every epoch
(`f"Trail-{date_time_str}.kml"` computed fresh each call), rather
than accumulating one connected trail like its `_single` sibling
does. It still "logs position" as described, just not as a usable
trail - produces hundreds of one-point files instead of one line.
Functionally works, just doesn't do what a "trail" implies; the
`_single` variant is the one that actually does.

## Dependencies (all 10)

`requests` (pip) needed by `snoopr.py`, `wardrive.py`,
`wardriver-pwnagotchi-plugin`, `WigleLocator`; `snoopr.py` additionally
optional `bleak`/`cryptography`/`scipy` for BLE/crypto/trilateration
features. `pwnagotchi_GPSD-ng` needs `gpsd`/`python3-gps` (apt) plus a
running `gpsd` daemon - same class of setup as Cluster 8's
`gpsdeasy.py`. `f0xtr0t` needs `python-dateutil` (`dateutil.parser`)
and optionally the `gpsd` Python module. `WigleLocator` needs a WiGLE
account/API key. None of the rest declare anything beyond the usual
boilerplate `scapy` pip entry (unused).
