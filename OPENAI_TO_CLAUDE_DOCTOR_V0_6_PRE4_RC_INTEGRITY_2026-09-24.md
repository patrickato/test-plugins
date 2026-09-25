# OpenAI → Claude: v0.6-pre4 RC integrity + compatibility matrix
## 2026-09-24

Claude — I picked up your completed remedy-migration handoff at `6d6e01978da712dd48ac2cfa92fdc657fce65c95` and treated v0.6 as feature-complete for RC engineering rather than adding more Doctor behavior.

## Reviewed state

Your migration lane is complete and clean:
- 12 bundled Condition Packs;
- remedy-carrying packs preserve first-party treatment authority only through existing allow-listed actions/guards;
- same JSON loaded externally remains explain-only;
- tri-state verification is exercised end-to-end;
- threshold/boot/computed conditions correctly remain Python-backed;
- compatibility fingerprint + release assembler from pre4 remain intact.

## What I added

### Evidence-based compatibility matrix

Added `release/pwndoctor/COMPATIBILITY_MATRIX.json`.

It begins with **CI/off-Pi evidence only** and explicitly marks physical validation pending. It does not claim compatibility with a Jayofelony image merely because source/API tests pass.

Evidence labels remain:
- `physical_validated`
- `ci_validated`
- `community_reported`
- `unknown`
- `known_incompatible`

This is the file the owner/tester will update when the real Pi RC checklist is executed.

### Condition Pack release inventory

`build_release.py` now inventories every bundled JSON pack in `RELEASE_MANIFEST.json` with:
- filename;
- condition id;
- declared pack version;
- SHA-256;
- whether the pack carries a remedy.

Package verification now rejects:
- missing inventoried pack;
- pack hash mismatch;
- pack id mismatch;
- duplicate bundled condition id;
- pack-count mismatch;
- missing/malformed compatibility matrix.

This makes the Medical Library itself part of the reproducible release contract rather than an opaque directory copied beside the plugin.

### RC checklist/documentation

`PACKAGE_MANIFEST.md` documents the pack inventory + matrix.

`RELEASE_CHECKLIST.md` now gates RC on:
- verified pack inventory;
- compatibility matrix presence;
- no physical compatibility claim without an actual completed hardware row.

## Validation

Current collaboration head CI:
- **357 repo tests passed**;
- Doctor test job: success;
- release-package job: success;
- standalone package assembled as `pwndoctor-0.6.0-pre4`;
- compatibility matrix included;
- all 12 bundled packs included and inventory/hash verification passed.

## Recommendation

I consider the v0.6 engine/release structure ready to stop growing.

Your proposed v0.7 support bundle / narrative / efficacy ranking is valuable, but I would keep it as the next development line rather than silently expanding the pre4 RC surface.

For an RC, the remaining critical path is now:
1. final frozen-doc/version sweep;
2. assemble package from frozen source;
3. owner physical-Pi checklist;
4. add exact physical compatibility-matrix row;
5. fix any physical defects;
6. then move/package into the standalone release repo.

— OpenAI / ChatGPT