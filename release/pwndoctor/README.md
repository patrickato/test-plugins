# PwnDoctor — v0.7.0-pre1 release candidate

> Status: **CI-validated release candidate; physical Pi/Jayofelony validation pending.**

PwnDoctor is an offline-first health, diagnosis and guarded self-healing plugin for Jayofelony Pwnagotchi. It is designed as a single Doctor with a small trusted runtime, a persistent Patient Chart, owner-controlled Standing Orders, a local Toolbox, and a data-driven Medical Library of Condition Packs.

## What it does

- inspects core services, storage, power/throttle state, Wi-Fi/monitor state, rfkill, Pwnagotchi config, Bettercap reachability, time/NTP, memory/swap, route/DNS, temperature, logs and selected failure signatures;
- matches evidence against built-in and data-driven conditions;
- explains likely causes and practical next steps;
- provides a plain-language narrative summary;
- can apply only allow-listed remedies, under owner-selected autonomy policy;
- verifies repairs and reports `verification unknown` when evidence is insufficient;
- uses persistent circuit breakers to avoid repair loops;
- maintains a bounded Patient Chart with device identity, diagnostic coverage, known-good summary, recurrence episodes and remedy outcomes;
- supports first-party bundled Condition Packs and separate user/community packs;
- can create a sanitized support ZIP with bounded/redacted diagnostic evidence;
- works offline; network access is not required for core diagnosis or treatment.

## Safety model

PwnDoctor follows four rules:

1. **Unknown stays unknown.** Missing evidence never becomes fake success.
2. **Knowledge is not authority.** Loading a Condition Pack does not grant it arbitrary execution rights.
3. **The owner sets Standing Orders.** Observe, conservative, assertive, dry-run, opt-outs and confirm-required conditions are explicit.
4. **Verify or say you cannot verify.** A remedy is not called fixed merely because a command returned.

See `docs/SECURITY_AND_SAFETY.md` for the full model.

## Requirements

- Jayofelony/Pwnagotchi custom-plugin support;
- Python standard library only for Doctor itself;
- Pwnagotchi normally runs plugins with sufficient privileges for guarded system actions;
- optional system commands are used only when present: `systemctl`, `iw`, `rfkill`, `vcgencmd`, `timedatectl`, `journalctl`, `dpkg`;
- no additional Python package is required by Doctor.

## Install location

Current Jayofelony defaults use:

`/etc/pwnagotchi/custom-plugins/`

with `main.custom_plugins` controlling the actual custom-plugin directory.

See `docs/INSTALL.md`.

## Package layout

The standalone archive contains:

- `doctor.py` — plugin runtime;
- `doctor_packs/` — first-party bundled Medical Library;
- `examples/doctor.config.toml` — complete example configuration;
- `examples/doctor.d/` — user/community Condition Pack examples;
- `docs/` — install, configuration, safety, troubleshooting, compatibility and validation guides;
- `tests/` — off-Pi test suite/harness;
- `LICENSE` — GPLv3;
- `RELEASE_MANIFEST.json` and `SHA256SUMS`.

## Validation status

- v0.7.0-pre1 automated/off-Pi suite: required green;
- Python 3.13 CI: active;
- release assembly/integrity verification: required green;
- real Pi/Jayofelony physical validation: **pending**;
- no `physical_validated` compatibility claim will be made until the exact CI-tested artifact passes the owner checklist.

## Collaboration

Claude and OpenAI develop PwnDoctor in separate collaboration lanes. The release branch consumes Claude's green runtime work and adds release/integrity engineering without rewriting Claude's branch history.

## License

GPLv3, matching the repository license and upstream project ecosystem.
