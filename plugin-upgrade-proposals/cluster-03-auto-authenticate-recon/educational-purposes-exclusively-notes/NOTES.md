# Notes: `educational-purposes-exclusively.py`

**Status: KEPT AS-IS — no upgrade plan needed, minor notes only.**

Unlike the other three plugins in this cluster, this one works close
to as described out of the box - no missing/dead top-level import, no
config-ignoring bug, real RSSI-gated single-SSID connect logic
matching `self.options["home-network"]` / `["minimum-signal-strength"]`.
Kept on the master list with no fix required to load or run.

## Minor things worth knowing, not blocking

- **`_port_scan(self, target_ip)` is dead code.** It sweeps ports
  1-1024 against `target_ip` via bash `/dev/tcp` redirection, but
  nothing in the file ever calls it - no hook passes it a target, it
  just sits there unused. The docstring's "internal network recon"
  claim rides on this method existing, but it never actually runs.
  If real recon is ever wanted, this is a rough starting point (would
  need a caller wired up, and a real destination IP - currently
  nothing supplies one), not a finished feature.
- **`_generate_report()` depends on `reportlab`**, which is not
  declared in `__dependencies__`. If this method is ever called (it
  currently isn't, from any hook), it would fail with an
  `ImportError` on a stock install unless `reportlab` happens to
  already be present. Since it's unused, this isn't currently a
  problem - just worth knowing if anyone extends this file later.
- **`_send_notification()` is a stub** - logs a message, does not
  actually send anything anywhere. Same "not currently a problem
  since nothing calls it expecting real delivery" caveat.
- Same MAC-randomization / hostname-spoofing behavior as its sibling
  plugins in this cluster (unconditional, not configurable) - fine to
  leave as-is given it's already working, but worth remembering if
  you ever want to disable that behavior specifically on this one too.

## If this ever gets touched

Given it already works, the honest recommendation is: leave it alone
unless the dead `_port_scan`/`_generate_report`/`_send_notification`
code is specifically wanted wired up into something real. Fixing
unused dead code that doesn't affect current behavior isn't a
priority relative to the other two plugins in this cluster that
currently can't even load.
