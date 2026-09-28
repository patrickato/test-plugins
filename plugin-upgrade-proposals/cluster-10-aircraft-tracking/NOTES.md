# Notes: aircraft-tracking plugin cluster

**Status: all 3 KEPT on the master list.** `skyhigh.py` is clean.
`adsbsniffer.py` and `pwnaware.py` both need real fixes to work as
shipped - documented below, not applied to the source. User owns
multiple RTL-SDR USB dongles, so the hardware-dependent pair
(`adsbsniffer.py`, `pwnaware.py`) is directly usable once fixed, not
theoretical.

These three are not duplicates of each other despite overlapping
purpose (nearby-aircraft display): `skyhigh.py` needs no RTL-SDR
hardware at all (internet-only, OpenSky API); `adsbsniffer.py` and
`pwnaware.py` both need an RTL-SDR dongle but via different toolchains
- `adsbsniffer.py` shells out to `rtl_adsb` directly and parses its
raw text output itself, `pwnaware.py` expects a separately-running
`dump1090-fa` daemon (its own apt package/service, not something
either plugin installs) and reads its JSON output file. Not
interchangeable - picking one over the other is a software-stack
choice, not a duplicate-removal choice.

## `skyhigh.py` (AlienMajik, v2.2.0) - clean, no hardware needed

Pulls live aircraft state vectors from the OpenSky Network's public
API (`https://opensky-network.org/api/states/all`), shows an
on-screen count, and serves a live map/flight-strip board via
`on_webhook`. No RTL-SDR dependency, no handshake-filename dependency
- entirely internet/API driven. Same author and code-quality bar as
`snoopr.py`/`theylive.py` (Cluster 9) - well-structured, actively
versioned. No bugs found. Needs `requests` (pip) and internet access;
optionally an OpenSky account for higher API rate limits (works
anonymously too, just more rate-limited).

## `adsbsniffer.py` (AlienMajik, earlier/simpler plugin) - likely broken on load

Requires an RTL-SDR dongle and the `rtl_adsb` binary (from the
`rtl-sdr` apt package). Runs `timeout 10s rtl_adsb` as a subprocess on
a timer and parses hex/signal-strength pairs from its output.

**Bug:** option defaults are set as an **instance** dict inside
`__init__`:

```python
def __init__(self):
    self.options = {
        'timer': 60,
        'aircraft_file': '/root/handshakes/adsb_aircraft.json',
        'adsb_x_coord': 160,
        'adsb_y_coord': 80
    }
```

pwnagotchi's plugin loader assigns `self.options` from
`config['main']['plugins'][name]` (the user's `config.toml` section
for this plugin, or `{}` if none exists) **after** `__init__()` runs -
overwriting whatever was set here entirely. `on_loaded()` immediately
does `self.options['aircraft_file']` - which would `KeyError` unless
every one of those four keys is explicitly set in config.

**CORRECTED FIX (see Cluster 18's project-wide `__defaults__`
correction):** this NOTES.md originally recommended moving these
defaults into a class-level `__defaults__` attribute. That
recommendation was wrong for this fork - I later confirmed by reading
this jayofelony fork's actual plugin loader
(`pwnagotchi/plugins/__init__.py`) that it **never reads
`__defaults__` at all**, on any plugin, regardless of whether it's
declared. Adding `__defaults__` here would not have fixed anything.
The two fixes that actually work on this fork:

```python
# Option A - configure every key explicitly in config.toml (no code change):
[main.plugins.adsbsniffer]
enabled = true
timer = 60
aircraft_file = "/root/handshakes/adsb_aircraft.json"
adsb_x_coord = 160
adsb_y_coord = 80
```

```python
# Option B - patch the plugin to fall back with .get() instead of
# indexing self.options directly, so it works even with a bare
# `enabled = true` in config.toml:
def on_loaded(self):
    self.timer = self.options.get('timer', 60)
    self.aircraft_file = self.options.get('aircraft_file', '/root/handshakes/adsb_aircraft.json')
    self.adsb_x_coord = self.options.get('adsb_x_coord', 160)
    self.adsb_y_coord = self.options.get('adsb_y_coord', 80)
```

Neither applied to the source. Otherwise straightforward once fixed -
it's a simple polling loop around a subprocess call, nothing
structurally wrong beyond this.

## `pwnaware.py` (evilsocket-derived, edited by itsdarklikehell) - broken (fatal) + smaller bugs

Requires an RTL-SDR dongle plus a separately-running `dump1090-fa`
daemon (own apt package/systemd service) writing
`/var/run/dump1090-fa/aircraft.json` - neither plugin installs or
starts that daemon itself, it has to be set up independently.

**Fatal bug in `on_loaded()`:**

```python
def on_loaded(self):
    logging.info(f"[{self.__class__.__name__}] plugin loaded")
    logging.warn(f"[{self.__class__.__name__}] options = " % self.options)
    if not "numPlanes" in self.options:
        self.options["numPlanes"] = 4
```

The second line mixes an f-string (already fully interpolated, a
plain `str` with no `%`-format placeholders) with the `%` operator
against `self.options` (a dict). `"some plain string" % {...}` with
no `%(name)s`-style placeholders in the string raises `TypeError: not
all arguments converted during string formatting` - immediately, on
every load. Since this happens on the line **before** the
`numPlanes` default gets set, `self.options["numPlanes"]` is never
populated, and every later hook that reads it
(`on_ui_setup`, `on_ui_update`, `on_unload`) will `KeyError`.

**Fix:**

```python
# before
logging.warn(f"[{self.__class__.__name__}] options = " % self.options)

# after
logging.warning(f"[{self.__class__.__name__}] options = {self.options}")
```

(also fixes the deprecated `logging.warn` → `logging.warning` while
touching this line.)

**Secondary bug in `update_scoreboard()`** - a watch-list lookup uses
the bare Python builtin `hex` instead of the string `"hex"` as a dict
key:

```python
# before
elif ("*" + p["hex"]) in self.watch_planes:
    watch = self.watch_planes["*" + p[hex]]

# after
elif ("*" + p["hex"]) in self.watch_planes:
    watch = self.watch_planes["*" + p["hex"]]
```

This raises a `KeyError` (`hex` the builtin function object isn't a
valid dict key match) whenever that specific branch is reached -
i.e. when a tracked plane shows up under its hex ID rather than a
named flight.

**Tertiary bug, same function's exception handler** - references an
undefined variable `err` instead of the caught exception `e`:

```python
# before
except Exception as e:
    logging.error(
        f"[{self.__class__.__name__}] update scoreboard: %s" % repr(err)
    )

# after
except Exception as e:
    logging.error(
        f"[{self.__class__.__name__}] update scoreboard: %s" % repr(e)
    )
```

Because the exception handler itself references an undefined name,
this raises a **new** `NameError` instead of logging the original
error - meaning whatever originally went wrong there (like the `hex`
bug above) propagates out of `update_scoreboard()` uncaught, into
whichever hook called it (`on_internet_available`, `on_ready`,
`on_wait`, `on_sleep`, `on_epoch` - all called frequently). Same
pattern (`r` instead of `e`) also appears in `on_webhook()`'s
exception handler - lower impact since it only affects the error
page shown for a webhook failure, not a core hook.

**Net effect:** as shipped, `pwnaware.py` cannot get past `on_loaded()`
without the fatal fix above; even after that fix, the `hex`/`err`
bugs would surface as soon as a tracked plane is seen by hex ID
rather than callsign. All three are one-line fixes, not a redesign.

## Dependencies

`adsbsniffer.py`: `rtl-sdr` (apt, for `rtl_adsb`). `pwnaware.py`:
`geopy` (pip, already declared), `dump1090-fa` (apt/separate service,
not declared in `__dependencies__` at all - a real gap, since without
it the plugin has no data source). `skyhigh.py`: `requests` (pip).
