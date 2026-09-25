# PwnDoctor v1 package manifest

## Target

- release candidate: `1.0.0-rc1`
- canonical runtime: `pwnagotchi-plugins/doctor.py`
- first-party Medical Library: `pwnagotchi-plugins/doctor_packs/`
- public contracts are locked and verified during release assembly.

## Package map

- `doctor.py`
- `doctor_packs/`
- `examples/doctor.config.toml`
- `examples/doctor.d/`
- `catalog_fetch.py`
- `physical_validation.py`
- `docs/CONDITION_PACK_SCHEMA.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `docs/UPSTREAM_COMPATIBILITY_CONTRACT.md`
- release documentation under `docs/`
- `tests/`
- `COMPATIBILITY_MATRIX.json`
- `LICENSE`

## Public contract lock

The release assembler reads `PUBLIC_CONTRACTS` from packaged `doctor.py` and verifies the
package against it:

- `condition-pack/v1`
- Patient Chart schema `2`
- `pwndoctor/status/v1`
- `pwndoctor/physical-validation/v1`
- `pwndoctor/provider/v1`

Assembly fails if required contract identifiers drift or the physical-validation recorder does
not match the runtime's declared validation contract.

## Generated integrity files

`RELEASE_MANIFEST.json` contains:
- release name/version;
- SHA-256 for every canonical packaged file;
- public contracts;
- per-pack id/version/hash/remedy inventory;
- compatibility-matrix path.

`SHA256SUMS` covers the assembled package.

Verification rejects missing/hash-mismatched files, duplicate/mismatched bundled pack ids,
contract drift, malformed compatibility matrix or target-version mismatch.

## Trust boundary

Do not package collaborator handoff notes, device-specific state, logs, secrets or unrelated
plugins. Catalog/provider runtime state is not release content.

## Promotion

The exact CI-produced archive is the physical-validation candidate. Stable `1.0.0` promotion
requires the exact archive to pass the guided checklist and produce a valid
`physical_validated` compatibility row.
