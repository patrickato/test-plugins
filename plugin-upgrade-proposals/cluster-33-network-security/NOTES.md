# Notes: Network / Security analysis cluster

**Status: 9 of 14 REMOVED, 1 moved to `plugins-wip` and fixed
(`wifi_jammer.py`), 3 reviewed with decision deferred, 1 kept as-is.**

## The shared fatal defect (9 of 14)

`dns_spoof_detector.py`, `mac_adress_logger.py`, `mac_randomizer.py`,
`network_intrusion_detector.py`, `network_mapper.py`,
`network_packet_sniffer.py`, `rogue_ap_detector.py`, `traffic_sniffer.py`,
`wifi_analyser.py`, and `wifi_jammer.py` (10 total, all credited to the
same author, "Deus Dust") all open with:

```python
from pwnagotchi.plugins import BasePlugin

class SomePlugin(BasePlugin):
    ...
    def on_loaded(self):
        self.log.info("...")
```

**`BasePlugin` does not exist anywhere in this fork** - confirmed by
grepping the real cloned `jayofelony/pwnagotchi/pwnagotchi/plugins/__init__.py`
source. The only base class it defines is `plugins.Plugin`, which uses
`__init_subclass__` to auto-register itself the moment the class is
*defined* (not instantiated) - a completely different mechanism than
what these files assume. Every one of these plugins raises `ImportError`
the instant pwnagotchi tries to load its module. None of them can ever
run, under any configuration, on this or (as far as could be checked)
any other real pwnagotchi fork. This is the same "imagined API" root
cause already found in `wd_honey_Pot.py` and the already-removed
`bluetooth_scanner.py` - not a bug to patch, the entire premise the code
was written against doesn't exist here.

They also all call `self.log.info(...)`/`self.log.error(...)` - even a
correctly-subclassed `plugins.Plugin` instance has no `self.log`
attribute, so this would be a second independent crash even if the
import somehow succeeded.

## Per-plugin disposition within that group of 10

- **`dns_spoof_detector.py`** - REMOVED. Even setting the fatal bug
  aside, it would only ever see anything if the pwnagotchi's WiFi
  interface is associated to a network and passing real DNS traffic
  through it - not the monitor-mode recon state this device normally
  runs in. Deployment mismatch on top of the fatal bug.
- **`mac_adress_logger.py`** - REMOVED. Trivial to fix in isolation, but
  adds nothing: the MAC is already embedded in every handshake filename
  and tracked by multiple other plugins already on this list.
- **`mac_randomizer.py`** - REMOVED. Redundant with `neurolyzer.py`
  (Attack/Capture category), which does the same MAC-rotation job and
  is "well-engineered, no bugs found" per its own Cluster 30 review.
  `neurolyzer.py`'s bullet has been updated to note the conflict this
  created is now moot.
- **`network_intrusion_detector.py`** - REMOVED. Beyond the fatal bug,
  this isn't actually an intrusion detector even in concept: its
  `packet_handler` logs `"Intrusion detected: {src} -> {dst}"` for
  *every single IP packet it sees*, with no anomaly logic of any kind.
  Nothing here to save even with a rewrite of the import.
- **`network_mapper.py`** - REMOVED. Requires `python-nmap` + a system
  `nmap` binary (new dependencies), hardcodes the scan target as
  `192.168.1.0/24` (wrong for most home networks), and is only useful
  at all if the pwnagotchi is actually attached to a LAN rather than
  doing its normal monitor-mode recon.
- **`network_packet_sniffer.py`** / **`traffic_sniffer.py`** - REMOVED
  (both). These are the identical `scapy.sniff(prn=lambda p:
  print(p.summary()))` script, copy-pasted under two different names by
  the same author (one fires from `on_loaded`, the other from
  `on_periodic` - the only difference). Not real tooling, no filtering
  or persistence, and blocking/unbounded (`scapy.sniff` with no filter
  or timeout) on top of the fatal import bug.
- **`rogue_ap_detector.py`** - REMOVED, though this was the closest
  thing to a good idea in this group. It already receives a live
  `access_points` list via the real `on_wifi_update(self, agent,
  access_points)` hook, but then ignores it and shells out to `iwlist
  wlan0 scan` instead (which generally doesn't even work against a
  monitor-mode interface) - so even a "fixed" version would need real
  rework, not just a base-class swap. `agent.display_text()` (called
  when a rogue AP is found) also isn't a real Agent method on this
  fork. If ever revisited, this is the one worth rebuilding using the
  `access_points` argument it's already handed rather than the broken
  `iwlist` shell-out.
- **`wifi_analyser.py`** - REMOVED. Same shape as `rogue_ap_detector.py`
  (shells out to `iwlist wlan0 scan` when it already gets `access_points`
  via `on_periodic`... actually via nothing - it doesn't use a real
  AP-list hook at all), and its `on_periodic` also references `fonts`
  without ever importing it (`NameError` even past the fatal bug). Its
  end result mostly duplicates what the stock UI/other plugins (wigle,
  grid) already show.
- **`wifi_password_cracker.py`** - REMOVED. Shells out to `aircrack-ng`
  with a hardcoded placeholder wordlist path
  (`/path/to/wordlist.txt`) that doesn't exist on any real system.
  Fully redundant with `better_quickdic.py` and the crack-pipeline `_ng`
  plugins already on this list, which do this job correctly.
- **`wifi_jammer.py`** - the one plugin in this group judged worth a
  real rebuild. See the dedicated section below and
  `plugins-wip:wifi-jammer-suite/NOTES.md` for full detail.

## `wifi_jammer.py` - fixed and moved to `plugins-wip` (`WifiJammerNG`)

Beyond the shared fatal `BasePlugin` bug and an `access_point.bssid`
attribute-access bug (this fork hands plugins a dict, not an object),
the original had **no targeting scope whatsoever** - `on_handshake`
fired at whatever AP it was given, unconditionally, via
`aireplay-ng --deauth 0` (a count of `0` in aireplay-ng means "send
continuously, forever," not zero).

Rebuilt around an explicit `authorized_networks` allowlist (BSSID
and/or SSID form) that is **empty by default** - the plugin loads and
does nothing at all until specific hardware is explicitly named. Every
firing path (association, handshake, and a manual "fire now" webhook
page) checks against this list before ever calling into bettercap. Also
replaced the `aireplay-ng` subprocess entirely with `agent.run('wifi.deauth
<mac>')` - the same in-process bettercap API call this fork's own core
`pwnagotchi/agent.py` already uses for its own normal deauth behavior,
which avoids a new binary dependency, interface-name guessing, and two
processes contending for the same monitor interface. Full writeup,
design rationale, and test suite in `plugins-wip:wifi-jammer-suite/NOTES.md`.

## Reviewed, decision deferred (not removed, not yet fixed)

- **`beacons.py`** - uses the real base class and hooks correctly (an
  actual, functional plugin, unlike the 10 above), but `__init__`
  hardcodes the monitor interface as `wlan0mon` and immediately does
  `open("/sys/class/net/wlan0mon/address")` at construction time -
  crashes plugin load if that interface isn't up yet (typical, since
  plugins usually load before bettercap brings the monitor interface
  up) or isn't literally named `wlan0mon`. Its own `pack_info()` could
  also raise `ValueError` via `self._faces.index(face)` if the live
  face value isn't in its hardcoded face list (e.g. a custom face/theme
  pack in use). Its own `on_loaded()` log line honestly warns "this
  plugin is not stealthy at all - anyone could see the beacons when
  they search for WiFi networks," a real, self-disclosed tradeoff worth
  knowing about before enabling it. Fix would mean reading the
  interface from `pwnagotchi.config['main']['iface']` (the same
  pattern its sibling `beaconify.py` already uses correctly) and
  guarding the face lookup.
- **`test_security.py`** ("SecurityMonitor") - also uses the real base
  class and hooks, but `deep_packet_inspection()`/`analyze_packet()`
  read `self.security_issue_detected` without it ever being initialized
  in `__init__` - only set (and only conditionally) inside
  `analyze_packet()`. If none of the 10 packets it sniffs per call trip
  that branch (the common case), `on_excited` - a normal, frequent
  personality state - crashes with `AttributeError` every time. Also
  checks `ap.get("essid")` for the network name, but this fork's real
  AP dict key is `hostname`, so that check never actually identifies a
  real SSID. Explicitly marked `# THIS PLUGIN IS ON DEVELOPMENT` in its
  own header, and most of its methods are unfilled stubs
  (`# Replace with actual X logic`) - closer to a work-in-progress
  skeleton than a finished plugin.

## Kept as-is

- **`beaconify.py`** - real base class, real hooks, reads the interface
  from config correctly. Its automatic pwngrid-restart retry/backoff
  logic is entirely commented out (dead code - it only ever attempts
  one restart, never actually retries), but that's a missed-resilience
  nit, not a bug worth a rebuild on its own.

## Dependencies

`wifi-jammer-suite` (the only thing actually built this cluster): none
beyond what pwnagotchi/bettercap already provide - no new pip packages,
no new binaries. The 9 removed plugins variously needed `scapy`,
`python-nmap` + system `nmap`, and `aircrack-ng`/`aireplay-ng` - moot
now that they're removed.
