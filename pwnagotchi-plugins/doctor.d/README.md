# `doctor.d/` — local, offline Condition Packs

Drop **data-only** JSON condition packs here (see `../CONDITION_PACK_SCHEMA.md`). At runtime the
Doctor loads them from the directory named by `main.plugins.doctor.condition_dir`
(default `/etc/pwnagotchi/doctor.d`). This folder in the repo is a **template + example**; copy
packs you want onto the device.

Rules the loader enforces (v0.6-pre1):
- **Data only.** A pack is JSON — no code. `detect`/`verify` are a tiny boolean tree over
  canonical signal keys.
- **Offline-first.** Packs load from local disk with no network.
- **Explain-only by default.** A pack that names a `fix.action` is shown as guidance, not run —
  even if the action exists. Set `main.plugins.doctor.allow_pack_remedies = true` to let *trusted
  local* packs invoke actions that are **already allow-listed** in the Doctor. A pack can never
  introduce a new executable action; unknown actions/guards stay inert.
- **Built-ins win.** A pack may not redefine a core condition id — the built-in takes precedence.
- **Bounded.** Up to 128 packs, ≤128 KB each; malformed/oversized files are skipped and logged.

`system.memory_pressure_warn.json` is a minimal, explain-only example: it warns early (info) when
memory use climbs past 85%, before the built-in `low_memory` (92%) fires. Use it as a starting
point for your own packs.
