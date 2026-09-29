# Notes: last two unreviewed Attack/Capture plugins

**Status: 1 of 2 REMOVED, 1 saved for later (fix candidate).**

## `potfilesorter.py` - REMOVED

Advertised itself as a webhook page to sort/organize cracked results plus
some wpa-sec backup/config helpers. On close read, every path through it
is broken:

- `on_webhook(self, _download_from_wpasec, backup_configs, copy_config, checkwpaconfig, readpotfiledata, agent)`
  - the real framework calls `on_webhook(self, path, request)`. This
    signature can never match that call, so the entire advertised
    feature (the "sorter" itself) is unreachable dead code - it has
    never actually run on this fork, or any other pwnagotchi build using
    the standard plugin dispatch.
- `on_loaded()` calls `self.load_data(data_path)` - no such method exists
  anywhere in the class. `AttributeError` on every load, were `on_loaded`
  the only thing that mattered here (it's caught by the framework's
  loader, so the plugin just silently fails to do its startup step, not
  crash the daemon).
- `readpotfiledata()` references a free variable `handshake_dir` that is
  never defined anywhere in scope - `NameError` if this method were ever
  reachable.
- Several class-level path constants hardcode Android WiFi config store
  paths (`/home/pi/WiFiConfigStore.xml`, `/home/pi/WiFiConfigStoreSoftAp.xml`)
  that don't exist on a Linux/Raspberry Pi filesystem at all - confirmed
  absent from the plugin's own sample `configs/potfilesorter.toml`, so
  this isn't a documented alternate mode, just leftover/copied code.
- **The serious one**: `copy_config()`'s error branches call bare
  `exit()`. `exit()` raises `SystemExit`, which is a `BaseException`
  subclass, NOT an `Exception` subclass. The framework's
  `PluginEventQueue.process_events()` (confirmed by reading
  `pwnagotchi/plugins/__init__.py` in the cloned jayofelony source) wraps
  every plugin hook call in `except Exception:` - it does NOT catch
  `SystemExit`. If this code path were ever reached, it would kill the
  entire pwnagotchi daemon process, not just this one plugin's hook.
  Currently unreachable (blocked by the broken `on_webhook` signature
  above), but would become live and dangerous the moment someone "fixed"
  the signature without also removing these `exit()` calls.

**Decision: remove entirely.** The core feature is unreachable dead code
riddled with independent fatal bugs, and the one thing that plausibly did
work (downloading/organizing cracked results) is already covered by
`BanthexNG` and `HashesPwnagotchiNG` in `plugins-wip`, which handle
downloading cracked results from their respective services directly.
Rebuilding this one would mean rewriting nearly the whole plugin for a
feature we already have elsewhere.

## `meshpwnstic.py` - saved for later (fix candidate)

A 752-line plugin giving remote monitoring/control of the pwnagotchi over
a Meshtastic LoRa mesh radio: text commands over the mesh for `/status`,
`/restart`, `/plugin list|enable|disable|toggle|refresh`, `/set`, `/echo`,
`/deauth`, `/assoc on|off`, and `/bcap <raw bettercap command>`.

Genuinely useful concept (out-of-band control with no WiFi/network
dependency) and mostly functional as written, but has real issues:

1. **No sender authentication at all.** None of the mesh command handlers
   check who sent the message. Any device broadcasting on the same
   Meshtastic mesh can run `/bcap` (arbitrary bettercap commands),
   toggle `/deauth` or `/assoc`, or `/restart` the device. Compare this
   to the Discord bot built earlier in this project, which gates
   destructive commands behind `ctx.author.id == AUTHORIZED_USER_ID`.
   This is the main reason it isn't a clean "just fix and move on."
2. `on_handshake()`'s GPS sidecar write does
   `filename.replace(".pcap", ".gps.json")` - the same recurring
   extension-assumption bug seen throughout this whole project. On this
   fork's real `.pcapng` filenames this doesn't produce a clean
   `.gps.json` sidecar the way `GPSTaggerNG`/`HandshakesDLNG` do.
3. Line ~328, inside the `NODEINFO_APP` packet handler in `onReceive()`:
   `self.nodes['num'] = user` uses the literal string `'num'` as the dict
   key instead of the local variable `num` (extracted from
   `packet['from']`) - every node-info update overwrites the same single
   dict entry instead of keying per-node. The separate `onNodeUpdated()`
   pub/sub handler does this correctly (`self.nodes[node['num']] = node['user']`),
   so this is a genuine, isolated bug in one code path only.
4. Two exception handlers (~lines 460, 477) call `logging(e)` -
   `logging` is the imported *module*, not callable, so this raises a
   fresh `TypeError` instead of logging the original error. Likely
   swallowed by an outer `try/except Exception` in `onReceive()` (which
   does log correctly), just with a confusing/wrong message in the log.
5. `onRebooting()` calls `self.interface.sendText("Rebooting")` with no
   check that `self.interface` isn't `None` first - possible
   `AttributeError` if the radio isn't connected at reboot time.

**Decision: save for later.** Worth fixing (mainly for the auth gap) when
this cluster comes back up - recommend adding a configurable authorized-
node allowlist (same shape as the Discord bot's `AUTHORIZED_USER_ID`
gate) plus the four smaller fixes above, then moving it to `plugins-wip`.
Not touched this pass.

## Dependencies

`potfilesorter.py`: none beyond stdlib (moot now - removed).
`meshpwnstic.py`: the `meshtastic` Python package plus a physical
Meshtastic-compatible LoRa radio connected to the pwnagotchi (typically
USB serial) - out of scope to verify from this sandbox either way.
