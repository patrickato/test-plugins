# Using PwnDoctor v1

## 1. First boot

Install the package, copy/review the example config, and start in observation/dry-run mode.

Open the Doctor WebUI page after restart. Review:

- current status and plain-language summary;
- findings, confidence and outcome;
- treatment decision traces;
- Patient Chart coverage/recurrence;
- Doctor self-test/capability state;
- known-good drift when a checkpoint exists.

## 2. Standing Orders

Move from `observe` to `conservative` only after the device behaves as expected.

Use `confirm_required` for conditions you always want to approve manually and
`deny_actions` for actions Doctor must never execute.

## 3. Recovery posture

When Doctor sees questionable storage integrity (for example SD I/O errors/read-only root) or an
invalid-config crash loop, recovery posture activates. Automatic mutation is reduced to
confirmation. Explicit owner confirmation can still permit an otherwise-authorized action.

## 4. Remedy learning

Patient Chart records verified outcomes. Doctor can report per-device efficacy and rank candidate
remedies. Poor verified history never increases confidence; after the configured minimum history
it can force confirmation for a repeatedly ineffective remedy.

## 5. Known-good generations

Use the WebUI checkpoint action after the device is healthy. v1 keeps a bounded generation
history, while ordinary drift comparison still targets the newest checkpoint by default.

## 6. Condition Packs

- bundled `doctor_packs/`: first-party release knowledge;
- `/etc/pwnagotchi/doctor.d/`: owner/community packs, explain-only by default;
- cached catalog: always explain-only.

Author/test packs with the schema in `docs/CONDITION_PACK_SCHEMA.md`.
PwnDoctor's pure linter/simulator can evaluate pack structure and tri-state behavior without
executing a remedy.

## 7. Optional catalog fetch

Stage a pinned pack:

```bash
python3 catalog_fetch.py \
  https://example.invalid/pack.json \
  --sha256 <expected-64-hex-sha256> \
  --output-dir /var/lib/pwnagotchi/doctor/catalog.d
```

Then set `enable_cached_catalog = true`. The staged pack remains explain-only.

## 8. Specialist providers

Sibling plugins may publish bounded JSON snapshots into `/run/pwnagotchi/health.d/` using
`pwndoctor/provider/v1`. Doctor consumes only fresh snapshots. Core evidence wins over provider
evidence for the same canonical key, and provider findings cannot contain executable fixes.

## 9. Machine-readable local status

`Doctor.status_contract()` returns `pwndoctor/status/v1` for local integrations. It contains
bounded Doctor state, decision traces, Patient Chart summary, providers/catalog metadata,
recovery state, compatibility identity and self-test—but not raw logs, SSIDs, IPs or GPS data.

## 10. Support bundle

Use the WebUI support-bundle action for a sanitized ZIP containing report/config/log-tail/
incidents/Patient Chart/environment information. Inspect it before posting publicly.

## 11. Physical validation

Run `docs/PHYSICAL_VALIDATION.md` against the exact CI-tested archive. The included
`physical_validation.py` recorder saves progress and refuses to generate a
`physical_validated` matrix row until every required test passes.
