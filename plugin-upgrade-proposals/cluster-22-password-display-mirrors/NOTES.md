# Notes: cracked-password display mirrors cluster

**Status: both KEPT (`show_password.py`, `show_pwd.py`). Findings-only.**

Sources: `show_password.py` by `@vanshksingh`, `show_pwd.py` is
itsdarklikehell's own rewrite of it - both from
`itsdarklikehell/pwnagotchi-plugins`.

This cluster was one of 7 spun out of a project-wide audit that found 42
plugins (across `itsdarklikehell`, `sniffleupagus`, and
`pwnagotchi-unofficial`'s archive) had never been added to the master
list at all - see Group 34 in the elimination log for the full audit and
the other clusters this produced.

## 1. What each one is and does

1. **`show_password.py`** - reads the last line of
   `/root/handshakes/wpa-sec.cracked.potfile`, parses out the network
   name/password with `awk`, and shows it on-screen; falls back to "No
   recently cracked passwords" if the file's empty or the read fails.
2. **`show_pwd.py`** - itsdarklikehell's rewrite of the same idea, same
   target file, different `awk` query.

Both are a third, independent mirror of the same underlying concept as
Cluster 7's `mycracked_pw.py`/`display-password.py`/`display-password-qr.py`
family - which read a **hashcat** potfile - except these two read a
**WPA-SEC** potfile (`wpa-sec.cracked.potfile`), a different file
produced by a different cracking/upload pathway (see the
`wpa-cracking-project-with-pwnagotchi`/`hashespwnagotchi.py` family
elsewhere on the list for context on WPA-SEC uploads).

## 2. `show_password.py` - one real gap

`on_ui_setup` reads `self.options['orientation']` directly, with no
`__defaults__`/`__dependencies__` block declared at all:

```python
if self.options['orientation'] == "vertical":
    ...
```

`KeyError` on load unless `orientation` is set explicitly in
`config.toml` - the recurring missing-defaults pattern found throughout
this project, and irrelevant either way since this fork's loader never
reads `__defaults__` regardless of whether one is declared.

The potfile read itself is reasonably defensive:
```python
try:
    last_line = os.popen(f'tail -n 1 {potfile_path} | awk -F: \'{{print $3 " - " $4}}\'').read().rstrip()
    if not last_line.strip():
        last_line = 'No recently cracked passwords'
except Exception as e:
    last_line = f'Error: {str(e)}'
```
Worth noting: `os.popen()` failures inside the shell pipeline itself
(e.g., `awk` erroring because the file doesn't exist) surface on stderr,
not as a Python exception - so the `except` clause mostly guards against
unrelated failures in invoking the shell at all. The `if not last_line.strip()`
empty-string check is what actually handles the common "no file /
nothing cracked yet" case, and it does handle it correctly.

**Fix:**
```python
def on_loaded(self):
    if "orientation" not in self.options:
        self.options["orientation"] = "horizontal"
    logging.info("display-password loaded")
```
(the same self-populating pattern `show_pwd.py` already uses - see below.)

## 3. `show_pwd.py` - fixes the gap, but changes the semantics of "recent"

**Fix present:**
```python
def on_loaded(self):
    logging.info(f"[{self.__class__.__name__}] plugin loaded")
    if "orientation" not in self.options:
        self.options["orientation"] = "horizontal"
```
Defensively self-populates the missing option - the same correct
workaround pattern used elsewhere in this project (`xp_grid.py`,
`blemon_plugin.py`) given `__defaults__` doesn't work on this fork. This
file does not `KeyError` on load.

**Behavioral change, not a crash bug:**
```python
# show_password.py - literally the last line of the file
os.popen(f'tail -n 1 {potfile_path} | awk -F: \'{{print $3 " - " $4}}\'')

# show_pwd.py - dedupes by network first, THEN takes the last of those
os.popen("awk -F: '!seen[$3]++ {print $3 \" - \" $4}' /root/handshakes/wpa-sec.cracked.potfile | tail -n 1")
```
`awk '!seen[$3]++ {...}'` prints only each network's (`$3`) *first*
appearance in the file, scanning top to bottom; `tail -n 1` then takes
the last of those first-appearance lines. Consequence: if a network is
cracked more than once and re-added to the potfile, its later/newer
entry is filtered out by the dedup and never surfaces - the display can
show an older crack for a network instead of the line that was truly
just added, which works against the plugin's whole purpose of showing
what was *just* cracked. This may be an intentional choice (avoids
re-displaying the same network back-to-back if it reappears), but it's
worth knowing it changes what "most recent" means compared to
`show_password.py`'s literal interpretation.

**Also dropped:** the friendly "No recently cracked passwords" fallback
and its surrounding try/except - `show_pwd.py` has neither, so an empty
result (nothing cracked yet, or file missing) displays as blank text on
the element rather than an explanatory message.

**Fix, if the literal-most-recent behavior is preferred:**
```python
last_line = os.popen(
    "tail -n 1 /root/handshakes/wpa-sec.cracked.potfile | awk -F: '{print $3 \" - \" $4}'"
).read().rstrip()
if not last_line.strip():
    last_line = "No recently cracked passwords"
```
(reverting to `show_password.py`'s query shape, while keeping
`show_pwd.py`'s already-fixed `orientation` defaulting.) Not applied -
both plugins work as shipped, this is a refinement not a bug fix, kept
per broad-scope philosophy for whenever either is prioritized.

## 4. Dependencies (both kept plugins)

Neither declares any pip/apt dependencies. Both read from
`/root/handshakes/wpa-sec.cracked.potfile` (hardcoded path, not
configurable) - requires whatever WPA-SEC upload/crack pathway populates
that specific file to already be in use (see
`wpa-cracking-project-with-pwnagotchi`/`hashespwnagotchi.py` elsewhere on
the list); neither plugin creates or populates that file itself.
