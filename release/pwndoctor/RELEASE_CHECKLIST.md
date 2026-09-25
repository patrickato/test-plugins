# PwnDoctor release checklist

## Automated gate — v0.7.0-pre1
- [x] Claude v0.7-pre1 source head green in collaboration CI
- [x] full repository suite green at handoff (364 passed)
- [x] Doctor-specific tests green at handoff (102)
- [x] Python syntax/import checks green
- [x] bundled pack schema validation green (12 bundled packs)
- [x] release manifest/checksums generated from canonical files
- [x] bundled Condition Pack inventory generated and verified (ids + hashes + duplicate check)
- [x] compatibility matrix targets v0.7.0-pre1 and makes no physical-validation claim
- [ ] OpenAI v0.7 release branch CI green on final release-document commit

## Documentation gate
- [x] README describes purpose and limits
- [x] dependencies/system-command requirements documented
- [ ] current Jayofelony install path physically verified on target image
- [x] install/upgrade/rollback/uninstall documented
- [x] all current config settings explained
- [x] safety/autonomy model explained
- [x] Condition Pack trust boundary explained
- [x] sanitized support bundle documented
- [x] troubleshooting guide complete
- [x] license included
- [x] changelog/release notes prepared
- [x] owner physical-validation runbook prepared

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
- [ ] narrative summary renders coherently
- [ ] sanitized support bundle generated and inspected for redaction

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
- [x] release-candidate version selected: 0.7.0-pre1
- [x] standalone package assembler targets canonical source
- [ ] exact CI-tested artifact physically validated
- [ ] compatibility matrix updated with physical_validated row
- [ ] final tag created from validated source
- [ ] final archive checksum published
