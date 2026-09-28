# Notes: dashboard plugin cluster - removed

**Status: both `dashboard.py` and `dashboard2.py` REMOVED**, per
explicit user decision ("we can drop both i dont think they will be
needed"). Kept here as a record, per this project's convention of
documenting every removal even when not being rebuilt.

## What they were

Both from the same author pair (itsdarklikehell / doki) - "everything
on one screen" plugins that consolidate a clock, RAM %, CPU %, CPU
temp, deauth counter, handshake counter, and a cracked-passwords count
(from `wpa-sec.cracked.potfile`) into a single set of UI elements,
instead of running separate `clock.py` + a deauth-counter plugin +
`memtemp` + a handshake-counter plugin individually.

`dashboard2.py` is `dashboard.py` with its Pivoyager-hat integration
removed - same element names, same layout approach (every position
read from `self.options["<name>_x_pos"/"_y_pos"]`), same counters.

## Why removed

- **`dashboard.py`** hard-requires a Pivoyager UPS/RTC hat.
  `on_loaded()` unconditionally starts a background thread and
  immediately calls `self.get_status()`, which runs
  `subprocess.run(["/usr/local/bin/pivoyager", "status"], ...)` with
  no existence check and no try/except around it. Without that
  specific hat installed, this throws `FileNotFoundError` and
  `on_loaded()` does not complete cleanly. (User has a Waveshare UPS,
  not a Pivoyager - different hat, different control binary/protocol
  - so even with that hardware on hand, this specific plugin wouldn't
  talk to it without a rewrite.)
- **`dashboard2.py`** has a real bug from an incomplete trim: its
  `on_ui_update()` still calls `status = self.get_status()`, but
  `get_status()` was one of the methods removed along with the
  Pivoyager code - it's not defined anywhere in the `Dashboard2`
  class. Every single UI refresh cycle throws `AttributeError:
  'Dashboard2' object has no attribute 'get_status'`. The `status`
  variable it assigns is also never used - dead, broken code left
  behind by an incomplete edit, not a deliberate feature.
- **Both** share an undeclared-`__defaults__` gap: none of their ~7-9
  position options (`clock_x_pos`, `mem_x_pos`, `cpu_x_pos`,
  `tmp_x_pos`, `deauth_x_pos`, `hand_x_pos`, `cracked_x_pos`, and
  `dashboard.py`'s additional `bat_x_pos`/`netstat_x_pos`) have
  class-level defaults - `on_ui_setup()` would `KeyError` unless every
  single one of them is set explicitly in `config.toml`. Same pattern
  found in `adsbsniffer.py`/`pwnaware.py` (Cluster 10).

Neither plugin would have worked out of the box on this build even
before the "not needed" decision - `dashboard.py` needed hardware not
present, `dashboard2.py` needed a one-line bug fix just to stop
crashing every refresh cycle, and both needed every position option
manually configured. If a consolidated-display plugin is ever wanted
again, `clock.py` (Cluster 11) plus the individually-kept counter/
status plugins already cover the same ground without inheriting these
bugs.
