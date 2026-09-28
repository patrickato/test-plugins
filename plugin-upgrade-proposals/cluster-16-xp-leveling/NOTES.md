# Notes: XP/leveling plugin cluster

**Status: `exp.py` and `Experience-Plugin-Pwnagotchi` REMOVED (exact
duplicates). `expv2.py`, `xp.py`, `xp_grid.py` KEPT.**

Sources: `exp.py`/`expv2.py` from `itsdarklikehell/pwnagotchi-plugins`;
`Experience-Plugin-Pwnagotchi`'s own `exp.py` from
`GaelicThunder/Experience-Plugin-Pwnagotchi` (the unmirrored upstream);
`xp.py`/`xp_grid.py` from `itsdarklikehell/pwnagotchi-plugins`
(originally by sliim).

## 1. What each one is and does

1. **`exp.py`** - awards XP for handshakes/associations/deauths, levels
   up on an XP threshold, shows "Lv" and "Exp" (progress-bar) UI
   elements.
2. **`expv2.py`** - identical leveling system to `exp.py`, plus a
   third derived stat, "Strength" (`exp * level * 0.05`), shown as a
   "Str" UI element.
3. **`Experience-Plugin-Pwnagotchi`** - the unmodified upstream repo
   that `exp.py` was copied from.
4. **`xp.py`** - a separate, much larger leveling system: 20 weighted
   event types (handshakes, deauths, AI events, peer detection,
   etc.), 21 named "ranks" from "newbie" to "legend" that change the
   on-screen face glyph set as you level up, a live-updating webhook
   dashboard page, and custom internal pwnagotchi events
   (`level_up`, `level_update`, `rank_update`) other plugins can
   listen for.
5. **`xp_grid.py`** - a companion to `xp.py` only (`xp.py` must be
   enabled): broadcasts your level/rank to grid peers via
   `on_level_update`/`on_rank_update`, and displays a nearby peer's
   level next to their name on-screen.

## 2. `exp.py` / `Experience-Plugin-Pwnagotchi` - removed, exact duplicates

Diffed `itsdarklikehell/pwnagotchi-plugins/exp.py` directly against
`GaelicThunder/Experience-Plugin-Pwnagotchi/exp.py` (the original,
unmirrored source). Identical logic throughout - the only differences
are whitespace/f-string reformatting and an added author credit line.
Same duplicate-mirror pattern as the Discord/Telegram (Group 2) and
fake-AP (Group 27) removals earlier in this project - one bullet's
worth of actual code shipped under two names. Removed both, since
`expv2.py` (below) is a strict superset of everything they did.

## 3. `expv2.py` - kept, but carries two bugs inherited unchanged from `exp.py`

Character-for-character identical to `exp.py` apart from the added
Strength calculation - so it inherits both of `exp.py`'s real bugs:

**Bug 1 - missing `__defaults__` for UI-position options.**
`__defaults__` only declares `{"enabled": False}`, but `on_ui_setup`
unconditionally reads:

```python
int(self.options["lvl_x_coord"])
int(self.options["lvl_y_coord"])
int(self.options["exp_x_coord"])
int(self.options["exp_y_coord"])
int(self.options["str_x_coord"])   # v2 only
int(self.options["str_y_coord"])   # v2 only
```

and `on_ui_update` reads `self.options["bar_symbols_count"]` the same
way - none of these six options have a fallback, so `on_ui_setup`
would raise `KeyError` on load unless every one of them is set
explicitly in `config.toml`. Same recurring pattern as
`adsbsniffer.py` and `dashboard.py`/`dashboard2.py` from earlier
clusters.

**Fix:**
```python
__defaults__ = {
    "enabled": False,
    "lvl_x_coord": 5,
    "lvl_y_coord": 95,
    "exp_x_coord": 25,
    "exp_y_coord": 95,
    "str_x_coord": 80,
    "str_y_coord": 95,
    "bar_symbols_count": 10,
}
```
(coordinates illustrative - pick values that don't collide with other
on-screen elements.) Not applied, documented for whenever this plugin
is actually enabled.

**Bug 2 - `==` instead of `=` in legacy-save migration.**
`loadFromTxtFile` (only used once, during migration from the old
`.txt` save format via `migrateLegacySave`) has a copy-paste typo:

```python
def loadFromTxtFile(self, file):
    if os.path.exists(file):
        outfile = open(file, "r+")
        lines = outfile.readlines()
        linecounter = 1
        for line in lines:
            if linecounter == 1:
                self.exp = int(line)        # correct - assignment
            elif linecounter == 2:
                self.lv == int(line)        # BUG - comparison, discarded
            elif linecounter == 3:
                self.exp_tot == int(line)   # BUG - comparison, discarded
            elif linecounter == 4:
                self.strength == int(line)  # BUG (v2 only) - comparison, discarded
            linecounter += 1
        outfile.close()
```

Anyone migrating from a legacy `.txt` save would silently keep only
their saved `exp` value - level, total-XP, and (in v2) strength would
silently reset rather than carry over, because the `==` lines do
nothing. Low real-world impact today (a one-time migration path from
a save format this old, and a fresh install never touches it at all),
but a genuine bug if that path is ever exercised.

**Fix:** change the three `==` to `=`.

**File-conflict note (why `exp.py` couldn't safely coexist with
`expv2.py` anyway):** both save to the same relative filename,
`exp_stats.json`, in their own plugin file's directory, and both add
UI elements named `"Lv"`/`"Exp"`. Installing both together (had both
been kept) would have meant a JSON-schema mismatch (v2 expects a
`"strength"` key the v1 file doesn't have) and a UI element-name
collision - one more reason `expv2.py` alone, not both, is the right
choice.

## 4. `xp.py` - kept, two gaps found

**Gap 1 - missing `__defaults__`, same pattern as above.** `on_loaded`
reads `opts["level_position"]`, `opts["rank_position"]`,
`opts["progressbar_position"]`, and `on_ready` reads
`self.options["load_initial_xp"]` - none declared in `__defaults__`
(`{"enabled": False}` only). Fix is the same shape as `expv2.py`'s
Bug 1 above - add class-level defaults for all four keys.

**Gap 2 - permanent 4x XP-rate penalty from a dead AI hook.** Every
XP award runs through:

```python
def _update_xp(self, event, multiplier=1):
    ...
    xp = EVENTS_XP[event] * multiplier
    if not self.ai_ready:
        xp /= 4
```

`self.ai_ready` is only ever set `True` inside `on_ai_ready(self,
agent)`. The AI/RL layer (all `on_ai_*` hooks) is fully removed on
this jayofelony fork, so `on_ai_ready` never fires, `self.ai_ready`
never becomes `True`, and every single XP award is permanently
divided by 4 for the life of the install. Not a crash - the plugin
works, levels still increase - just at a quarter of the rate its own
`EVENTS_XP` table implies. Same category as the other dead-`on_ai_*`
findings throughout this project (Cluster 8's `gsmfake.py` aside,
this is architecture dead-weight rather than a hard error).

**Fix, if ever prioritized:** either drop the `if not self.ai_ready:
xp /= 4` gate entirely (since `ai_ready` can never legitimately
become `True` here), or set `self.ai_ready = True` unconditionally in
`on_loaded`/`on_ready` so the intended full XP rate applies. Not
applied, documented for whenever this plugin's balance is revisited.

**Robustness note, not fixed:** `on_handshake` busy-waits on the
capture file with no timeout (`while not os.path.exists(filename):
time.sleep(1)`) - would block indefinitely rather than giving up if
the file never appears. No known trigger for this on the current
setup, flagged for awareness only.

**Design note, not a bug:** `xp.py` changes the pwnagotchi's on-screen
face glyph set at runtime as you rank up
(`faces.load_from_config(update)`), based on the current rank's
`"head"` characters. This is intentional and self-contained, but
worth knowing if any other installed plugin also modifies faces at
runtime - last-write-wins between them.

## 5. `xp_grid.py` - kept, no bugs found

Correctly avoids the missing-`__defaults__` pitfall found everywhere
else in this cluster: instead of declaring `__defaults__` for its
`position`/`name_position` options, it defensively sets sane fallback
values directly into `self.options` inside its own `on_loaded()` if
they're absent - a better pattern than most plugins reviewed in this
project use. Requires `xp.py` to be enabled (listens for the custom
`level_update`/`rank_update` events `xp.py` emits) - not functional
on its own.

**Integration dependency, not a bug:** `on_ui_setup` removes and
re-adds a UI element named `"friend_name"` that it expects some other
component (the peer/grid display) to have already created before
this plugin's `on_ui_setup` runs, so it can reposition it and read
back which peer is currently shown. This is deliberate design, not a
defect, but means `xp_grid.py`'s behavior is coupled to load order
relative to whatever plugin owns that element - worth knowing if
peer-name display ever looks wrong after enabling this plugin.

## 6. Dependencies (kept plugins)

`expv2.py`: `scapy` (pip, declared but unused - same unused-boilerplate
dependency pattern seen elsewhere in this project). No hardware.
`xp.py`: `scapy` (pip, same unused-boilerplate note), `flask` (pip,
already a core pwnagotchi dependency, used for the webhook dashboard).
No hardware. `xp_grid.py`: no declared dependencies beyond pwnagotchi's
own `grid`/`plugins`/`ui` modules; requires `xp.py` enabled and grid/
peer functionality active (unaffected by the AI/RL removal on this
fork, since grid/peer discovery is a separate, still-present feature).
