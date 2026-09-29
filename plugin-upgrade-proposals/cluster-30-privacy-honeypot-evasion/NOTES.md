# Cluster 30 - Attack/Capture category, continued: privacy / honeypot / evasion

Three plugins reviewed: `privacy-nightmare.py`, `wd_honey_Pot.py`,
`neurolyzer.py` (all from the Attack/Capture category pass).

## What each is/does

- **`privacy-nightmare.py`** (itsdarklikehell/pwnagotchi-plugins) - GPS-tags
  handshake logging and opens a second bettercap websocket listener for
  extra event coverage.
- **`wd_honey_Pot.py`** (itsdarklikehell/pwnagotchi-plugins) - simulates a
  decoy "honeypot" AP and tries to mask MAC addresses in its logs for
  privacy.
- **`neurolyzer.py`** (alienmajik) - MAC-rotation/evasion: detects
  WIDS/WIPS SSID blacklists and responds with MAC change + channel hop +
  TX power change + traffic shaping; also does hardware capability
  discovery (Nexmon/Broadcom injection detection).

## `privacy-nightmare.py` - decision: fix and move to `plugins-wip`

Nine source-verified bugs found (self.gps_hot referenced before being
set; a guaranteed NameError on `latlong` whenever GPS isn't locked - the
common case; two bare-indexed config options; a redundant/leaking
hand-rolled second websocket thread where this fork's real
`on_bcap_<event>` hooks already cover the same events; a new-AP handler
that passed the wrong argument shape, guaranteeing a crash; an
unguarded assumption that AP/station arguments are always full dicts,
when this fork can hand a plugin a bare MAC string instead; plus two
more found only while rebuilding - invalid multi-object JSON output
files, and a hostname-only filename that lets two different APs sharing
an SSID overwrite each other's file).

Approved improvements: a `.gps.json` sidecar written next to each
handshake capture, in the same schema `handshakes_dl_ng.py` (Cluster 29)
already reads; a distance filter (`min_regap_distance_feet`, default 50
feet - sized around typical consumer GPS drift under normal conditions,
not this specific test setup, per explicit instruction) so a restart
doesn't blindly rewrite every AP's file again without real movement; a
rate-limited "no GPS fix" log instead of either a crash or per-event
spam; and a `manage_gps` flag (default off) so this plugin doesn't fight
the fork's own built-in `[main.plugins.gps]` over the same device unless
explicitly told to take it over.

Full research, every fix, and full sandbox test results:
`plugins-wip:gps-tagger-suite/NOTES.md`. Built as `gps-tagger-suite`
(`GPSTaggerNG`) in `patrickato/plugins-wip`.

## `wd_honey_Pot.py` - decision: deferred, left on the list

Not fixable with a patch. It calls a nonexistent `self.register_event()`
method (guaranteed crash on load) and listens for event names
(`"wifi-handshake"`, `"ap-beacon"`) that don't exist anywhere in this
fork's real framework - the same "imagined API" root cause as the
already-removed `bluetooth_scanner.py`. It also never assigns `self.ui`
despite a background timer calling `self.ui.set(...)` ~60 seconds after
load (a second, independent guaranteed crash that also kills the timer's
own re-scheduling), has a dead `setup()` factory function this fork's
loader never calls, and its MAC-masking "privacy" feature is a
functional no-op (it masks a freshly-generated random MAC, not any MAC
actually present in the log line).

Options presented to the user: (A) a full rewrite from scratch against
real events/hooks, keeping only the honeypot concept; (B) drop it
entirely; (C) fold a lightweight decoy-AP feature into another plugin
instead of a standalone one. Decision: **save for now, revisit later.**

## `neurolyzer.py` - decision: deferred, left on the list

No bugs found - by far the most carefully engineered plugin reviewed in
this cluster (proper `fcntl` locking, a retrying subprocess helper, real
hardware capability discovery, graceful self-disable on bad config, full
try/except with traceback logging around its main hook). Improvements
suggested: per-measure config toggles (MAC change / channel hop / TX
power / traffic shaping independently switchable), a cooldown/rate-limit
on the evasion protocol, and surfacing the current stealth level on the
UI screen.

The one real concern: it independently rotates the device's MAC address,
and **`mac_randomizer.py`** (Network/Security analysis category, not yet
independently reviewed) does the same thing - if both are ever enabled,
they'll fight over the interface's MAC. Both plugins are now
cross-referenced in `MASTER_PLUGIN_LIST.md` and their fates will be
decided together. Decision: **save for now, revisit later** - flagged so
the conflict isn't forgotten before either is finalized.

## Dependencies

- `gps-tagger-suite` (built this cluster): no new apt/pip packages -
  Python standard library only.
- `wd_honey_Pot.py` / `neurolyzer.py`: no changes made, no dependency
  research needed yet.
