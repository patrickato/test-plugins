# Notes: cracked-password display/export cluster

**Status: all 3 KEPT on the master list.** `mycracked_pw.py` works
correctly with one minor staleness quirk. `display-password.py` and
`display-password-qr.py` share one bug that kills half of each file's
functionality, but their headline on-screen feature is unaffected and
already works.

## The three plugins and how they relate

All three are variants of the same author's (itsdarklikehell, forking
an original by @silentree12th / @nagy_craig) idea: read cracked
passwords out of `wpa-sec.cracked.potfile` (and an `onlinehashcrack`
CSV) and do something useful with them. They are not independent
implementations - `display-password.py` and `display-password-qr.py`
are byte-for-byte copies of `mycracked_pw.py`'s `_update_all()` method
with the same variable names, same file paths, same QR-generation
block - minus three import lines.

- **`mycracked_pw.py`** - the working original. Grabs all cracked
  passwords from both source files, writes a deduplicated wordlist to
  `/etc/pwnagotchi/wordlists/passwords/mycracked.txt` (explicitly
  intended to feed back into dictionary-crack plugins like the old
  `quickdic.py` or the current `best_quickdic`), and generates a
  `WIFI:S:...;T:WPA;P:...;;` QR code per network under
  `/home/pi/qrcodes/`.
- **`display-password.py`** - adds an on-screen display element
  showing the most recently cracked password/SSID, via
  `on_ui_setup`/`on_ui_update`. Also carries a full copy of
  `mycracked_pw.py`'s `_update_all()` method (QR + wordlist
  generation), but with `qrcode`, `csv`, and `io` never imported.
- **`display-password-qr.py`** - identical to `display-password.py`
  (same class name `DisplayPassword`, same on-screen display code,
  same broken `_update_all()`), plus an unused Flask/Jinja `TEMPLATE`
  string meant for a web-UI page listing generated QR codes. Despite
  the filename and header comment ("shows recently cracked passwords
  ... as a qrcode"), nothing in this file actually pushes a QR code to
  the physical display - the only QR-rendering code is the broken
  `_update_all()`, and the on-screen text path (`on_ui_update`) is
  pure text, identical to `display-password.py`'s.

## The shared bug: missing imports in `_update_all()`

`display-password.py` and `display-password-qr.py` both import only:

```python
import pwnagotchi
import logging
import os
```

(`display-password-qr.py` additionally imports `json`, `glob`, unused
by anything in the file.) But their `_update_all()` method - copied
from `mycracked_pw.py` - references `csv.DictReader(...)`,
`qrcode.QRCode(...)`, `qrcode.constants.ERROR_CORRECT_L`, and
`io.StringIO()`, none of which are imported. The moment
`_update_all()` reaches the `onlinehashcrack.cracked` block (or, if
that file doesn't exist, the moment it reaches `qrcode.QRCode(...)` in
the QR-save loop, assuming any password was found), it raises an
uncaught `NameError` and the method aborts.

Consequences:

- `on_loaded()` calls `_update_all()` directly (not inside a
  try/except at the call site), so on the first plugin load after a
  password has ever been cracked, this raises. In pwnagotchi's plugin
  loader an exception inside `on_loaded()` typically just gets logged
  and the plugin continues running (it doesn't crash the whole
  agent), but `_update_all()` itself never completes - no QR codes and
  no `mycracked.txt` wordlist are ever produced by either of these two
  files.
- The `on_ui_setup`/`on_ui_update`/`on_webhook`/`on_unload` methods are
  completely separate code paths that never call `_update_all()`.
  They shell out directly: `tail -n 1 wpa-sec.cracked.potfile | awk
  -F: '{print $3 " - " $4}'`. This is what actually appears on the
  pwnagotchi screen, and it works fine independently of the broken
  method - the advertised "shows recently cracked passwords on the
  display" feature is intact in both files.

## The fix (identical for both files)

Add the three missing imports at the top:

```python
import qrcode
import csv
import io
```

That alone makes `_update_all()` functionally identical to
`mycracked_pw.py`'s (down to writing to the same
`/etc/pwnagotchi/wordlists/passwords/mycracked.txt` and
`/home/pi/qrcodes/` paths `mycracked_pw.py` also writes to - running
more than one of these three plugins together is redundant, not
conflicting, since they'd just re-derive the same files).

Alternative fix, if the QR/wordlist side-feature isn't wanted from
these two files at all (since `mycracked_pw.py` already covers it):
delete the entire `_update_all()` method and its two call sites
(`on_loaded()`'s `self._update_all()` line, and the
`os.makedirs("/home/pi/qrcodes/")` setup it doesn't need without that
method). Neither file's actual display feature depends on it.

## `display-password-qr.py`'s misleading name and dead template

Worth flagging on its own regardless of which fix above is chosen:
the file name and `__description__`/`__help__` strings ("displays
recently cracked passwords ... as a qrcode") promise on-device QR
rendering that the file has never actually done - the embedded
`TEMPLATE` Jinja string builds a web-UI *list of links* to
`/home/pi/qrcodes/<file>`, it doesn't render anything to the e-ink/LCD
screen, and nothing in the file registers that template with the web
UI (no `on_webhook` route serving it, no reference to `TEMPLATE`
anywhere outside its own definition - it's dead code). If this plugin
is ever picked up for real use, the name is worth keeping only if the
web-UI QR gallery is actually wired up; otherwise it's functionally
identical to `display-password.py` under a more confusing name.

## `mycracked_pw.py`'s minor issue: staleness on quiet runs

Only issue found here, and it's minor: `_update_all()` (which works
correctly, all three imports present) only runs from `on_loaded()`
(once, at plugin load) and `on_handshake()` (once per new handshake
capture). If a run goes a long time between new handshakes, the
`mycracked.txt` wordlist and the QR-code folder simply don't get
regenerated in between - not a bug, since there's nothing new to add,
but worth knowing if something external is expected to pick up
newly-cracked passwords from the wpa-sec potfile itself (e.g. a
password cracked by wpa-sec.net's own backend rather than by a local
`on_handshake` capture) - that case wouldn't trigger a refresh until
the next handshake or plugin reload.

## Dependencies (all 3)

Declared `pip` dependency in all three is just `scapy` (unused by any
of the three - dead/copy-pasted metadata, not a real requirement).
`mycracked_pw.py` and any fixed version of the other two additionally
need the `qrcode` package (not declared in `__dependencies__` in any
of the three files - a real gap if `mycracked_pw.py` is ever
freshly-installed via the plugin manager rather than hand-copied,
since `qrcode` isn't part of the base image). No apt dependencies.
