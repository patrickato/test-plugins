# Notes: cloud-crack-upload destination cluster

**Status: all 8 KEPT on the master list.** 7 share one bug and one
shared fix; the 8th already works correctly.

## The shared bug (7 of 8 plugins)

`banthex.py`, `banthex-de.py`, `better_onlinehashcrack.py`,
`dropbox_ul.py`, `hashespwnagotchi.py`, `nextcloud.py`, and
`wpa-cracking-project-with-pwnagotchi` all trigger **exclusively**
from `on_internet_available`, and all filter the handshake directory
identically:

```python
handshake_paths = [os.path.join(handshake_dir, filename)
                    for filename in handshake_filenames
                    if filename.endswith('.pcap')]
```

This image only ever writes `.pcapng` files. Unlike Cluster 5 (where
this same bug only broke a secondary backlog-scan path while live
conversion still worked), here it's the plugin's *only* trigger -
these seven currently upload nothing, ever, on this image. They load
fine and run fine, they just never find a file to act on.

This isn't independent sloppiness across seven different authors -
`banthex.py`'s own header comment says outright "the plugin and the
banthex backend code clones of wpa-sec," and the code shape (identical
`StatusFile` usage, identical `remove_whitelisted` calls, identical
`on_internet_available` structure) confirms all seven descend from the
same original wpa-sec upload template, written before this fork
switched capture output to `.pcapng`.

## The fix (identical across all 7)

```python
# before
if filename.endswith('.pcap')

# after
if filename.endswith('.pcap') or filename.endswith('.pcapng')
```

One line, same change, same place, in each of the seven files. Low
risk, not urgent (nothing breaks further by leaving it as-is - they
just stay inert until touched), worth doing whenever any one of them
gets picked up for actual use.

## Extra flag: `hashespwnagotchi.py`'s whitelist protection is disabled

Every one of the other six plugins in this cluster calls
`remove_whitelisted(handshake_paths, self.options['whitelist'])`
before uploading - this excludes any AP you've listed in
`main.whitelist`/the plugin's own `whitelist` option from ever being
uploaded. `hashespwnagotchi.py` has this exact same line present in
its source, but **commented out**:

```python
# handshake_paths = remove_whitelisted(handshake_paths, self.options['whitelist'])
```

This means if the `.pcap`/`.pcapng` bug above is ever fixed on this
one plugin without also uncommenting this line, it would upload
*every* captured handshake with no whitelist exclusion at all - a
real scope difference from its six siblings, not just a missing
nice-to-have. **If `hashespwnagotchi.py` specifically is ever fixed,
uncomment this line in the same change**, or the fix would create a
genuine behavior gap versus the rest of this cluster.

## `pwn2crack.py` (Brets0150, aka pwnagotchi-to-hashtopolis-plugin) - already works, no fix needed

Architecturally different from the other seven, and it dodges the bug
entirely:

- `on_handshake` (a live hook, given the real filename directly - no
  extension assumption) runs `hcxpcapngtool` itself to confirm a valid
  handshake and produce a `.22000` hash file.
- `on_internet_available` then uploads files ending in `.22000` - the
  format it just created, so the raw-capture extension (`.pcap` vs
  `.pcapng`) never enters the picture.
- It also deletes the raw capture file if `hcxpcapngtool` determines
  it's not a valid handshake/PMKID - similar cleanup behavior to
  `hashieclean.py` from Cluster 5, worth knowing if you don't want
  incomplete captures auto-deleted.

No fix needed here - already functions correctly on this image as
shipped.

## Required tools / dependencies (all 8)

`requests` (pip) for the six HTTP-upload plugins; `pwn2crack.py`
additionally needs `hcxpcapngtool` (from `hcxtools`, same as Cluster
5) since it does its own conversion rather than uploading raw pcaps.
`wpa-cracking-project-with-pwnagotchi` is the one destination that
isn't a public third-party service - it uploads to a self-hosted
backend (Docker Compose stack included in that project's own repo:
`src/frontend` + `src/backend`), so using it means standing up that
backend yourself somewhere reachable from the pwnagotchi, not just
pointing at a public URL like the others.
