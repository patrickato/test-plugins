# Notes: fake-AP plugin cluster

**Status: `apfaker.py` REMOVED (exact duplicate). `better_apfaker.py`
KEPT.**

## What it is

Crafts fake 802.11 beacon frames with `scapy` (random spoofed source
MACs, a configurable SSID list, optional WPA2-"privacy" flag on the
beacon) and continuously transmits them over the wifi interface with
`sendp()`. A "fake AP flood" - clutters nearby WiFi scanners/wardriving
tools with decoy networks that don't really exist.

## `apfaker.py` - removed, exact duplicate

Diffed line-for-line against `better_apfaker.py` (same author,
itsdarklikehell/dadav). The only differences:

- Class `__name__`: `"APFaker"` vs `"Better_APFaker"`.
- `better_apfaker.py` adds one extra `__defaults__` key,
  `"path": "/home/pi/apfaker/"` - never referenced anywhere in either
  file's actual code. Dead/unused config.
- Minor cosmetic reordering (one log line moved, a blank line).

No functional difference whatsoever - "better" is a misnomer, not an
actual improvement. Removed as a straightforward exact-duplicate,
same category as the Discord/Telegram dupes resolved earlier in this
project.

## `better_apfaker.py` - kept, but has a real architecture concern

**Issue:** `on_ready()` ends in an unbounded loop that runs directly
in the hook body, not in a spawned thread:

```python
def on_ready(self, agent):
    ...
    main_config = agent.config()
    logging.info(f"[{self.__class__.__name__}] plugin ready")

    while not self.shutdown:
        sendp(frames, iface=main_config["main"]["iface"], verbose=False)
        sleep(max(0.1, len(frames) / 100))
```

`on_ready()` is a synchronous startup hook - pwnagotchi's main agent
loop calls it once during startup and expects it to return so the
agent can proceed into its normal recon/attack cycle. Without a
thread wrapping this loop, `on_ready()` never returns while the
plugin is enabled and running, which would very likely block the
entire pwnagotchi main loop for as long as this plugin stays active -
the only way out is `on_before_shutdown()` setting `self.shutdown =
True`, which itself only fires during actual agent shutdown. This is
the same underlying problem class as `pwnassistant.py`'s hang from
Cluster 13 (a blocking loop where the framework expects control back)
- the difference is this one is a deliberate design choice by the
author rather than an accident, and (caveat) this assessment is based
on how pwnagotchi's `on_ready` hook is documented/used across every
other plugin reviewed in this project, not on having read the core
agent-loop source directly in this session.

**Fix:** move the transmit loop into a background thread, same
pattern already used elsewhere in this project (`dashboard.py`'s
Pivoyager status thread, `speak_to_me.py`'s worker thread):

```python
from threading import Thread

def on_ready(self, agent):
    if not self.ready:
        return
    shuffle(self.ssids)
    cnt = 0
    base_list = self.ssids.copy()
    while len(self.ssids) <= self.options["max"] and self.options["repeat"]:
        self.ssids.extend([f"{ssid}_{cnt}" for ssid in base_list])
        cnt += 1
    frames = list()
    for idx, ssid in enumerate(self.ssids[: self.options["max"]]):
        try:
            logging.info(f'[{self.__class__.__name__}] creating fake ap with ssid "%s"', ssid)
            frames.append(APFaker.create_beacon(ssid, password_protected=self.options["password_protected"]))
            agent.view().set("apfake", str(idx + 1))
        except Exception as ex:
            logging.debug(f"[{self.__class__.__name__}] %s", ex)

    main_config = agent.config()
    logging.info(f"[{self.__class__.__name__}] plugin ready")

    def _transmit_loop():
        while not self.shutdown:
            sendp(frames, iface=main_config["main"]["iface"], verbose=False)
            sleep(max(0.1, len(frames) / 100))

    Thread(target=_transmit_loop, name="APFakerTransmit", daemon=True).start()
```

Not applied yet, documented for whenever this plugin is actually
enabled.

## Dependencies

`scapy` (pip, already declared) for crafting/sending raw 802.11
frames. Needs a wifi interface capable of packet injection in monitor
mode - the same requirement bettercap itself already has, so no
additional hardware capability needed beyond what pwnagotchi already
relies on.
