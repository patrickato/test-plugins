# Notes: attack-mode toggles & AP restriction cluster

**Status: all 3 REMOVED (`cuffs.py`, `enable_assoc.py`, `enable_deauth.py`).**

Sources: all three from `itsdarklikehell/pwnagotchi-plugins`.

This is the first cluster of a new review pass - moving from the
discovery-audit clusters (20-26) to a category-by-category pass through
the whole master list, grouping plugins that were sitting in the same
category section but hadn't been individually source-reviewed yet.

## 1. What each one is and does

1. **`cuffs.py`** - overrides the agent's own `get_access_points()` so
   only whitelisted APs/BSSIDs are ever attacked; everything else is
   filtered out before deauth/assoc logic ever sees it.
2. **`enable_assoc.py`** (`Do_Assoc`) - forces `personality.associate =
   True` on load, `False` on unload; tracks and displays an on-screen
   association counter.
3. **`enable_deauth.py`** (`Do_Deauth`) - same idea for
   `personality.deauth`, with its own on-screen counter.

## 2. `cuffs.py` - one low-severity bug, removed anyway

```python
for ap in access_points:
    if not self.is_whitelisted(ap):
        access_points.remove(ap)   # mutates the list while iterating it
```
Removing an item mid-loop shifts later elements down one slot, so the
loop can skip checking the item that slides into the current index -
with two or more consecutive non-whitelisted APs, some survive removal
in this particular list. Low severity in practice: the resulting
`self.filtered_ap_list` is set but never read anywhere else in the file,
and the plugin's actual enforcement path is a separate method,
`custom_get_access_points()`, which filters correctly with a list
comprehension (`aps.append()` only for whitelisted APs) - no mutation
bug there. So real attack-scoping worked; only an internal log count/
unused list was inaccurate.

**Fix, documented for reference even though removed:**
```python
access_points[:] = [ap for ap in access_points if self.is_whitelisted(ap)]
```

## 3. `enable_assoc.py` / `enable_deauth.py` - no bugs, removed as redundant

Confirmed via this fork's own `pwnagotchi/defaults.toml`:
```
deauth = true
associate = true
```
Both are **already enabled by default** out of the box - this is core
pwnagotchi behavior, not something either plugin adds. What the plugins
actually do:
- **On load:** force `associate`/`deauth` back to `True` - a no-op
  against the default, only meaningful if the user had manually set
  either to `False` in `config.toml`.
- **On unload:** force it to `False` for the rest of that session.

So functionally these are a **live kill-switch** (disable the plugin to
turn deauth or assoc off without touching `config.toml` or restarting),
not an "enabler" the way their descriptions ("Enable and disable X on the
fly") imply at first read. Both files were otherwise clean - correct UI
element add/remove on load/unload, no dead imports, no wrong hook names.

## 4. Decision

All three removed by user decision - `cuffs.py` for its bug (despite low
severity), `enable_assoc.py`/`enable_deauth.py` because their actual
function (a kill-switch against an already-on-by-default setting) wasn't
what was wanted.

## 5. Dependencies (all removed)

`scapy` (pip, declared but unused - same boilerplate pattern seen
throughout this project) on all three; no other dependencies.
