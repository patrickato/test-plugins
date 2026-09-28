# Notes: age/strength plugin cluster

**Status: all 3 KEPT (`age.py`, `agev2.py`, `age.py` AlienMajik
variant).**

Sources: `age.py`/`agev2.py` from `itsdarklikehell/pwnagotchi-plugins`
(originally by Kaska); `age.py` (AlienMajik variant) from
`alienmajik/pwnagotchi_plugins`.

## 1. What each one is and does

1. **`age.py`** - adds four on-screen counters: "Age" (wall-clock time
   since the plugin loaded, formatted `Xy Ym Zd`), "Strength" (trained-
   epoch count), "Access Points" (seen count), "Deauths Sent". Loads a
   one-time baseline from `/root/brain.json` (`epochs_lived`,
   `epochs_trained`) on startup.
2. **`agev2.py`** - the same four stats, same logic, near-identical
   code to `age.py` with one renamed internal UI-element ID.
3. **`age.py` (AlienMajik variant)** - unrelated plugin, filename
   collision only. A full RPG-style system: age/strength "titles" with
   narrative lore text per tier, a prestige/rebirth mechanic, random
   events (lucky breaks, time warps, personality swaps), personality
   traits (aggro/stealth/scholar) derived from play style, achievements,
   points decay for inactivity, and a styled webhook status page at
   `/plugins/age/`.

## 2. `age.py` / `agev2.py` - kept, shared gaps documented

**Gap 1 - missing `__defaults__` for UI-position options.**
`__defaults__` only declares `{"enabled": False}` in both files, but
`on_ui_setup` unconditionally reads:

```python
int(self.options["age_x_coord"])
int(self.options["age_y_coord"])
int(self.options["str_x_coord"])
int(self.options["str_y_coord"])
int(self.options["ap_x_coord"])
int(self.options["ap_y_coord"])
int(self.options["deauth_x_coord"])
int(self.options["deauth_y_coord"])
```

None of these eight options have a class-level default, so `on_ui_setup`
would raise `KeyError` on load unless every one of them is set
explicitly in `config.toml`. Same recurring pattern as
`adsbsniffer.py`, `dashboard.py`/`dashboard2.py`, `exp.py`/`expv2.py`,
and `xp.py` from earlier clusters.

**CORRECTED FIX (see Cluster 18's project-wide `__defaults__`
correction):** this originally recommended adding a class-level
`__defaults__` block. That would not actually fix anything on this
jayofelony fork - I later confirmed its plugin loader never reads
`__defaults__` at all, on any plugin. The two fixes that actually
work here:

```toml
# Option A - config.toml, no code change:
[main.plugins.age]
enabled = true
age_x_coord = 5
age_y_coord = 80
str_x_coord = 80
str_y_coord = 80
ap_x_coord = 5
ap_y_coord = 90
deauth_x_coord = 80
deauth_y_coord = 90
```

```python
# Option B - patch on_ui_setup to use .get() fallbacks:
int(self.options.get("age_x_coord", 5))
int(self.options.get("age_y_coord", 80))
# ...and so on for the remaining six keys
```

(coordinates illustrative - pick values that don't collide with other
on-screen elements.) Neither applied, documented for whenever either
plugin is actually enabled.

**Gap 2 - three of four stats are permanently frozen on this fork.**
Strength, Access Points, and Deauths Sent are only ever updated inside
`on_ai_training_step`:

```python
def on_ai_training_step(self, agent, _locals, _globals):
    self.train_epochs += 1
    self.access_points_seen += len(agent.view().access_points())
    self.deauths_sent += agent.stats("deauth")
    if self.train_epochs % 100 == 0:
        self.strength_checkpoint(agent)
```

This hook belongs to the AI/RL layer, which is fully removed on this
jayofelony fork, so it never fires - these three stats stay at 0
forever. Only "Age" actually functions, and even that is wall-clock
time since the plugin loaded (`datetime.now() - self.device_start_time`),
not epoch-based despite both files' `__description__` claiming
"based on epochs." `self.epochs` is tracked internally (incremented in
`on_epoch`, which does still fire) but is only used for the periodic
`age_checkpoint()` status message, never for the displayed Age value
itself.

**Fix, if ever prioritized:** either accept these fields as
AI-dependent and cosmetic on this fork, or move the counting logic
into `on_epoch`/`on_association`/`on_deauthentication` (all of which
do fire normally) the way AlienMajik's variant does, so the stats
actually progress without a working AI layer. Not applied - kept
per broad-scope philosophy since this is a fork-compatibility
limitation, not a crash.

## 3. `agev2.py` - one additional bug, worse off than `age.py`

**Real bug: Age display is broken.** `on_ui_setup` adds the Age
element under a renamed key:

```python
ui.add_element("AgeV2", LabeledValue(..., label="♥ Age", ...))
```

but `on_ui_update` still calls the v1 key:

```python
def on_ui_update(self, ui):
    ui.set("Age", self.calculate_device_age())   # BUG: no element named "Age" exists
```

Since no UI element named `"Age"` was ever added by this plugin,
`ui.set("Age", ...)` targets a key that doesn't exist in the view's
state - this would raise on every single `on_ui_update` cycle rather
than silently failing. The apparent intent (renaming the element so
`age.py` and `agev2.py` could theoretically coexist without a UI
element-name collision) wasn't followed through with the matching
`ui.set()` change - a genuine regression versus `age.py`, which gets
this one piece right.

**Fix:** change `ui.set("Age", ...)` to `ui.set("AgeV2", ...)`.
One-line change, not applied - documented for whenever this plugin is
actually enabled.

**Minor, dead code:** a leftover module-level line instantiates an
unused, never-referenced second copy of the plugin outside any
framework hook:

```python
# Instantiate the plugin
age_plugin = AgeV2()

# Example usage (replace this with the actual Pwnagotchi usage)
# ...
```

Harmless (no side effects beyond `__init__` setting instance
attributes) but clearly leftover example/scratch code, not part of
the plugin's real operation. Worth deleting if this file is ever
cleaned up.

**Filename-collision note:** `agev2.py` and `age.py` use different
filenames, so both can coexist on disk without conflict - the only
filename collision in this cluster is between `age.py`
(itsdarklikehell) and `age.py` (AlienMajik), which is not a concern
unless both are ever installed together (not the case here, since
they weren't proposed as coexisting).

## 4. `age.py` (AlienMajik variant) - kept, no bugs found

By far the most carefully engineered plugin reviewed in this project
to date. Notable design choices, several of them explicitly
documented in the file's own comments as fixes for past (v4) bugs:

- **Doesn't depend on the dead AI hook for core progression.**
  `on_epoch` (which does fire normally on this fork) tracks whether
  AI training steps have been seen recently; if not (as will always
  be the case here), it accrues Strength passively every epoch
  instead of freezing. This is the exact gap `age.py`/`agev2.py` have
  - AlienMajik's version was clearly written with a no-AI environment
  in mind.
- **Correctly handles both handshake extensions**: `HANDSHAKE_EXTS =
  ('.pcapng', '.pcap')` with an explicit comment about bettercap's
  2.9.5.5+ extension change - avoids the `.pcap`-only-matches bug
  pattern found repeatedly elsewhere in this project (`f0xtr0t`,
  `wardrive.py`, etc.).
- **Thread safety**: uses an `RLock` (not a plain `Lock`) around all
  shared state, with a code comment explaining why a plain lock would
  deadlock (helper methods that acquire the lock are called from
  already-locked sections).
- **Save durability**: writes to a temp file, flushes, `fsync`s, then
  atomically `os.replace`s over the real data file, and throttles
  saves to once per `save_interval` seconds (default 60) rather than
  writing on every event - avoids both SD-card wear and a truncated
  file from a power loss mid-write.
- **Defensive config parsing**: every option is read through typed
  helpers (`_opt_int`/`_opt_float`/`_opt_bool`) that catch bad values
  and fall back to a default with a logged warning, rather than
  letting a malformed `config.toml` value crash the plugin.
- Self-documented bugfix history in comments (e.g., a v4 multiplier
  bug where `int(1.1) == 1` made "Time Warp" a no-op; a v4 achievement
  check that required exact set equality and could never actually
  match; a v4 decay bug that could wipe out an entire session's points
  in one hit).

No dependencies beyond the Python standard library plus pwnagotchi's
own bundled modules (`plugins`, `faces`, `fonts`, `components`,
`view`) - no `pip`/`apt` packages declared or needed, no additional
hardware.

## 5. Dependencies (all kept plugins)

`age.py`/`agev2.py`: `scapy` (pip, declared but unused - same
unused-boilerplate dependency pattern seen elsewhere in this project).
No hardware. `age.py` (AlienMajik): none declared, none needed beyond
the standard library and pwnagotchi's own bundled UI modules.
