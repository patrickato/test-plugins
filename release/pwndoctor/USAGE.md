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

A finding can include:
- severity;
- evidence confidence;
- symptom;
- likely cause;
- outcome;
- suggested steps;
- an eligible remedy;
- causal relationship to another condition;
- Condition Pack provenance.

## Outcomes

Common outcomes include:
- `needs_user` — Doctor will explain but not act under current policy;
- `would_fix` — dry-run shows an eligible action;
- `awaiting_confirm` — owner confirmation is required;
- `fixed` — action ran and verification succeeded;
- `fix_failed` — action ran but verification proved the condition remains/fix failed;
- `executed_verification_unknown` — action ran but Doctor cannot prove success or failure;
- `blocked_guard` — a safety guard says acting is unsafe in the current context;
- `gave_up` — circuit-breaker budget was exhausted.

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

Use the WebUI checkpoint function after the device is healthy and configured the way you want. Doctor can later compare config hash, enabled plugins, package versions, kernel and OS to answer 'what changed since it worked?'

## Condition Packs

First-party bundled packs ship in `doctor_packs/`.

Your own/community JSON packs live in `/etc/pwnagotchi/doctor.d/` and are explain-only by default.

Use `CONDITION_PACK_SCHEMA.md` when authoring packs.

## When Doctor cannot verify

Treat `executed_verification_unknown` as unresolved evidence, not success. Check the associated probe manually or collect a support bundle once that feature lands.

## Recommended everyday mode

After first-run review and physical validation, `conservative` is the intended normal default: safe eligible remedies may run automatically, while riskier/blocked/confirm-required work remains under owner control.