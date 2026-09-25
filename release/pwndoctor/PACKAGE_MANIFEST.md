# PwnDoctor package manifest

This file defines the standalone PwnDoctor release assembled from the collaboration repository.

## Current target

- release candidate: `0.7.0-pre1`
- canonical runtime source: `pwnagotchi-plugins/doctor.py`
- canonical first-party Medical Library: `pwnagotchi-plugins/doctor_packs/`
- release assembly is reproducible and CI-verified
- Claude and OpenAI work in separate collaboration lanes; packaging consumes the integrated source without rewriting collaborator history

## Canonical source → standalone package

- `pwnagotchi-plugins/doctor.py` → `doctor.py`
- `pwnagotchi-plugins/doctor_packs/` → `doctor_packs/`
- `pwnagotchi-plugins/doctor.config.toml` → `examples/doctor.config.toml`
- `pwnagotchi-plugins/doctor.d/` → `examples/doctor.d/`
- `pwnagotchi-plugins/CONDITION_PACK_SCHEMA.md` → `docs/CONDITION_PACK_SCHEMA.md`
- `pwnagotchi-plugins/DOCTOR_ROADMAP.md` → `docs/DEVELOPMENT_ROADMAP.md`
- `pwnagotchi-plugins/DOCTOR_COMPATIBILITY_CONTRACT.md` → `docs/UPSTREAM_COMPATIBILITY_CONTRACT.md`
- `pwnagotchi-plugins/tests/test_doctor.py` + required harness → `tests/`
- repo `LICENSE` → `LICENSE`
- `release/pwndoctor/*.md` → top-level/docs as appropriate
- `release/pwndoctor/COMPATIBILITY_MATRIX.json` → `COMPATIBILITY_MATRIX.json`

## Do not package

- collaborator handoff notes;
- unrelated plugins;
- private checkpoints;
- development-only branch notes;
- stale screenshots/logs/credentials/device-specific state.

## Generated integrity files

The release assembler generates:
- `RELEASE_MANIFEST.json` — package name/version plus SHA-256 for every canonical packaged file;
- `SHA256SUMS` — verification hashes for the assembled artifact.

The assembler verifies both before returning success.

## Condition Pack inventory

`RELEASE_MANIFEST.json` records every bundled Condition Pack with filename, pack id, declared pack version, SHA-256 and whether it carries a remedy. Assembly verification rejects missing files, hash mismatches, id mismatches and duplicate bundled ids.

The manifest points to `COMPATIBILITY_MATRIX.json`; package verification rejects a missing/malformed matrix and rejects a matrix whose `target_version` does not match `Doctor.__version__`.

## Promotion rule

The CI-tested archive is the artifact to physically validate. A stable release/tag is promoted only after the exact artifact passes the physical checklist and the compatibility matrix records the hardware/image evidence.
