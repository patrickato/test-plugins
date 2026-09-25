# PwnDoctor v1 release checklist

## Software / automated gate
- [x] original roadmap feature implementation complete through v1 RC
- [x] Condition Pack v1 + bundled/external/catalog trust classes
- [x] Patient Chart v2 migration + future-schema protection
- [x] treatment decision trace
- [x] persistent circuit breaker + guards + owner Standing Orders
- [x] remedy efficacy safeguards (history can only reduce autonomy)
- [x] root-cause/downstream-treatment suppression
- [x] recovery posture
- [x] cached catalog + pinned optional fetch; catalog explain-only
- [x] specialist provider hub; providers read-only/explain-only
- [x] stable status contract + self-test
- [x] known-good generation history
- [x] support bundle + redaction
- [x] guided physical-validation recorder
- [x] public-contract release lock
- [ ] final v1.0.0-rc1 cumulative CI run green
- [ ] exact final CI artifact downloaded/checksum independently verified

## Documentation/package gate
- [x] complete example `doctor.config.toml`
- [x] install/upgrade/rollback/uninstall
- [x] configuration guide
- [x] usage guide
- [x] security/trust model
- [x] dependencies
- [x] troubleshooting
- [x] compatibility policy/matrix
- [x] Condition Pack schema
- [x] development roadmap
- [x] physical-validation instructions
- [x] package manifest
- [x] license

## Physical Jayofelony/Pi gate
- [ ] clean install + reboot load
- [ ] Doctor WebUI opens
- [ ] observe mode
- [ ] dry-run
- [ ] safe verified remedy
- [ ] confirm-required flow
- [ ] circuit breaker survives restart
- [ ] Patient Chart v2 persistence/migration behavior
- [ ] known-good save/diff/history
- [ ] bundled provenance
- [ ] external/catalog explain-only boundaries
- [ ] malformed/oversized pack failure
- [ ] provider stale/invalid failure
- [ ] missing optional commands safe degradation
- [ ] radio/monitor failure diagnosis
- [ ] invalid config/recovery posture
- [ ] read-only/media guard/recovery posture
- [ ] verification unknown case
- [ ] narrative/support bundle/self-test
- [ ] sanitized support archive manually inspected

## Stable release
- [ ] validation record reports all required checks pass
- [ ] `physical_validated` compatibility row added
- [ ] stable version changed to `1.0.0` with no feature delta
- [ ] stable build/test/package gate green
- [ ] stable archive checksum published
