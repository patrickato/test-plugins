# PwnDoctor v1 RC readiness

## Candidate
`1.0.0-rc1`

## Software status

**Software feature work for the original v1 roadmap is complete.**

Included:
- v0.5 safety/ailment foundation;
- v0.6 Condition Packs, trust classes, Patient Chart, recurrence, policy and release foundation;
- v0.7 narrative/support bundle, treatment decision trace, Patient Chart v2 and per-device remedy
  efficacy safeguards;
- v0.8 deep pack lint/simulation, cached explain-only catalog, SHA-pinned opt-in fetch,
  provenance/signing identity contract and evidence-freshness contract;
- v0.9 specialist-provider hub, stable status contract, bounded known-good generations and
  root-cause/downstream-treatment suppression;
- v1 recovery posture, public-contract lock, self-test and guided physical-validation recorder.

## Automated gate

The final RC must have:
- full repository/Doctor pytest green;
- package assembly green;
- release manifest + SHA256SUMS verified;
- 12 bundled Condition Packs inventoried and verified;
- version == compatibility-matrix target;
- all public contracts consistent;
- CI-tested release archive preserved as an artifact.

## Physical gate

Physical compatibility remains pending until the exact CI archive is tested on the owner's real
Jayofelony/Pwnagotchi device.

Use `PHYSICAL_VALIDATION.md` and `physical_validation.py`.

The recorder must show every required check as `pass` before it can emit a
`physical_validated` matrix row.

## Stable v1 promotion

After exact-artifact physical validation:
1. add the generated `physical_validated` row to `COMPATIBILITY_MATRIX.json`;
2. set `physical_validation_pending` false for the validated release;
3. change runtime/release version `1.0.0-rc1` → `1.0.0` with no feature changes;
4. rebuild and run the complete automated gate;
5. publish/tag that validated source/archive/checksum.

No new feature work belongs between RC1 validation and stable v1 unless validation finds a defect.
