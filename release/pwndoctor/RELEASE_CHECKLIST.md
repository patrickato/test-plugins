# PwnDoctor release checklist

## Automated gate
- [ ] full repository test suite green on release commit
- [ ] Doctor-specific tests green
- [ ] Python syntax/import check green
- [ ] no stale version strings in config/docs
- [ ] bundled pack schema validation green
- [ ] release manifest/checksums generated from frozen files
- [ ] bundled Condition Pack inventory generated and verified (ids + hashes + duplicate check)
- [ ] compatibility matrix included; no physical-validation claim without completed hardware row

## Documentation gate
- [ ] README describes purpose and limits
- [ ] dependencies/system-command requirements documented
- [ ] current Jayofelony install path verified
- [ ] install/upgrade/rollback/uninstall documented
- [ ] all config settings explained
- [ ] safety/autonomy model explained
- [ ] Condition Pack trust boundary explained
- [ ] troubleshooting guide complete
- [ ] license included
- [ ] changelog/release notes prepared

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