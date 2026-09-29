# Offensive/Defensive Bluetooth Plugin Ideas
## Idea backlog — 2026-09-29 (from Cluster 37 / Hardware-specific review)

This is an idea/roadmap document, not a build queue — nothing here is approved
for construction yet. It was written up while reviewing the Hardware-specific
plugin cluster (blemon_plugin.py, bluetoothsniffer.py, fix_region.py,
flipperLink.py), after a discussion of the wider offensive-Bluetooth tooling
landscape (Ubertooth, Btlejack, Sniffle, crackle, GATTacker, Flipper/ESP32
Marauder BLE spam, bettercap's BLE module, etc.). Revisit this list once all
plugin clusters are done, or sooner if it becomes relevant.

Target hardware: Pi 4 + jayofelony 64-bit pwnagotchi image, onboard
Broadcom BCM43455 Bluetooth radio via BlueZ. Ideas are split by whether they
need only the onboard radio or an add-on USB dongle.

---

## Buildable with the onboard radio only (BlueZ / bettercap BLE module)

### 1. BLE tracker/tag detector (AirTag / Tile / SmartTag alert)
Passively fingerprints BLE advertisement payloads against the known
manufacturer-data signatures for Apple AirTags, Tile trackers, and Samsung
SmartTags, and flags one that's been in range for an unusual amount of time.
This is effectively a DIY version of Apple/Google's official "unwanted
tracker" alert feature — a **defensive/privacy** tool rather than an
offensive one, but it lives in the same BLE-recon space as
blemon_plugin.py/bluetoothsniffer.py and would be a genuinely useful
always-on plugin.

### 2. BlueBorne-style passive vulnerability fingerprinting
Devices often leak stack/firmware version info in their discovery response.
Cross-referencing that against a small local CVE list (informational only,
no live exploitation) turns the existing scanners from "count of devices
nearby" into "count of devices nearby, with a risk flag on anything running
a stack with known BlueBorne-class issues."

### 3. GATT service/characteristic mapper
For any BLE device that allows an unauthenticated connect (a lot of
consumer IoT does), enumerate its GATT services and characteristics and log
a device fingerprint. Real red-team recon value — builds a catalog of "what
is actually reachable" on a target device, not just "what is advertising."

### 4. Classic-BT (BR/EDR) SDP service scanner
Same idea as #3 but for classic Bluetooth — enumerate what services a
discovered device exposes (OBEX file transfer, serial port profile, etc.)
via SDP, rather than just logging its MAC/name the way bluetoothsniffer.py
currently does.

### 5. WiFi/Bluetooth data-fusion plugin
blemon_plugin.py/bluetoothsniffer.py's device logs and CrackHouseNG's
cracked-network list currently live in separate silos. A fusion plugin
correlating "this BT MAC and this WiFi AP were seen at the same
location/time" adds intel value for free, since both data streams already
exist independently in plugins-wip.

### 6. BLE advertisement spam ("Flipper BLE spam" category)
Floods nearby iOS/Android/Windows devices with bogus pairing-popup BLE
advertisements — fully doable on the stock adapter, well-documented public
attack class (Flipper Zero, ESP32 Marauder both implement it). **Purely
disruptive, not informational** — flagged for the same design treatment as
WifiJammerNG: off by default, and scoped to only fire against MACs
explicitly allowlisted ahead of time, not broadcast indiscriminately. Given
the rural/isolated lab setup this is lower-risk than most deployments, but
default-safe design still applies.

---

## Needs an add-on dongle (~$15-30, e.g. a nRF52840 USB dongle)

The onboard BCM43455 cannot do raw-radio-level promiscuous capture or
connection-following — BlueZ only sees what it's told to see. These need
dedicated sniffer hardware/firmware (Btlejack, Sniffle, or similar).

### 7. True raw BLE sniffing (Btlejack/Sniffle wrapper)
Full promiscuous capture of BLE traffic including connection-following,
exported as pcap for offline analysis in Wireshark.

### 8. BLE pairing-key cracking (crackle)
Downstream of #7 — needs a captured pairing exchange from a raw sniff
first, then runs crackle against it to recover BLE Legacy Pairing keys.

### 9. BLE connection hijacking / GATTacker-style MITM proxy
The most exploit-like item on this list. Also needs the dongle. Would need
the **same allowlist-gate treatment as #6, applied even more strictly** —
this is active man-in-the-middle interception of another device's
connection, not just a nuisance broadcast.

---

## Design notes carried over from prior clusters

- Any plugin here that actively transmits at another device rather than
  just listening (items #6 and #9 especially) should follow the
  authorized-target-allowlist pattern established for WifiJammerNG: empty
  allowlist by default, explicit opt-in required, no blanket "attack
  everything in range" mode.
- A dongle-dependent plugin (#7-#9) should auto-detect whether the
  nRF52840 (or equivalent) is actually plugged in and degrade gracefully
  to a recon-only mode without it, rather than failing to load.
- None of these have been scoped into a plugins-wip suite yet. When
  revisited, they should go through the same process as every other
  cluster: findings/value/upgrade-ideas table first, explicit per-item
  approval, then build.
