# Notes: misc grab-bag cluster

**Status: all 6 KEPT for now (`wigle_ng.py`, `wpa-sec-list.py`,
`wpa-sec_ng.py`, `auto-update_ng.py`, `prime_gsm_hat.py`, `auto_tune.py`).
Findings-only.**

Sources: `wigle_ng.py`, `wpa-sec-list.py`, `wpa-sec_ng.py`,
`auto-update_ng.py`, `prime_gsm_hat.py` from
`itsdarklikehell/pwnagotchi-plugins`; `auto_tune.py` from
`sniffleupagus/pwnagotchi_plugins`.

This is the last of 7 clusters spun out of a project-wide audit that found
42 plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced. Unlike most other clusters, this one is
a genuine grab-bag - the 6 plugins here don't share a common lineage or
theme; each was reviewed independently.

## 1. What each one is and does

1. **`wigle_ng.py`** - automatically uploads collected WiFi network data
   (SSIDs/BSSIDs plus GPS coordinates, parsed from handshake filenames) to
   wigle.net.
2. **`wpa-sec-list.py`** - reads the local WPA-SEC potfile and displays a
   list of cracked passwords on a web page.
3. **`wpa-sec_ng.py`** - despite the similar name and its neighboring spot
   on the master list, this is a completely different plugin: it
   automatically uploads handshakes to https://wpa-sec.stanev.org (an
   upload/download tool, not a display page).
4. **`auto-update_ng.py`** - checks for and applies pwnagotchi/plugin
   updates when internet is available.
5. **`prime_gsm_hat.py`** - intended to feed bettercap fake GPS
   coordinates from a GSM hat's fake serial device, as a companion
   approach to `gsmfake.py`.
6. **`auto_tune.py`** - adjusts AUTO mode parameters (attack timing/
   aggressiveness tuning) based on observed conditions.

## 2. `wigle_ng.py` - the recurring `.pcap`-vs-`.pcapng` bug, in the upload path this time

```python
handshake_filename = os.path.basename(handshake_path)
if handshake_filename.endswith(".pcap"):
    gps_filename = handshake_filename.replace(".pcap", ".gps.json")
```
This fork writes `.pcapng` files exclusively (confirmed project-wide,
multiple prior clusters). Since every real capture's filename ends in
`.pcapng`, not `.pcap`, the `.endswith(".pcap")` check is always `False`
for genuine captures here - the GPS-filename lookup never runs, so no
handshake ever gets a matching GPS file attached, and the upload logic
built around that pairing silently never fires for this device's actual
files. Same bug family previously found in `webgpsmap_ng.py` (Cluster 21)
and, in a backlog-scan variant, the Cluster 6 wpa-sec family - now
confirmed a third time, in a third independent codepath.

**Fix:**
```python
if handshake_filename.endswith(".pcapng"):
    gps_filename = handshake_filename.replace(".pcapng", ".gps.json")
```

## 3. `wpa-sec-list.py` - `IndexError` risk on a malformed potfile line

```python
for line in potfile_lines:
    parts = line.strip().split(":")
    password = parts[-1]
    bssid = parts[0]
    ...
```
The WPA-SEC potfile format is normally colon-delimited with a predictable
number of fields, but this code makes no length check before indexing.
Any line that doesn't split into the expected shape (a blank line, a
partial/corrupted write mid-crack, a format change) raises `IndexError`
on `parts[0]` or `parts[-1]` - and since this is all inside the single
request-handling loop that builds the whole page, one bad line breaks the
entire display, not just that one entry.

**Fix:**
```python
for line in potfile_lines:
    parts = line.strip().split(":")
    if len(parts) < 2:
        continue
    password = parts[-1]
    bssid = parts[0]
```

## 4. `wpa-sec_ng.py` - misdescribed on the master list, and shares the Cluster 6 backlog-scan bug

The master list previously grouped this with `wpa-sec-list.py` under one
shared, inaccurate description ("Lists cracked passwords from wpa-sec on
a web page"). Its own `__description__` says otherwise:
```python
__description__ = "This plugin automatically uploads handshakes to https://wpa-sec.stanev.org"
```
Confirmed by reading the actual logic - this plugin has no web-page/
display code at all; it's purely an upload/download tool for the
wpa-sec.stanev.org cracking service. The master list bullet has been
split into two independent entries as part of this cluster's review.

Functionally, it shares the same `.pcap`-vs-`.pcapng` backlog-scan bug
already documented for the Cluster 6 wpa-sec plugin family - handshakes
already on disk before the plugin was installed are never picked up for
upload, since the backlog scan filters on the wrong extension. New
handshakes captured after install are still uploaded correctly via the
`on_handshake` event hook, which receives the live `.pcapng` filename
directly and doesn't depend on the broken filter.

**Fix:** apply the same extension correction used for the Cluster 6
family - filter backlog scans on `.pcapng` instead of `.pcap`.

## 5. `auto-update_ng.py` - detect/notify works, but the actual install feature silently never runs

Four module-level functions all make the same mistake:
```python
def make_path_for(path):
    ...
    logging.info(f"[{self.__class__.__name__}] Creating path: {path}")
    ...

def download_and_unzip(url, path):
    ...
    logging.info(f"[{self.__class__.__name__}] Downloading update from {url}")
    ...

def verify(path):
    ...
    logging.info(f"[{self.__class__.__name__}] Verifying: {path}")
    ...

def install(path):
    ...
    logging.info(f"[{self.__class__.__name__}] Installing update")
    ...
```
None of `make_path_for`, `download_and_unzip`, `verify`, or `install` are
defined as class methods - they're plain module-level functions - yet
every one of them references `self.__class__.__name__` in its logging.
`self` doesn't exist in that scope, so every single call to any of these
four functions raises `NameError` immediately.

This matches the same bug pattern found repeatedly elsewhere in this
project (`away_base.py`/`home_base.py`'s shared `_log()` in Cluster 19) -
a method clearly written first as part of a class, then extracted to
module level (or copy-pasted from a class-based file) without updating
the self-reference.

The practical effect: the plugin's periodic check-for-updates logic
(which doesn't call any of these four functions) runs fine and correctly
logs/notifies when an update is available. But the moment a user actually
triggers the install path, it calls into one of these four broken
functions, hits `NameError`, and the calling method's own try/except
silently swallows it - the auto-install feature is completely non-functional,
while the plugin otherwise looks like it's working (loads cleanly, no
startup errors, notifications still appear).

**Fix:**
```python
def make_path_for(path):
    logging.info(f"Creating path: {path}")
    ...

def download_and_unzip(url, path):
    logging.info(f"Downloading update from {url}")
    ...

def verify(path):
    logging.info(f"Verifying: {path}")
    ...

def install(path):
    logging.info(f"Installing update")
    ...
```
(Or, if the class-scoped log tag is wanted, pass a class-name string in
as a parameter instead of referencing a nonexistent `self`.)

## 6. `prime_gsm_hat.py` - not actually a pwnagotchi plugin at all

Confirmed via a full read of the file: there is no `class X(plugins.Plugin):`
definition anywhere in it. Per this fork's own plugin-loader source
(`Plugin.__init_subclass__` in `pwnagotchi/plugins/__init__.py`), a
plugin only registers with the framework - and only then does any of its
code ever run - when a real subclass of `plugins.Plugin` is defined in
the module. A file with no such class imports without error but silently
never registers: nothing in it ever executes, and no error is logged
anywhere. This is the exact same pattern that debunked
`quick_rides_to_jail.py` in Cluster 20.

Beyond just missing a class wrapper, this file is actually a standalone
manual setup script from the Python 2 era:
```python
device = raw_input("Enter the GSM hat's serial device path: ")
```
`raw_input()` was renamed to `input()` in Python 3 and no longer exists -
even if someone manually extracted this code and ran it standalone
outside the plugin system (its apparent original intent, going by the
interactive prompts), it would crash immediately with `NameError` on the
first prompt, on any Python 3 interpreter, which is all this fork runs.

**Not fixable as a plugin without a substantial rewrite** - it would need
a real `plugins.Plugin` subclass built around the interactive setup logic
(converting the one-time interactive prompts into `__defaults__`/config
options, since a real plugin's `on_loaded` can't block on interactive
`input()` the way this manual script does), plus the `raw_input()` →
`input()` port. Kept on the list for now per the broad-scope philosophy,
but this is closer to a documentation snippet than a working plugin as
shipped.

## 7. `auto_tune.py` - no bugs found

Sampled extensively across its 692 lines (parameter-tuning logic,
config-option handling, event hooks) - no crash bugs, no dead imports, no
`self`-in-module-function mistakes, no stale API calls found. The most
thoroughly clean file reviewed in this discovery-audit thread.

## 8. Dependencies (kept plugins)

`wigle_ng.py`: `requests` (pip, for the wigle.net upload API), a WiGLE
API account/token (user-configured). `wpa-sec-list.py`: no special
dependencies, reads the local potfile directly. `wpa-sec_ng.py`:
`requests` (pip), a wpa-sec.stanev.org API key (user-configured).
`auto-update_ng.py`: standard library only (`zipfile`, `urllib`/`requests`
depending on version) - no non-stdlib dependencies beyond what pwnagotchi
already ships with. `prime_gsm_hat.py`: none identified (standalone
script, not integrated with the plugin dependency system at all).
`auto_tune.py`: no special dependencies beyond the standard library and
pwnagotchi's own bettercap/AUTO-mode internals.
