# Notes: Bluetooth scanning plugin cluster

**Status: `bluetooth_scanner.py` REMOVED (non-functional by
construction). `blemon_plugin.py` and `bluetoothsniffer.py` KEPT.**

Sources: `blemon_plugin.py` and `bluetoothsniffer.py` from
`itsdarklikehell/pwnagotchi-plugins` (the latter also confirmed
identical in `jayofelony/pwnagotchi-torch-plugins`, jayofelony's own
optional community-plugin repo - see note at the end);
`bluetooth_scanner.py` from `pwnagotchi-unofficial/plugins_archive/`
(Deus73/pwnagotchi-plugins).

Ranked best to worst per the user's request before the keep/remove
decision: `blemon_plugin.py` > `bluetoothsniffer.py` > `bluetooth_scanner.py`.

## 1. What each one is and does

1. **`blemon_plugin.py`** - a BLE (Bluetooth Low Energy) device
   monitor built on bettercap's own `ble.recon` module. Starts a BLE
   scan on `on_ready`, counts currently-visible and max-simultaneous
   BLE devices via bettercap's `on_bcap_ble_device_*` events, shows a
   "BLE" counter on-screen, and runs `ble.enum` against unnamed
   devices to try to learn more about them.
2. **`bluetoothsniffer.py`** - runs `hcitool inq` periodically to
   discover nearby classic-Bluetooth devices, looks up each one's name
   and manufacturer via further `hcitool` calls, and persists
   everything (name, manufacturer, device class, first/last seen,
   sighting count) to a JSON file on disk.
3. **`bluetooth_scanner.py`** - intended to run `hcitool scan`
   periodically and print found classic-Bluetooth devices to the
   screen. As detailed below, it cannot actually do this on any real
   pwnagotchi.

## 2. `blemon_plugin.py` - kept, one small bug

**Bug:** `on_ui_setup` registers the UI element as `"blemon_count"`,
but `on_bcap_ble_device_lost` calls:

```python
ui.set("blecount", "%d/%d" % (self.blecount, self.blemaxcount))
```

- wrong key (missing the `mon`). This call would fail every time a
tracked BLE device is lost. The equivalent line in
`on_bcap_ble_device_new` correctly uses `"blemon_count"`, so this is a
one-off typo, not a systemic mismatch.

**Fix:**
```python
# before
ui.set("blecount", "%d/%d" % (self.blecount, self.blemaxcount))

# after
ui.set("blemon_count", "%d/%d" % (self.blecount, self.blemaxcount))
```

**Minor, not fixed:** uses `if name is "":` (identity comparison
against a string literal) in two places instead of `if name == "":`.
Usually harmless for empty-string literals under CPython's string
interning, but not guaranteed-correct Python and worth cleaning up if
this file is ever touched.

**Why it's otherwise solid:** correctly defers to bettercap's real BLE
event stream rather than reinventing scanning itself, and defensively
self-populates missing `self.options` keys (`"face"`, `"position"`)
inside `on_loaded`/`on_ui_setup` rather than relying on `__defaults__`
- the same smart workaround `xp_grid.py` (Cluster 16) uses, which
means it's unaffected by the project-wide `__defaults__` correction
(Group 31) that affects several other plugins in this project.

## 3. `bluetoothsniffer.py` - kept, three real bugs plus one open question

**Bug 1 - wrong UI key on unload**, same category as `blemon_plugin.py`'s
bug above:

```python
def on_unload(self, ui):
    with ui._lock:
        try:
            ui.remove_element("BluetoothSniffer")   # BUG: element was added as "BtS"
```

The element is added as `"BtS"` in `on_ui_setup`, never as
`"BluetoothSniffer"`. Wrapped in try/except, so it won't crash on
unload, but the `"BtS"` element is never actually cleaned up.

**Fix:** change `ui.remove_element("BluetoothSniffer")` to
`ui.remove_element("BtS")`.

**Bug 2 - `UnboundLocalError` risk in `scan()`.** The `name` variable
is only assigned inside two of the branches that can set
`changed = True` (the "name was Unknown, look it up" branch, and the
"brand-new device" branch):

```python
if mac_address in self.data and len(self.data) > 0:
    if "Unknown" == self.data[mac_address]["name"]:
        name = self.get_device_name(mac_address)   # only assigns `name` here...
        ...
        changed = True
    if "Unknown" == self.data[mac_address]["manufacturer"]:
        ...
        changed = True                              # ...or here, without touching `name`
    if device_class != self.data[mac_address]["class"]:
        ...
        changed = True                              # ...or here, without touching `name`
    if current_time - last_seen_time >= self.options["count_interval"]:
        ...
        changed = True                              # ...or here, without touching `name`
else:
    name = self.get_device_name(mac_address)         # new-device branch does assign `name`
    ...
    changed = True

...
if changed:
    with open(self.options["devices_file"], "w") as f:
        logging.info(f"...Saving bluetooths %s into json.", name)   # BUG: `name` may be undefined
```

If `changed` becomes `True` purely from the device-class-changed or
the recount-interval-elapsed branch (both plausible on their own,
independent of the device's name ever being "Unknown"), `name` was
never assigned in that code path, and this log line raises
`UnboundLocalError` - which also means the `json.dump(self.data, f)`
two lines later never runs, so the scan's results for that cycle are
lost, not just the log line.

**Fix:** don't reference `name` unconditionally in that log line -
either log a fixed message, or set `name = self.data[mac_address].get("name", "Unknown")`
at the top of the `if mac_address in self.data` branch so it's always
defined before the `if changed:` block runs.

**Bug 3 - instance-dict defaults, discarded regardless of `__defaults__`
(see Group 31's project-wide correction).** `__init__` sets:

```python
def __init__(self):
    self.options = {
        "timer": 45,
        "devices_file": "/root/handshakes/bluetooth_devices.json",
        "count_interval": 86400,
        "bt_x_coord": 160,
        "bt_y_coord": 66,
    }
```

This fork's plugin loader overwrites `self.options` entirely with
`config['main']['plugins']['bluetoothsniffer']` (or `{}`) after
`__init__` runs, regardless of what's set here - and, per the
project-wide correction, a class-level `__defaults__` wouldn't have
helped either, since this fork never reads it. `on_loaded`/`on_ui_setup`
would `KeyError` on any of these five keys unless all of them are set
explicitly in `config.toml`.

**Fix:**
```toml
# config.toml - no code change needed:
[main.plugins.bluetoothsniffer]
enabled = true
timer = 45
devices_file = "/root/handshakes/bluetooth_devices.json"
count_interval = 86400
bt_x_coord = 160
bt_y_coord = 66
```
or, in code, replace direct `self.options["key"]` indexing with
`self.options.get("key", fallback)` throughout.

**Open question, not confirmed - `hcitool` availability.** The entire
scan/lookup mechanism depends on `hcitool` (`hcitool inq`, `hcitool
name`, `hcitool info`), a deprecated component of older BlueZ releases
that has been dropped from the default package set on some newer
Debian Bookworm-based images in favor of `bluetoothctl`. Whether it's
present on this specific build would need checking directly on the
device (`which hcitool`) - flagged rather than asserted, since I don't
have visibility into which base image this build started from. If
missing, the initial `hcitool inq` call in `scan()` raises
`FileNotFoundError`, which is **not** caught by the surrounding
`except subprocess.CalledProcessError` - that specific exception type
would propagate out of `scan()` uncaught (called from `on_ui_update`,
which fires on every screen refresh).

**Note on origin/mirroring:** this exact file (bug-for-bug identical
aside from formatting) also exists in `jayofelony/pwnagotchi-torch-plugins`,
which `defaults.toml` on this fork lists as one of the URLs offered
for optional custom-plugin installation. It's not part of the truly
auto-loaded `pwnagotchi/plugins/default/` set (confirmed by listing
that folder directly - it contains the standard bundled set like
`grid.py`, `gps.py`, `wigle.py`, `auto_backup.py`, etc., and
`bluetoothsniffer.py` is not among them), so it wasn't excluded by
this project's "minus jayofelony-bundled defaults" rule - just worth
knowing that jayofelony's own repo is one of its available sources,
alongside itsdarklikehell's mirror.

## 4. `bluetooth_scanner.py` - removed, non-functional by construction

Not "buggy" in the sense the other two are - every layer of this file
is built against an API that doesn't exist in this or any pwnagotchi
version:

```python
from pwnagotchi.plugins import BasePlugin   # no such class - confirmed
                                              # against plugins/__init__.py,
                                              # which defines only `Plugin`

class BluetoothScanner(BasePlugin):          # fails to even import
    ...
    def on_periodic(self, agent):            # not a real hook - never called
        ...
        agent.display_text(...)              # not a real method on agent
```

The `ImportError` on the first line means this file fails before any
of its own code executes - the plugin loader's `load_from_file()`
would hit the exception during `exec_module()` and log a load error,
skipping the plugin entirely (confirmed via `load_from_path()`'s own
try/except wrapper in `plugins/__init__.py`). Also missing `import
pwnagotchi.ui.fonts as fonts` despite referencing `fonts.Small`, and
calls `self.log`, an attribute that doesn't exist on the real `Plugin`
base class (plugins use the standard `logging` module directly).
Reads like it was written against an imagined or very early draft of
a pwnagotchi-like API rather than this framework as it actually
exists. Would need a full rewrite from scratch - every hook name, the
base class, and the agent/display API are all wrong - not a patch, so
removed rather than documented-as-fixable, consistent with this
project's handling of `pwnassistant.py` (Cluster 13).

## 5. Dependencies (kept plugins)

`blemon_plugin.py`: bettercap's built-in `ble.recon` module (already
part of bettercap, no separate install) plus a BLE-capable radio - the
Pi 4's onboard Bluetooth chip normally suffices, no dongle needed.
`bluetoothsniffer.py`: the `hcitool` binary (part of `bluez`/legacy
`bluez-hcidump` depending on OS version - see the open question above)
plus a classic-Bluetooth-capable radio (again, the Pi 4's onboard chip
normally suffices).
