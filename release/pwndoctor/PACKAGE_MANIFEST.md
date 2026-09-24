# PwnDoctor package manifest (staging)

This file defines what will move from `test-plugins` into the standalone release after code/content freeze.

## Canonical source → standalone package

- `pwnagotchi-plugins/doctor.py` → `doctor.py`
- `pwnagotchi-plugins/doctor_packs/` → `doctor_packs/`
- `pwnagotchi-plugins/doctor.config.toml` → `examples/doctor.config.toml`
- `pwnagotchi-plugins/doctor.d/` → `examples/doctor.d/`
- `pwnagotchi-plugins/CONDITION_PACK_SCHEMA.md` → `docs/CONDITION_PACK_SCHEMA.md`
- `pwnagotchi-plugins/DOCTOR_ROADMAP.md` → `docs/DEVELOPMENT_ROADMAP.md` (optional for public repo)
- `pwnagotchi-plugins/DOCTOR_COMPATIBILITY_CONTRACT.md` → `docs/UPSTREAM_COMPATIBILITY_CONTRACT.md`
- `pwnagotchi-plugins/tests/test_doctor.py` + required harness → `tests/`
- repo `LICENSE` → `LICENSE`
- `release/pwndoctor/*.md` → top-level/docs as appropriate

## Do not package

- collaborator handoff notes;
- unrelated gap plugins;
- private preservation checkpoints;
- development-only branch notes;
- stale screenshots/logs/credentials/device-specific state.

## Final assembly rule

Do not manually maintain duplicate copies of `doctor.py` during development. Assemble the standalone package only from the frozen canonical files after Claude + OpenAI sign-off and physical validation.
## Generated integrity files

The release assembler generates:
- `RELEASE_MANIFEST.json` — package name/version plus SHA-256 for every canonical packaged file;
- `SHA256SUMS` — verification hashes for the assembled artifact.

The assembler verifies both before returning success.