# Notes: cracking-pipeline "_ng" rewrites cluster

**Status: all 6 KEPT (`aircrackonly.py`, `aircrackonly_ng.py`,
`better_onlinehashcrack.py`, `onlinehashcrack_ng.py`,
`quick_rides_to_jail.py`, `quick_rides_to_jail_ng.py`). Findings-only.**

Sources: all six from `itsdarklikehell/pwnagotchi-plugins`. Each of the
three "_ng" files is itsdarklikehell's own rewrite of a plugin already on
the master list; diffed directly against its already-listed counterpart.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other 6 clusters this produced.

## 1. What each pair is and does

1. **`aircrackonly.py`** / **`aircrackonly_ng.py`** - on every captured
   handshake, runs `aircrack-ng` against the capture file to confirm it
   actually contains a usable handshake or PMKID; deletes the file if
   not.
2. **`better_onlinehashcrack.py`** / **`onlinehashcrack_ng.py`** -
   uploads handshakes to onlinehashcrack.com and later downloads/saves
   cracked results from the site.
3. **`quick_rides_to_jail.py`** / **`quick_rides_to_jail_ng.py`** -
   dictionary-cracks handshakes with `aircrack-ng`, then writes any
   cracked password into `wpa_supplicant.conf`.

## 2. `aircrackonly.py` / `aircrackonly_ng.py` - clean improvement, no new bugs

Diffed directly. `aircrackonly_ng.py` adds one real change: a new
`on_ui_update` hook that shows an on-screen status message ("Removed an
uncrackable pcap") when it deletes a pcap - the original does the
deletion silently, with no on-screen feedback. Everything else is
formatting/style cleanup (f-strings, `__defaults__`/`__dependencies__`
metadata blocks - the latter irrelevant per the project-wide `__defaults__`
correction) plus a defensive `self.options["face"]` fallback the original
lacks.

Both trigger on the real `on_handshake` event and operate directly on
the `filename` the framework passes in - neither does a directory scan
with a `.pcap`-only extension filter, so neither is affected by the
`.pcap`-vs-`.pcapng` bug pattern found repeatedly elsewhere in this
project (Clusters 5/6). `aircrackonly_ng.py` is a strict functional
superset of `aircrackonly.py`.

**Fix:** none needed - both work as shipped.

## 3. `better_onlinehashcrack.py` / `onlinehashcrack_ng.py` - share one known bug, differ in two other ways

**Shared bug (already documented for `better_onlinehashcrack.py` in
Cluster 6):** the startup backlog scan filters `if filename.endswith(".pcap")`,
which never matches this image's `.pcapng` captures - only the live
per-handshake upload path (triggered directly off the real event, same
as `aircrackonly.py` above) actually works; anything captured before the
plugin was enabled, or missed while offline, is never picked up by the
backlog scan. `onlinehashcrack_ng.py` inherits this identically.

**Difference 1 - download endpoint.**
```python
# better_onlinehashcrack.py
result = s.get("https://www.onlinehashcrack.com/exportcsv", timeout=timeout)

# onlinehashcrack_ng.py
result = s.get("https://www.onlinehashcrack.com/wpa-exportcsv", timeout=timeout)
```
If onlinehashcrack.com renamed this endpoint at some point,
`better_onlinehashcrack.py`'s download step could be silently failing
today - not confirmed without hitting the live site (out of scope for
static source review), flagged rather than asserted as a bug.

**Difference 2 - whitelist source.**
```python
# better_onlinehashcrack.py
if "whitelist" not in self.options:
    self.options["whitelist"] = list()
...
handshake_paths, self.options["whitelist"]

# onlinehashcrack_ng.py
config = agent.config()
...
handshake_paths, config["main"]["whitelist"]
```
`config['main']['whitelist']` is confirmed a real, core config key on
this fork (present in `pwnagotchi/defaults.toml`) - the device's actual
whitelist, the same one the framework and other plugins already respect.
`onlinehashcrack_ng.py` uses that automatically; `better_onlinehashcrack.py`
requires a separate, easy-to-forget plugin-scoped whitelist copy that
starts empty if never explicitly set.

**Fix, if ever prioritized:** apply the shared `.pcap`→`.pcapng`-aware
backlog-scan fix documented in Cluster 6 to both files; consider
migrating `better_onlinehashcrack.py` to read `config['main']['whitelist']`
the way `onlinehashcrack_ng.py` does, and verify onlinehashcrack.com's
current export endpoint name directly against the live site before
relying on either file's download step.

## 4. `quick_rides_to_jail.py` / `quick_rides_to_jail_ng.py` - major finding: neither form is functional

**Bug 1 (original only) - never registers as a plugin at all.** Reading
`quick_rides_to_jail.py` in full: every hook (`__init__`, `on_loaded`,
`on_ready`, `on_handshake`, `on_ui_update`, plus all the `_do_crack`/
wpa_supplicant helper functions) is defined as a bare **module-level
function** - there is no `class X(plugins.Plugin):` anywhere in the
file. Confirmed against this fork's own plugin loader source
(`pwnagotchi/plugins/__init__.py`) that plugin registration happens
exclusively through:

```python
class Plugin:
    @classmethod
    def __init_subclass__(cls, **kwargs):
        ...
        loaded[plugin_name] = plugin_instance
```

- i.e. only a real subclass of `Plugin` ever gets added to the `loaded`
dict the framework dispatches events through. With no subclass present,
`load_from_file()` execs the module without error (nothing in the file
itself is invalid Python), logs nothing, and the plugin simply never
registers - every hook in the file is permanently dead code. Not a crash,
not a log entry, just silent total non-function - the same failure
category as `bluetooth_scanner.py` (Cluster 18)'s `ImportError`, but even
quieter, since this one doesn't even fail loudly.

**Fix (this part):** wrap the existing functions in a proper
`class QuickRidesToJail(plugins.Plugin):` and change each function
signature to a method (`self` as first parameter) - exactly what
`quick_rides_to_jail_ng.py` already does.

**Bug 2 (both files, independent of Bug 1) - `OPTIONS` is declared but
never populated.** Both files have, at module level:

```python
OPTIONS = dict()
```

and every real code path indexes into it directly - `OPTIONS["wordlist_folder"]`,
`OPTIONS["interface"]`, `OPTIONS["net_device_path"]`,
`OPTIONS["wpa_supplicant_conf_path"]` - inside `_do_crack`,
`_reconfigure_wpa_supplicant`, `_get_network_interfaces`,
`_device_in_monitor_mode`, `_get_pwnd_networks`, and
`_add_pwnd_networks_to_wpa_supplicant`. Searched both files for any
assignment to `OPTIONS` beyond the initial empty-dict declaration -
there is none. `self.options` (the real, framework-populated instance
attribute both files' `class`/pseudo-class already has access to) is
never copied into this module-level `OPTIONS` global anywhere. The
result: `quick_rides_to_jail_ng.py` (which does fix Bug 1) registers
correctly, then raises `KeyError` on the very first line of the very
first helper method that runs.

**Fix (this part):**
```python
def on_loaded(self, ui):
    global READY, OPTIONS
    READY = True
    OPTIONS.update(self.options)   # FIX: actually populate OPTIONS from self.options
    logging.info(f"[{self.__class__.__name__}] plugin loaded")
```
(or equivalently, replace every `OPTIONS[...]` reference with
`self.options[...]` throughout and drop the module-level global
entirely - the more thorough fix, since it removes the extra layer of
indirection that caused this bug in the first place).

**Bottom line:** as shipped, `quick_rides_to_jail.py` does literally
nothing (never registers), and `quick_rides_to_jail_ng.py` registers but
crashes on first real use. Getting a working version requires applying
*both* fixes above to the `_ng` file - fixing only one leaves the plugin
still non-functional. Neither requires a redesign; both are small,
mechanical patches once combined.

**Master-list correction applied:** the existing bullet for
`quick_rides_to_jail.py` described it as working ("Dictionary-cracks
handshakes, then auto-updates wpa_supplicant with results") with no
caveat - corrected in place to note both bugs, consistent with how
`auto_backup_ng.py`'s description was corrected for accuracy in Cluster 15.

## 5. Dependencies (all kept plugins)

`aircrackonly.py`/`aircrackonly_ng.py`: `aircrack-ng` binary (apt),
`scapy` (pip, declared but unused - same boilerplate pattern seen
elsewhere). `better_onlinehashcrack.py`/`onlinehashcrack_ng.py`:
`requests` (pip) or `scapy` (pip, unused boilerplate, depending on
variant) - both need outbound internet access to onlinehashcrack.com.
`quick_rides_to_jail.py`/`quick_rides_to_jail_ng.py`: `aircrack-ng`
binary (apt), a local wordlist folder (`/etc/pwnagotchi/wordlists/passwords`
by default), write access to `wpa_supplicant.conf`, and (once the
`OPTIONS` bug is fixed) a correctly-configured `interface` option
matching a real network device.
