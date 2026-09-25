# OpenAI → Claude: PwnDoctor v0.6-pre4 RC handoff

Status: **software/release work complete for this RC; physical validation is the only remaining release gate.**

Claude's branch has been fast-forwarded to the finished collaboration state that was previously on `openai/pwndoctor-v0.6-collab`.

## Included in this handoff

- all Claude v0.6-pre4 implementation work;
- Condition Pack v1 + bundled/external trust separation;
- tri-state detect/verify semantics;
- remedy/action guard and Standing Orders behavior;
- persistent circuit breaker;
- Patient Chart identity, coverage, recurrence and remedy history;
- compatibility fingerprint + compatibility contract;
- known-good checkpoint/drift;
- 12 bundled declarative condition packs;
- reproducible standalone package assembler;
- package manifest + SHA256SUMS verification;
- compatibility matrix;
- installer/configuration/usage/security/troubleshooting/release docs;
- hardened CI and RC-readiness checks.

## Verification

The collaboration head `0505e838b4d91067b5d478f6568bab75b55218e9` passed the PwnDoctor collaboration workflow. Release assembly and integrity verification are green.

No known Claude work is missing from this branch.

## Freeze rule

Do not add v0.7 features to this RC unless a real-device validation defect requires a fix.

## Only remaining gate

Run `release/pwndoctor/RELEASE_CHECKLIST.md` against the exact assembled artifact on the owner's real Jayofelony/Pwnagotchi Pi.

Until that happens, compatibility remains correctly labeled as CI-validated / physical-validation-pending.

After a successful physical pass:
1. update `COMPATIBILITY_MATRIX.json` for that exact hardware/image;
2. rebuild/verify if any source changed;
3. freeze/tag the validated release;
4. then create/publish the standalone PwnDoctor repository/release artifact.

This RC is handed back to Claude as **implementation-complete, release-engineering-complete, physical-validation-pending**.
