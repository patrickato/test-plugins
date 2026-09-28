# Notes: pcap→hash conversion cluster (`hashie-hcxpcapngtool.py`,
# `hashieclean.py`, `hashie_ng.py`)

**Status: all 3 KEPT on the master list. One shared bug documented
here rather than three separate proposal docs, since all three share
the exact same fix.**

## The shared bug

All three plugins have two independent code paths:

1. **`on_handshake`** - fires live, right after each new capture.
   Passes whatever filename the hook actually hands it straight to
   `hcxpcapngtool`. This works correctly on this image - `hcxpcapngtool`
   is pcapng-native and the plugin doesn't filter by extension here,
   it just uses the real path it was given. **No fix needed on this
   path for any of the three.**

2. **`_process_stale_pcaps`** - a startup/interval batch job that
   scans the handshake directory for anything not yet converted, to
   catch up on a backlog. All three filter with:
   ```python
   handshakes_list = [os.path.join(handshake_dir, filename)
                       for filename in os.listdir(handshake_dir)
                       if filename.endswith('.pcap')]
   ```
   This image only ever writes `.pcapng` files. That filter will
   never match anything here, so the batch/catch-up path silently
   finds zero files on every run, on all three plugins.

Notably, `hashie_ng.py` - co-authored by jayofelony, the fork
maintainer, and presumably the version most likely to have been
checked against this exact image - has the identical bug. That's a
useful signal: this isn't one author being careless, it's a bug that
predates the fork's switch to `.pcapng` output and nobody's gone back
to fix the backlog-scan filter in any variant that inherited this
lineage.

## Why this wasn't treated as a removal-worthy break

Unlike the fully-broken `hashie.py` (already removed - its LIVE path
had this same filter, so it converted nothing, ever), here the live
path is unaffected. The backlog scan only matters if you're catching
up on old capture files that predate the plugin being loaded, or
migrating `.pcap` files in from an older setup. For normal day-to-day
operation (plugin loaded, then captures handshakes as it goes), all
three work as intended.

## The fix, if/when applied to any of the three

One-line change per file, same fix in each:

```python
# before
if filename.endswith('.pcap')

# after
if filename.endswith('.pcap') or filename.endswith('.pcapng')
```

Straightforward, low-risk, and identical across all three files. Not
urgent given the live path already works - worth doing whenever one
of these three gets touched for another reason anyway, rather than as
its own priority task.

## Per-plugin notes

- **`hashie-hcxpcapngtool.py`** - otherwise clean. No other issues
  found.
- **`hashieclean.py`** - additionally deletes "lonely" pcaps (files
  that couldn't be converted to either `.22000` or `.16800`) inside
  the same broken batch function, after logging their GPS data for
  webgpsmap. Currently unreachable on this image for the same reason
  as the batch scan itself - worth knowing this delete behavior would
  start functioning the moment the one-line fix above is applied, so
  if that fix is ever made, decide deliberately whether you want
  unconvertible pcaps auto-deleted or not (this is a real behavior
  change, not just a bugfix, once the filter is corrected).
- **`hashie_ng.py`** - functionally near-identical to
  `hashie-hcxpcapngtool.py` (no delete-lonely-pcaps behavior), triggers
  its batch job via `on_ready` instead of `on_config_changed`. Worth
  knowing this one exists and is co-authored by the fork maintainer -
  possibly the "closest to canonical" choice of the three if you ever
  want to pick just one.

## Required tools / dependencies

Same across all three: `hcxpcapngtool` (from `hcxtools`, built from
source per the in-file install instructions -
`git clone https://github.com/ZerBea/hcxtools.git`, standard apt build
deps `libcurl4-openssl-dev libssl-dev zlib1g-dev`, `make && sudo make install`),
plus `tcpdump` (used in the PMKID-repair fallback path in
`hashie-hcxpcapngtool.py`/`hashieclean.py`, not in `hashie_ng.py`,
which drops the tcpdump-based repair fallback entirely - one more
small difference between it and the other two). `scapy` listed as a
pip dependency in all three but not actually imported/used anywhere in
any of the three files - a dead dependency declaration in all of them.
