# PwnDoctor release checklist

## Automated gate  (verified on this commit — Claude, 2026-09-25)
- [x] full repository test suite green on release commit (357 passed)
- [x] Doctor-specific tests green (95)
- [x] Python syntax/import check green
- [x] no stale version strings in config/docs (all at 0.6.0-pre4)
- [x] bundled pack schema validation green (build assembles all 12 packs)
- [x] release manifest/checksums generated from frozen files
- [x] bundled Condition Pack inventory generated and verified (ids + hashes + duplicate check)
- [x] compatibility matrix included; no physical-validation claim without completed hardware row

## Documentation gate
- [ ] README describes purpose and limits
- [ ] dependencies/system-command requirements documented
- [ ] current Jayofelony install path verified
- [ ] install/upgrade/rollback/uninstall documented
- [ ] all config settings explained
- [ ] safety/autonomy model explained
- [ ] Condition Pack trust boundary explained
- [x] troubleshooting guide complete
- [x] license included
- [x] changelog/release notes prepared (CHANGELOG.md)
- [x] owner physical-validation runbook prepared (PHYSICAL_VALIDATION.md)

## Physical Pi gate
- [ ] clean install on target Jayofelony image
- [ ] plugin loads after reboot
- [ ] WebUI Doctor page opens
- [ ] observe mode produces sensible findings
- [ ] dry-run shows would-fix without mutation
- [ ] conservative safe action tested
- [ ] confirm-required hold + one-tap approval tested
- [ ] persistent circuit breaker survives restart
- [ ] Patient Chart survives reboot and avoids scan-by-scan writes
- [ ] known-good checkpoint save/diff tested
- [ ] bundled pack loads with expected provenance
- [ ] external pack remains explain-only by default
- [ ] malformed/oversized pack fails safely
- [ ] unavailable optional commands fail as unknown/unavailable, not crash

## Failure-injection gate
- [ ] service-down condition
- [ ] rfkill condition
- [ ] monitor-interface problem
- [ ] bad/invalid config case
- [ ] DNS/route distinction
- [ ] low-disk/log-bloat case
- [ ] read-only/media-error guard case
- [ ] verification evidence intentionally missing → verification unknown

## Release decision
- [ ] no unresolved critical/unsafe physical-test defects
- [ ] all known limitations listed
- [ ] final version/tag selected
- [ ] standalone repository/folder package assembled from frozen canonical files
- [ ] final archive checksum published