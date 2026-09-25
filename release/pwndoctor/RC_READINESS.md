# PwnDoctor RC Readiness
## v0.7.0-pre1 collaboration checkpoint

Status: **implementation/release-structure ready for physical release-candidate validation**.

This does **not** claim physical compatibility yet.

## Automated evidence

- Claude's v0.7-pre1 source head completed green collaboration CI.
- 102 Doctor tests / 364 repository tests were green at the v0.7-pre1 handoff.
- Standalone package assembles as `pwndoctor-0.7.0-pre1`.
- Release manifest + SHA256SUMS are generated and verified.
- 12 first-party bundled Condition Packs are inventoried by id/version/hash.
- Duplicate/missing/hash-mismatched bundled packs fail package verification.
- Compatibility matrix targets `0.7.0-pre1` and explicitly marks physical validation pending.
- External/local user packs remain explain-only by default.
- Reproducible installer backs up existing Doctor files and does not edit `config.toml`.

## Current RC feature surface

v0.7.0-pre1 includes all v0.6-pre4 Doctor foundations plus:

- plain-language Doctor narrative;
- sanitized one-click support bundle;
- redaction of MACs, IPv4 addresses, emails and secret/location/identity configuration values;
- bounded support-log collection;
- configurable `support_dir` and `support_log_lines`.

Foundation retained:

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

## Collaboration rule

Claude and OpenAI retain separate implementation lanes. Release work integrates Claude's current green Doctor source without overwriting Claude's branch or silently changing runtime authority.

## Owner physical-validation gate

The next required evidence must come from a real Jayofelony/Pwnagotchi device using the exact tested v0.7.0-pre1 artifact.

Run `PHYSICAL_VALIDATION.md` / `RELEASE_CHECKLIST.md` and record:
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
17. missing verification evidence -> verification unknown;
18. narrative renders coherently;
19. sanitized support bundle is created and does not leak configured secrets/identifiers.

## Promotion rule

Only after those checks pass should `COMPATIBILITY_MATRIX.json` receive a `physical_validated` row for that exact hardware/image combination.

If a physical test fails, preserve the evidence, fix the defect in the appropriate collaborator lane, rebuild a new tested artifact, and repeat the failed checks.

## Release order

1. CI assembles + verifies the v0.7.0-pre1 package.
2. Physical validation runs on that exact artifact.
3. Any defect is fixed/rebuilt/retested.
4. Compatibility matrix + known limitations are updated.
5. Tag the validated source.
6. Publish the standalone release/archive with its checksum.
