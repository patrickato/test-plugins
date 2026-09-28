# Notes: GPS/location status plugin cluster

**Status: 3 of 10 CONFIRMED KEEP** (`gps_error.py`, `gps_sat.py`,
`gps-plus.py`). Remaining 7 (`gps_fix.py`, `gps_grid.py`,
`gps_led.py`, `gps_live.py`, `gpsdeasy.py`, `gsmfake.py`, `mygps.py`)
still under review - decision pending, see "Open items" below.

This is the GPS-hardware/status sub-group split out of the larger
GPS/wardriving pile flagged (but not resolved) back in Group 2.
Wardriving/WiGLE-upload plugins are a separate, not-yet-reviewed
cluster.

User's actual GPS hardware on hand: a u-blox 7 USB GPS dongle, a
second puck-style USB GPS receiver, and another GPS sensor - so any
plugin expecting a real serial/USB GPS device is directly usable, not
theoretical.

## Confirmed keeps

### `gps-plus.py` - KEEP, needs a fix

Drives bettercap's own GPS module directly off a serial/USB device
(`self.options["device"]`, e.g. `/dev/ttyACM0`) - a direct fit for the
u-blox 7 or the puck receiver. Displays lat/long/alt on screen, saves
GPS coordinates alongside each handshake.

**Bug found:** in `on_handshake`, coordinates are saved to a file
computed as:

```python
gps_filename = filename.replace(".pcap", ".gps.json")
```

`str.replace` matches the substring `.pcap` wherever it occurs - it
is not extension-aware. This image's real capture filenames end in
`.pcapng`, and `"net.pcapng".replace(".pcap", ".gps.json")` produces
`"net.gps.jsonng"`, not `"net.gps.json"`. The coordinates *are* saved
(the write itself succeeds), just under a mangled filename that
nothing downstream (map plugins, WigleLocator, manual review) would
know to look for.

**Fix:**

```python
# before
gps_filename = filename.replace(".pcap", ".gps.json")

# after
base = filename[:-len(".pcapng")] if filename.endswith(".pcapng") \
       else filename[:-len(".pcap")] if filename.endswith(".pcap") \
       else filename
gps_filename = base + ".gps.json"
```

Same underlying bug, same fix, also present in `gpsdeasy.py` and
`mygps.py` (see "Open items" below) - all three descend from the same
GPS-tagging idea and made the same extension assumption.

### `gps_error.py` - KEEP

Trivial, no downside to leaving enabled. Reads `plugins.loaded["gps"]`
and reports "Not loaded" / "Not running" / "No data" / "Not fixed"
instead of failing silently when GPS isn't working. Depends on a
plugin registered under the exact name `"gps"` to do anything useful
- harmless and inert until that dependency exists.

### `gps_sat.py` - KEEP

Same author/template as `gps_error.py`. Displays satellite count from
`plugins.loaded["gps"].coordinates["NumSatellites"]`. Cheap diagnostic
value once a `"gps"`-named plugin is active, harmless before then.

## Open items - not yet decided

### The `"gps"` name-dependency catch

`gps_error.py`, `gps_sat.py`, and three more not yet decided
(`gps_fix.py`, `gps_grid.py`, `gps_live.py`) all call
`plugins.loaded["gps"]` - they look up a plugin registered under the
literal name `"gps"`, which is what jayofelony's own **bundled**
`gps.py` (ships with the image) registers as. `gps-plus.py` is a fork
of that same bundled plugin's logic but was not confirmed to still
register under the name `"gps"` (its class is `GPSPlus`, and
pwnagotchi's plugin loader may key on `__name__`/class name rather
than filename) - this needs a direct check on the live install before
assuming `gps-plus.py` satisfies these four's dependency. If it
doesn't register as `"gps"`, either patch its `__name__`/registration
to match, or these four stay inert no matter what GPS plugin is
running.

### `gps_fix.py`, `gps_grid.py`, `gps_live.py` - pending

Same author/template as the two confirmed keeps above (`gps_error.py`,
`gps_sat.py`) - fix-quality readout, grid-peer coordinate sharing, and
per-epoch coordinate refresh, respectively. Same `"gps"`-name
dependency caveat above applies to all three. No bugs found in any of
the three beyond that dependency question. Pending decision alongside
resolving the naming question.

### `gpsdeasy.py` - pending

Talks to a `gpsd` daemon over a local socket rather than driving
bettercap's GPS module directly - heavier setup (installs/configures
`gpsd` itself, plus a systemd service/socket) but supports PPS
time-sync hardware for sub-microsecond accuracy if the GPS device has
a PPS pin. Also pulls in `numpy` + `matplotlib` for an optional
polar/sky-plot webhook feature. Same `.pcap`→`.gps.json` filename-
mangling bug as `gps-plus.py` (same fix applies, see above). Does NOT
depend on a `"gps"`-named plugin - manages its own GPS connection and
its own on-screen fields independently. An alternative to `gps-plus.py`
rather than a companion to it - likely redundant if `gps-plus.py` is
the chosen GPS source, since both talk to the same class of USB/serial
hardware.

### `gps_led.py` - pending

Flashes a physical LED wired to GPIO 26 whenever `on_ui_update` fires.
Manages its own bettercap GPS on/off independently (doesn't depend on
a `"gps"`-named plugin, similar to `gps-plus.py`). Purely a hardware
question - depends on whether an LED gets wired to GPIO 26, unrelated
to which GPS software plugin is running.

### `mygps.py` - pending, leaning drop

GPS via a phone's GPSLogger app over HTTP webhook - built specifically
for the no-GPS-hardware case. Given the user has three actual GPS
devices on hand, this solves a problem that doesn't apply here. Same
`.pcap`→`.gps.json` filename-mangling bug as `gps-plus.py`/
`gpsdeasy.py` (same fix, if ever used). Functionally solid otherwise.

### `gsmfake.py` - pending, leaning drop

Not a real pwnagotchi plugin - no `plugins.Plugin` subclass, no
`on_*` hooks, no `pwnagotchi.plugins` import. It's a standalone
Python 2/3 CLI test-harness script for `gpsd` (`python gsmfake.py -P
2948 /root/fakegps.data`, run by hand), requiring a specific Waveshare
GSM/GPRS/GNSS hat and companion files (`prime_gsm_hat.py`, a patched
`gps/fake.py`) not present in this repo. Author's own description
calls it "real shitty hacks." Misfiled as a plugin.

## Dependencies (confirmed keeps)

`gps-plus.py`: no apt/pip beyond the (unused, boilerplate) `scapy`
pip entry already declared. Needs a serial/USB GPS device path set in
config (`main.plugins.gps-plus.device`, `.speed`).
`gps_error.py`/`gps_sat.py`: same boilerplate `scapy` entry, no real
dependency beyond the `"gps"`-named plugin being loaded and running.
