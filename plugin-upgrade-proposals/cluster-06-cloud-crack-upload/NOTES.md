# Notes: cloud-crack-upload destination cluster

**Status (updated, Cluster 31): 3 of 8 REMOVED, 2 moved to `plugins-wip`
and fixed, 3 untouched.** Originally (Group 19) all 8 were kept pending a
shared one-line fix. Revisited in Cluster 31 with a closer per-plugin
pass, then both survivors were fully fixed and moved:

- **Removed**: `banthex.py` (redundant/more-buggy twin of `banthex-de.py`
  - see the file-deletion bug below), `dropbox_ul.py` (the shared `.pcap`
  bug plus an unvalidated required option that guarantees an uncaught
  `KeyError` on every upload if `path` isn't set), `nextcloud.py` (the
  shared `.pcap` bug plus a genuine crash bug - see below).
- **Moved to `plugins-wip`, fixed**: `banthex-de.py` (now `BanthexNG` in
  `plugins-wip:banthex-suite/`) - the `.pcap`/`.pcapng` bug and a
  permanent-skip-on-failure bug both fixed.
  `hashespwnagotchi.py` (now `HashesPwnagotchiNG` in
  `plugins-wip:hashespwnagotchi-suite/`) - the real security finding
  below fixed (every external command now runs via a real argument list,
  never a shell), plus a previously-unknown `on_config_changed` crash
  bug, the shared `.pcap` bug, a Python-2 `.encode("hex")` bug, the
  disabled whitelist, and the same permanent-skip-on-failure bug as
  `banthex-de.py`, all fixed. Full detail in each suite's own NOTES.md.
- **Untouched this pass**: `better_onlinehashcrack.py`,
  `wpa-cracking-project-with-pwnagotchi`, `pwn2crack.py` (already works,
  no fix needed - see below).

## Additional bugs found in Cluster 31 (beyond the shared `.pcap` issue)

- **`banthex.py`**: its `__init__` corrupted-state-file recovery has a
  copy/paste bug - if its own `/root/.banthex_uploads` state file is
  ever corrupt JSON, the except-handler deletes a *different* file
  (`/root/.wpa_sec_uploads`, another plugin's state file entirely) and
  then immediately tries to reopen the still-corrupt original file,
  which fails again, this time uncaught - the plugin fails to load at
  all. `banthex-de.py` (a separate contributor's fork of the same
  plugin) fixes this correctly - it deletes its own actual state file.
  This, on top of being otherwise identical code, is why `banthex.py`
  was removed as the redundant/worse of the two rather than fixed.
- **`dropbox_ul.py`**: `on_loaded()` validates the `app_token` option
  but not the `path` option, which `_upload_to_dropbox()` also requires
  (`self.options["path"]`, bare-indexed). If `path` is ever left unset,
  every upload attempt raises `KeyError` - not a `requests` exception or
  `OSError`, so the existing `except` clauses around the upload call
  never catch it - which aborts that entire upload cycle silently.
- **`nextcloud.py`**: `_make_session()` returns `False` on bad
  credentials or a bad `baseurl`/path (a 401 or 404 response), but
  `on_internet_available` never checks that return value before
  continuing to use `self.session` - which is still `None` in that
  case - guaranteeing `AttributeError: 'NoneType' object has no
  attribute 'request'` on every single internet-available cycle instead
  of the clean "wrong creds"/"path does not exist" log message the code
  clearly intended.

## `hashespwnagotchi.py` - real security concern (found this pass, now FIXED)

`_writeEAPOL()` and `_writePMKID()` build `hcxpcapngtool` commands with
Python string formatting (`"hcxpcapngtool -o {}.22000 {} ...".format(...)`)
and execute them with `subprocess.getoutput()`, which runs the string
through a real shell (`/bin/sh -c`) rather than calling the binary
directly with an argument list.

This fork's own handshake filenames embed the AP's ESSID directly -
confirmed convention is `{ESSID}_{BSSID}.pcap`/`.pcapng` (this plugin's
own `_essid_from_path`/`_bssid_from_path` helpers assume exactly this
shape, splitting the filename on `_`). An ESSID is a value any nearby
device can broadcast as literally anything, including shell
metacharacters (backticks, `$()`, `;`, `|`, etc.). Since that string
ends up as part of the filename passed into a shell-interpreted command,
a maliciously-named nearby AP could achieve command injection - running
arbitrary commands as root - the moment the pwnagotchi captures a
handshake from it and this plugin attempts to convert the file. This
applies to the real-time `on_handshake` path too, not just the broken
`.pcap` batch scan, since `on_handshake` is handed the real filename
directly and isn't affected by that bug.

**Fixed** in the `plugins-wip` rebuild (`HashesPwnagotchiNG`): every
external command (`hcxpcapngtool`, `tcpdump`) now runs via
`subprocess.run([...], shell=False)` with each argument passed
separately, so nothing from a filename can ever be shell-interpreted,
regardless of what an AP names itself. The rebuild also fixed a
previously-unknown `on_config_changed` crash bug (`self.status` was
referenced but never assigned - only `self.report` was - so setting the
`interval` option crashed this method every time, silently disabling the
startup batch-conversion pass entirely), the shared `.pcap` bug, the
fragile `path.split(".")[0]` filename parsing (now `os.path.splitext()`
throughout), a Python-2-only `.encode("hex")` call in the PMKID repair
path, the disabled whitelist (re-enabled), and a permanent-skip-on-
failure bug (bounded retries added). Full detail, and the full sandbox
test suite proving the fix, in
`plugins-wip:hashespwnagotchi-suite/NOTES.md`.

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
