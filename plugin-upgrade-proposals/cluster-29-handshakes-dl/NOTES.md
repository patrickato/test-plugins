# Notes: handshake download web-UI cluster

**Status: `handshakes-dl.py` REMOVED (redundant subset). `handshakes-dl-hashie.py`
marked IN PROGRESS, moved to `plugins-wip` for a full rebuild.**

Sources: both from `itsdarklikehell/pwnagotchi-plugins`; `handshakes-dl.py`
cross-checked against jayofelony's own copy in
`jayofelony/pwnagotchi-torch-plugins`.

## 1. What each one is and does

1. **`handshakes-dl.py`** - adds a page to the pwnagotchi's web UI listing
   every captured handshake file with a search box, and a click-to-
   download link for each one.
2. **`handshakes-dl-hashie.py`** - the same download page, but for each
   capture it also checks whether a converted hash file already exists
   next to it (`.2500`, `.16800`, or `.22000`) and adds a separate
   download link for each format found.

Same original author (`me@sayakb.com`), near-identical code skeleton -
`handshakes-dl-hashie.py` is a strict superset of `handshakes-dl.py`'s
feature set, not a parallel alternative.

## 2. The shared bug - `.pcap`-only, three places at once

Both files make the same assumption in three separate spots:
```python
handshakes = glob.glob(os.path.join(self.config['bettercap']['handshakes'], "*.pcap"))
handshakes = [os.path.basename(path)[:-5] for path in handshakes]   # [:-5] = strips ".pcap"
...
send_from_directory(dir, path + '.pcap', as_attachment=True)        # hardcoded .pcap
```
This fork only ever writes `.pcapng` files. All three effects compound:
- The glob never matches anything, so the page always shows an empty list.
- Even if the glob were fixed, `[:-5]` strips the wrong number of
  characters for `.pcapng` (7 chars, not 5) - display names would come
  out with `ng` left on the end.
- Even if both of those were fixed, the download handler still
  hardcodes `.pcap` when looking the file up on disk - it would request
  a file that doesn't exist.

**Confirmed this isn't just a mirror-specific mistake:** jayofelony's own
official plugin repo (`jayofelony/pwnagotchi-torch-plugins`, one of the
`custom_plugin_repos` listed in this fork's own `defaults.toml`)
distributes `handshakes-dl.py` with this exact same bug, unpatched. This
is a real gap in an officially-distributed plugin, not just a
third-party mirror issue.

**Fix (documented for reference, applied properly in the `plugins-wip` rebuild):**
```python
handshakes = glob.glob(os.path.join(self.config['bettercap']['handshakes'], "*.pcapng"))
handshakes = [os.path.basename(p)[:-len(".pcapng")] for p in handshakes]
...
send_from_directory(dir, path + '.pcapng', as_attachment=True)
```

## 3. Decision

`handshakes-dl.py` removed - `handshakes-dl-hashie.py` does everything it
does plus more, so there's no scenario where keeping both adds value.
`handshakes-dl-hashie.py` moved to `plugins-wip` for a full rebuild
(fix the `.pcap` bug throughout, plus whatever improvements come out of
that design discussion) rather than a plain in-place fix here, per the
same workflow established for the DiscoHash Suite in Cluster 28.

## 4. Dependencies

Both: `scapy` (pip, declared but unused - same boilerplate pattern seen
throughout this project), Flask (already a core pwnagotchi dependency
for the web UI).
