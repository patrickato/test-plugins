# Notes: `hp_educational-purposes.py` (aka `CombinedPlugin`)

**Status: REMOVED from the master list (Group 16). Kept here for the
record, not as an active proposal - see the "why not upgraded"
reasoning below before reviving this.**

Source: itsdarklikehell/pwnagotchi-plugins, credited "(edited by:
itsdarklikehell, bauke.molenaar@gmail.com), Andryu Schittone,
@nagy_craig". Filename in the repo is `hp_educational-purposes.py`;
class name is `CombinedPlugin`.

## Why this was removed rather than upgraded

Direct source review found it functionally inert on both of the two
things its own description claims, for three separate, independent
reasons - not one bug, three:

1. **The "honeypot" half never transmits anything.**
   `create_fake_aps()` generates random ESSID strings and random MAC
   addresses and stores them in a Python `set()` (`self.honey_pot_aps`).
   That's it. No `hostapd`, no `scapy.sendp()` of beacon frames,
   nothing goes out over RF. `handle_ap_beacon()` checks whether a
   real beacon event's ESSID happens to match one of these
   internally-generated strings - which it structurally cannot,
   since nothing was ever broadcast with that ESSID. The honeypot
   counters (`detected_fake_aps`, `active_fake_aps`) can only ever
   read zero in real-world operation.

2. **The "auto-connect" half ignores config entirely.**
   `__init__(self, home_network="test-net", home_password="TestNet1")`
   takes these as constructor arguments with hardcoded defaults - but
   pwnagotchi's plugin loader instantiates plugins with no arguments
   (`Plugin()`), so `self.home_network` is always the literal string
   `"test-net"` and `self.home_password` is always `"TestNet1"`,
   regardless of anything in `config.toml`. `self.options` (the
   dict pwnagotchi populates FROM config.toml) is never read anywhere
   in this file. There is no way to point this plugin at your actual
   home network through configuration as written.

3. **Even if (2) were fixed, the RSSI check can't pass.**
   `handle_wifi_update()` gates connection on
   `if signal_strength >= 60`. Real RSSI values from bettercap are
   negative dBm figures (e.g. -40 to -90) - a value of positive 60
   essentially never occurs, so this branch is dead in practice even
   with a matching SSID.

## What a real fix would actually require

This isn't "delete one bad import line" like the other two plugins in
this cluster. A working version would need:

- A real fake-AP implementation - either shelling out to `hostapd`
  with a generated config per fake ESSID, or building and
  periodically transmitting real 802.11 beacon frames via `scapy`
  (`sendp` on a monitor-mode interface) - genuine new functionality,
  not a bugfix.
- `self.home_network`/`self.home_password` rewired to actually read
  `self.options["home-network"]` / `self.options["home-password"]` -
  straightforward, but combined with everything else here, this is a
  rebuild, not a tweak.
- The RSSI comparison flipped to something like
  `signal_strength >= self.options.get("minimum-signal-strength", -75)`.
- At that point, the sensible path is arguably not "fix this file" but
  "run `educational-purposes-only.py` (or its upgraded version) for
  the auto-connect half, and treat honeypot detection as a separate,
  purpose-built plugin" - bolting two unrelated, both-broken features
  back together in one file isn't obviously worth doing versus
  keeping them apart, especially since a real honeypot implementation
  is a meaningfully different scope of work (transmitting fake beacon
  frames, deliberately deceptive, worth its own careful ethics/scope
  discussion) from "reconnect to my own wifi."

## If this ever gets revived

Treat it as "build a new honeypot-detection plugin" and "build a new
config-respecting auto-connect plugin" as two separate proposals
rather than reviving this file directly - the combination doesn't buy
anything given both halves need a from-scratch rebuild anyway.
