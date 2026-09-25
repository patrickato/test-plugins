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

`disable_autofix = ["condition.id"]` blocks automatic treatment for named conditions while retaining diagnosis.

`confirm_required = ["condition.id"]` holds an otherwise-eligible action until the owner approves it from the Doctor WebUI. Held actions do not consume circuit-breaker budget.

`deny_actions = ["action_name"]` is an owner veto on specific actions. Doctor will still diagnose and explain, but never run denied actions.

`allow_reboot_actions = false` (default) holds reboot-class actions for confirmation even at `assertive`.

## Condition Packs

`condition_dir` defaults to `/etc/pwnagotchi/doctor.d` for user/community data-only packs.

`allow_pack_remedies = false` is the recommended default. External packs remain diagnostic/explanatory even if they name a known remedy.

First-party release packs live beside `doctor.py` in `doctor_packs/` and are treated as part of the reviewed release artifact. They still cannot create arbitrary new actions.

## Support bundle

v0.7 adds a sanitized support-bundle path for sharing useful diagnostic evidence without intentionally exporting sensitive device/network identity.

- `support_dir` — directory where generated support ZIP files are written.
- `support_log_lines` — bounded number of recent log lines included before redaction.

The bundle redacts configured secret/location/identity values and common MAC, IPv4 and email patterns. Inspect any bundle before sharing it publicly.

## Runtime state

- Patient Chart: `/var/lib/pwnagotchi/doctor/patient.json`
- incidents: configured by `incident_path`
- known-good checkpoint/history: configured by `checkpoint_path`
- `checkpoint_generations` — bounded number of known-good fingerprints retained (default 5,
  minimum 1, hard maximum 20); `load_checkpoint()` remains backward compatible and returns
  the current generation by default.
- persistent circuit breaker: configured by `breaker_path`

Runtime state is intentionally separate from first-party plugin files so upgrades do not erase the patient's history.

## Thresholds

v0.7 keeps config-tunable/computed thresholds in Python rather than turning Condition Pack v1 into a general programming language.

Current configurable examples include free-space, temperature, journald size and restart-loop thresholds.

## Service list

`services` controls which systemd units Doctor checks. The default targets Pwnagotchi, Bettercap and pwngrid-peer.
