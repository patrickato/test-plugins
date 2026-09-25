# PwnDoctor changelog / release notes

Physical compatibility remains pending until a `physical_validated` row exists in
`COMPATIBILITY_MATRIX.json`.

## 1.0.0-rc1 — software-complete v1 release candidate

PwnDoctor now implements the complete software side of the original roadmap through v1.

### Diagnose / explain
- broad guarded local diagnostics;
- Condition Pack v1 Medical Library;
- tri-state detection/verification;
- causal chains + root/downstream suppression;
- plain-language narrative;
- treatment decision trace;
- self-test/capability map.

### Treat safely
- allow-listed actions;
- owner Standing Orders, opt-outs, action vetoes and confirmation tier;
- reboot gate;
- named safety guards;
- persistent circuit breaker;
- recovery posture for storage/config integrity problems;
- verify-or-report-unknown;
- learned remedy efficacy can only reduce autonomy to confirmation.

### Remember
- Patient Chart v2 with v1 migration and future-schema overwrite protection;
- chronic/recurrence episodes;
- bounded remedy history;
- bounded known-good generations + drift.

### Extend
- bundled / external / cached-catalog trust classes;
- deep Condition Pack lint + non-mutating simulation;
- provenance/signing identity contract with zero authority delta;
- evidence freshness contract;
- SHA-pinned optional HTTPS catalog fetch;
- `pwndoctor/provider/v1` read-only specialist hub;
- `pwndoctor/status/v1` local integration contract.

### Support / release
- sanitized support ZIP;
- reproducible installer/package assembler;
- per-pack manifest + SHA256SUMS;
- compatibility matrix;
- public-contract lock;
- guided physical-validation evidence recorder.

### Release status
Automated gate must be green for the final RC commit. Stable `1.0.0` remains blocked only on
exact-artifact physical validation and any defects that validation uncovers.

## 0.7.0-pre1
- plain-language narrative;
- sanitized support bundle.

## 0.6.0-pre4
- data-driven Condition Packs;
- Patient Chart;
- trust/policy/verification foundation;
- bundled-pack migration;
- reproducible release staging.

Earlier development history is preserved in `docs/DEVELOPMENT_ROADMAP.md`.
