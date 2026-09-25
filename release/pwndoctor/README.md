# PwnDoctor v1.0.0-rc1

**Status:** software-complete v1 release candidate; automated/off-Pi validation green when the
final release gate passes; exact-artifact physical Jayofelony/Pi validation remains required
before the stable `1.0.0` tag.

PwnDoctor is an offline-first health, diagnosis and guarded self-healing plugin for stock
Jayofelony Pwnagotchi. It acts as the device's local "immune system":

**probe → diagnose → explain → gated-treat → verify → remember**

## v1 feature set

- broad guarded system/service/radio/storage/power/config/network diagnostics;
- Condition Pack v1 Medical Library with bundled vs external/catalog trust classes;
- tri-state truth: true / false / unknown;
- allow-listed remedies with Standing Orders, owner vetoes, confirmations, guards and a
  persistent circuit breaker;
- treatment decision trace explaining every allow/block/verify decision;
- Patient Chart v2 with lossless schema migration, recurrence/chronic memory and bounded
  remedy-outcome history;
- per-device remedy efficacy: poor verified history can only reduce automation to confirmation;
- causal/root suppression so downstream symptoms do not trigger redundant automatic repairs;
- recovery posture for questionable media/config integrity;
- bounded known-good generations and drift comparison;
- plain-language narrative;
- sanitized one-click support bundle;
- offline pack linter + tri-state simulation/replay;
- SHA-pinned opt-in catalog fetch utility; cached catalog packs are always explain-only;
- specialist-provider hub via `/run/pwnagotchi/health.d/` using
  `pwndoctor/provider/v1` snapshots;
- privacy-light `pwndoctor/status/v1` machine-readable status contract;
- Doctor self-test/capability map;
- reproducible package assembly, manifest/checksums and public-contract lock;
- guided physical-validation recorder that refuses to emit a `physical_validated` row until
  every required check passes.

## Safe first run

Use the included `examples/doctor.config.toml` and start with:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

Then restart Pwnagotchi, open Doctor in the WebUI, review findings/self-test, and only increase
autonomy after you are comfortable with the behavior on your hardware.

## Package contents

- `doctor.py`
- `doctor_packs/` — first-party Medical Library
- `examples/doctor.config.toml`
- `examples/doctor.d/`
- `catalog_fetch.py` — optional pinned HTTPS catalog staging utility
- `physical_validation.py` — guided validation evidence recorder
- `docs/` — installation, configuration, usage, security, compatibility, troubleshooting,
  schema/roadmap/validation docs
- `tests/`
- `RELEASE_MANIFEST.json`
- `SHA256SUMS`
- `COMPATIBILITY_MATRIX.json`
- `LICENSE`

## Important safety rule

Knowledge and authority are separate. Downloading, caching, signing or loading a Condition Pack
does not create treatment authority. Only compiled allow-listed actions plus owner Standing
Orders and all safety/verification gates can permit mutation.

## Validation status

Until the exact v1 RC artifact passes `docs/PHYSICAL_VALIDATION.md` on a real Jayofelony unit,
compatibility remains correctly labeled `ci_validated` / `physical_validation_pending`.
