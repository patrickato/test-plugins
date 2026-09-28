# Notes: Bluetooth tethering cluster

**Status: `bt-tether_ng.py` REMOVED (exact duplicate). `bt-tether.py` KEPT.**

Sources: both from `itsdarklikehell/pwnagotchi-plugins`.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced.

## 1. What it is and does

**`bt-tether.py`** / **`bt-tether_ng.py`** - a substantial (716-line),
well-built plugin that pairs with a phone over Bluetooth (NAP/PAN
networking), brings up a network interface to it, and makes the
pwnagotchi's web UI reachable through that connection - useful when
there's no other network path to it. Supports multiple named devices
(e.g. separate Android/iOS profiles) with per-device priority, retry
limits, and internet-sharing options, plus a legacy single-device config
format for backward compatibility.

## 2. Exact duplicate, confirmed via diff

```
$ diff bt-tether.py bt-tether_ng.py
469c469
< class BTTether(plugins.Plugin):
---
> class BTTether_ng(plugins.Plugin):
475c475
<     __name__ = "BTTether"
---
>     __name__ = "BTTether_ng"
```

That's the entire difference across 716 lines - a renamed class and
`__name__` attribute, nothing else. Same exact-duplicate-mirror pattern
found repeatedly in this project (`exp.py`/`Experience-Plugin-Pwnagotchi`
in Cluster 16, the Discord/Telegram groups in Group 2) - one file's
worth of real code shipped under two names. Installing both would be
redundant, not complementary.

**Decision:** kept `bt-tether.py` (the plain name) over `bt-tether_ng.py`.
No functional reason to prefer either - unlike every other `_ng`-suffixed
plugin reviewed in this project (which turned out to be worse rewrites:
`led-ng.py`, `wardriver_ng.py`, `webgpsmap_ng.py`), this one is a pure
rename with zero code difference, so the `_ng` suffix carries no signal
either way here. The plain name was chosen for config-key simplicity
(`[main.plugins.bt-tether]`) and to avoid future confusion with an
actually-different "next-gen" plugin, given how many genuinely-different
`_ng` files this audit turned up elsewhere.

## 3. Quality assessment - one of the more carefully built plugins found in this audit

`on_loaded` validates that every required option (`mac`, `ip`, `netmask`,
`interval`, etc.) is actually present for each enabled device, and logs
a clear error naming exactly what's missing, rather than letting a bare
`self.options[...]` indexing crash with `KeyError`:

```python
for device_opt in ["enabled", "priority", "scantime", "search_order",
                    "max_tries", "share_internet", "mac", "ip",
                    "netmask", "interval"]:
    if device_opt not in options or options[device_opt] is None:
        logging.error(
            "BT-TETHER: Please specify the %s for device %s.",
            device_opt, device,
        )
        break
else:
    if options["enabled"]:
        self.devices[device] = Device(name=device, **options)
```

Genuinely defensive design, independent of whether `__defaults__` works
on this fork (it declares one, but per the project-wide correction it's
never read - this plugin doesn't depend on it working, since `on_loaded`
checks explicitly instead). No functional bugs found anywhere in the
file.

**Cosmetic-only issue, not fixed:** `__help__` is copy-pasted from an
unrelated plugin:
```python
__description__ = "This makes the display reachable over bluetooth"   # correct
__help__ = "This plugin automatically uploads collected WiFi to wigle.net"   # wrong - copy-paste artifact
```
Doesn't affect function, only the text shown in the web UI's plugin-info
listing.

**Fix, if ever prioritized:**
```python
__help__ = "This makes the display reachable over bluetooth"
```
One-line fix, not applied this round.

## 4. Dependencies (kept plugin)

`dbus` (pip, for the Bluetooth NAP/PAN D-Bus interface), `scapy` (pip,
declared but unused - same boilerplate pattern seen elsewhere in this
project), a running `bluetooth.service` (the plugin checks for and
attempts to start it if not active), and a phone already paired over
Bluetooth with NAP/PAN tethering enabled on its end.
