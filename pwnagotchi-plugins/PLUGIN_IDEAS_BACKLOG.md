# Plugin Ideas Backlog (Claude / patrickato)

Running list of pwnagotchi plugin ideas to build later. This is separate
from the existing PwnDoctor gap/ideas document in this repo — that one
covers reliability/diagnostics; this one covers attack, capture,
convert, hash, and GPS functionality for the home-lab red-team-skills
project.

None of these are built yet. When one gets picked up, it moves into its
own self-contained folder under `pwnagotchi-plugins/`, same format as
`claudecrackauto/`, `handshakecompleter/`, `wpa3watch/`, and
`rfcomplianceguide/` — plugin file, `config-example.toml`, full README.

Everything here follows the same scoping principle already established
in the built plugins: any behavior that actively targets or affects a
specific network (deauth tuning, whitelist changes, attack arm/disarm)
is gated to the user's own declared SSIDs/APs. Passive classification
or read-only info can apply more broadly since it doesn't change what
pwnagotchi does to anything.

---

## Attack / Capture / Convert / Hash

1. **PMKID-First Attack Mode** — prefer the clientless PMKID grab before
   falling back to deauth-based 4-way capture. Quieter and less
   disruptive to clients on the target AP.

2. **Adaptive Deauth Throttling** — scale deauth burst count/frequency
   per AP based on observed response, instead of a fixed blast every
   time.

3. **Targeted Single-Client Kick** — deauth one specific connected
   client at a time rather than broadcasting to every client on the AP,
   so reconnection behavior can be tested without disrupting the whole
   network.

4. **Multi-Session Handshake Merge** — merge partial captures for the
   same AP collected across different sessions, instead of needing a
   single session to capture a complete 4-way.

5. **Default-Credential Pattern Checker** — identify router vendor from
   BSSID OUI and flag whether it matches known default-password
   patterns for that make/model, as a fast own-gear risk check before
   any wordlist attempt.

6. **Hash Format Auto-Detector** — inspect a capture and automatically
   select the correct hashcat mode (WPA/WPA2, PMKID, legacy WEP)
   instead of assuming `-m 22000` unconditionally.

7. **Rule-Based Mutation Cracking** — apply hashcat rule files
   (leetspeak, appended digits, casing variants) on top of a wordlist,
   for more realistic coverage than a flat dictionary pass.

8. **Passive-Only Mode Toggle** — a hard switch for "PMKID/beacon
   collection only, zero deauth traffic," for the quietest possible
   test run.

## GPS

9. **GPS-Triggered Mode Switch** — automatically drop to fully
   passive/dormant the moment GPS shows the unit has left the
   configured property boundary, and resume normal behavior once back
   inside.

10. **GPS-Gated Attack Arm/Disarm** — stronger version of #9: actively
    suspend all deauth/attack behavior outside a geofenced polygon,
    rather than just switching personality mode.

11. **Speed-Adaptive Scan Rate** — dwell longer per channel while
    stationary, hop faster while moving, based on GPS-derived speed, so
    a walking/driving perimeter loop doesn't miss APs.

12. **Dead-Zone Field Feedback** — real-time buzzer/LED signal-strength
    feedback toward a target AP while walking a test route, instead of
    reviewing a log after the fact.

13. **Waypoint Coverage Tracker** — program a patrol route around the
    property and track which waypoints were actually covered in a
    session, to confirm a perimeter test was complete.

## GPS / Location Logging

User-picked favorites from this category — consider building as one
combined location-logging plugin with a few tracked data streams,
rather than four separate plugins, since they naturally share the same
underlying GPS read and reinforce each other (fix-quality context makes
the heatmap and AP-location data trustworthy; the GPX track ties a
session together spatially).

14. **Handshake Heatmap Log** — logs GPS position + signal strength for
    every capture over time, building a cumulative heatmap of where on
    the property captures actually succeed (vs. the stock GPS plugin's
    one-off per-handshake tag).

15. **GPX Session Track Recorder** — records the physical path walked
    each session as a standard GPX file, importable into Google Earth
    or any mapping tool.

16. **AP First-Seen Location Log** — records the exact GPS point and
    timestamp where each new AP was first detected, for a discovery
    timeline that can be plotted on a map.

17. **GPS Fix-Quality Log** — logs HDOP/satellite count/fix quality
    alongside each tagged position, so it's clear how trustworthy a
    given GPS-tagged location actually is.

## Deauth / PMKID / PCAP mechanism

18. **Zero-Byte / Failed-Attempt Cleanup** — detects when an attack
    attempt produced an empty or junk `.pcap` (silent failure) and
    cleans it up immediately, instead of letting dead files pile up
    per AP.

---

*Last updated: 2026-09-28*
