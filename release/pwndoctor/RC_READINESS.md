# PwnDoctor RC Readiness
## v0.6.0-pre4 collaboration checkpoint

Status: **code/release-structure ready for physical release-candidate validation**.

This does **not** claim physical compatibility yet.

## Automated evidence

- Doctor engine/pack tests green in CI.
- Full test-plugins suite green.
- Standalone package assembled by CI.
- Release manifest + SHA256SUMS generated and verified.
- 12 first-party bundled Condition Packs inventoried by id/version/hash.
- Duplicate/missing/hash-mismatched bundled packs fail package verification.
- Compatibility matrix included and explicitly marks physical validation pending.
- External/local user packs remain explain-only by default.
- Reproducible installer backs up existing Doctor files and does not edit config.toml.

## Feature surface frozen for this RC

v0.6-pre4 includes:
- Condition Pack v1 loader/schema;
- bundled vs external trust classes;
- tri-state detect/verify truth;
- allow-listed actions/guards;
- autonomy/Standing Orders;
- deny-actions + reboot gate;
- confirm-required treatment flow;
- persistent circuit breaker;
- Patient Chart identity/coverage/recurrence/remedy history;
- compatibility fingerprint;
- known-good checkpoint/drift;
- 12 bundled declarative conditions;
- remaining threshold/boot/computed conditions in Python;
- WebUI Doctor surface;
- reproducible release package.

Do not add v0.7 support-bundle/narrative/ranking features to this RC unless a physical-validation defect requires a change.

## Owner physical-validation gate

The next required evidence must come from a real Jayofelony/Pwnagotchi device.

Run the release checklist against the exact tested package artifact and record:
- Pi model;
- Jayofelony/Pwnagotchi version/image identifier;
- Python version;
- kernel;
- OS build/image id where available;
- pass/fail notes for each physical checklist item.

At minimum validate:
1. clean install + reboot load;
2. Doctor WebUI opens;
3. observe mode;
4. dry-run;
5. one safe automatic remedy;
6. confirm-required hold/approve flow;
7. circuit breaker survives restart;
8. Patient Chart persists without scan-by-scan writes;
9. known-good checkpoint save/diff;
10. bundled pack provenance;
11. external pack explain-only default;
12. malformed/oversized pack safe failure;
13. unavailable optional command safe degradation;
14. radio/monitor failure case;
15. invalid config case;
16. read-only/media guard case;
17. missing verification evidence -> verification unknown.

## Promotion rule

Only after those checks pass should `COMPATIBILITY_MATRIX.json` receive a `physical_validated` row for that exact hardware/image combination.

Physical validation failure is not a reason to hide or soften the evidence label. Fix the defect, rebuild a new tested artifact, repeat the failed checks, and preserve the previous result.

## Standalone repository move

Do not move/publish the final standalone repo merely because the source looks complete.

Recommended order:
1. freeze the RC commit;
2. CI assembles + verifies package;
3. physical validation on the exact artifact;
4. fix/rebuild/retest if needed;
5. update compatibility matrix + known limitations;
6. create the standalone repository from the frozen tested package/source;
7. tag/release with published archive checksum.