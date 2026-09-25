# Using PwnDoctor

## First run

For a new installation, start in observation/dry-run mode:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

Restart Pwnagotchi, open Doctor in the WebUI, and review what it sees.

## Status vocabulary

- `OK` — no current actionable finding;
- `HEALED` — Doctor verified at least one repair and no remaining issue outranks it;
- `ATTENTION` — informational condition remains;
- `DEGRADED` — warning-level condition remains;
- `ACTION_REQUIRED` — high-severity or otherwise unresolved condition requires attention.

## What a finding shows

A finding can include severity, evidence confidence, symptom, likely cause, outcome, suggested steps, an eligible remedy, causal relationships and Condition Pack provenance.

## Outcomes

Common outcomes include:
- `needs_user`;
- `would_fix`;
- `awaiting_confirm`;
- `fixed`;
- `fix_failed`;
- `executed_verification_unknown`;
- `blocked_guard`;
- `gave_up`.

## Standing Orders

`autofix` controls the broad autonomy ceiling.

`disable_autofix` blocks named conditions from automatic treatment.

`confirm_required` lets you require one-tap approval for selected conditions even when the action would otherwise be eligible.

These policies are intentionally independent from the Medical Library. A condition knowing a remedy does not mean it may execute it.

## Patient Chart

The Patient Chart remembers this device rather than storing every raw log:
- hardware/build identity;
- diagnostic coverage;
- known-good summary;
- recurring condition episodes;
- verified remedy outcomes.

A condition that remains active across many scans counts as one episode. It becomes recurrent only after clearing and returning.

## Known-good checkpoint

Use the WebUI checkpoint function after the device is healthy and configured the way you want. Doctor can later compare config hash, enabled plugins, package versions, kernel and OS to answer “what changed since it worked?”

## Narrative summary

v0.7 adds a plain-language summary that combines current status, auto-fixes, unresolved work, likely causal chain and known-good drift into one readable paragraph.

## Sanitized support bundle

Use the Doctor support-bundle action when you need a forum/shareable diagnostic package. It includes a report, redacted configuration, redacted bounded log tail, incidents, Patient Chart summary and environment/drift information.

Redaction targets MAC addresses, IPv4 addresses, email addresses, secrets/tokens, SSID/BSSID/GPS and other configured identity/location values. Treat the ZIP as diagnostic data and inspect it before sharing publicly.

## Condition Packs

First-party bundled packs ship in `doctor_packs/`.

Your own/community JSON packs live in `/etc/pwnagotchi/doctor.d/` and are explain-only by default.

Use `CONDITION_PACK_SCHEMA.md` when authoring packs.

## When Doctor cannot verify

Treat `executed_verification_unknown` as unresolved evidence, not success. Check the associated probe manually or include the event in a sanitized support bundle.

## Recommended everyday mode

After first-run review and physical validation, `conservative` is the intended normal default: safe eligible remedies may run automatically, while riskier/blocked/confirm-required work remains under owner control.


## Machine-readable local status

`Doctor.status_contract()` returns the stable `pwndoctor/status/v1` read-only contract for
local sibling plugins, dashboards and Beastagotchi integration. It intentionally exposes Doctor
status, bounded finding summaries, decision traces, Patient Chart summary, pack counts,
known-good generation metadata and compatibility identity — not raw logs, SSIDs, IP addresses,
GPS coordinates or captured network data.

## Known-good generations

Doctor retains a bounded history of known-good fingerprints. The existing
`load_checkpoint()`/diff behavior still targets the newest checkpoint by default; older
generations can be selected for comparison without changing the current checkpoint.
