# PwnDoctor configuration guide

Canonical settings live under `main.plugins.doctor.*` in `/etc/pwnagotchi/config.toml`.

## Recommended first-run profile

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
main.plugins.doctor.disable_autofix = []
main.plugins.doctor.confirm_required = []
```

Run this way first, inspect findings, then choose your Standing Orders.

## Autonomy

- `off` — no acting;
- `observe` — diagnose/explain only;
- `notify` — currently observation semantics, reserved for notification integration;
- `conservative` — allow safe fixes under all other gates;
- `assertive` — permit riskier allow-listed fixes too;
- legacy `safe` maps to `conservative`; legacy `all` maps to `assertive`.

`dry_run = true` prevents mutation while showing what Doctor would do.

`disable_autofix = ["condition.id"]` permanently blocks auto-treatment for named conditions while retaining diagnosis.

`confirm_required = ["condition.id"]` holds an otherwise-eligible action until the owner approves it from the Doctor WebUI. Held actions do not consume circuit-breaker budget.

## Condition Packs

`condition_dir` defaults to `/etc/pwnagotchi/doctor.d` for user/community data-only packs.

`allow_pack_remedies = false` is the recommended default. External packs remain diagnostic/explanatory even if they name a known remedy.

First-party release packs live beside `doctor.py` in `doctor_packs/` and are treated as part of the reviewed release artifact. They still cannot create arbitrary new actions.

## Runtime state

- Patient Chart: `/var/lib/pwnagotchi/doctor/patient.json`
- incidents: configured by `incident_path`
- known-good checkpoint: configured by `checkpoint_path`
- persistent circuit breaker: configured by `breaker_path`

Runtime state is intentionally separate from the first-party plugin files so upgrades do not erase the patient's history.

## Thresholds

v0.6 deliberately keeps config-tunable/computed thresholds in Python rather than adding generic parameter substitution to Condition Pack v1. This keeps the public schema small and understandable.

Current configurable examples include free-space, temperature, journald size and restart-loop thresholds.

## Service list

`services` controls which systemd units Doctor checks. The default targets Pwnagotchi, Bettercap and pwngrid-peer.