# PwnDoctor v1 configuration guide

Canonical settings live under `main.plugins.doctor.*` in
`/etc/pwnagotchi/config.toml`.

The package includes `examples/doctor.config.toml`, which is the complete reference.

## Recommended first-run profile

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

## Standing Orders

- `autofix = "off" | "observe" | "notify" | "conservative" | "assertive"`
- `dry_run`
- `disable_autofix = []`
- `confirm_required = []`
- `deny_actions = []`
- `allow_reboot_actions = false`

Low-confidence findings are never auto-treated. Recovery posture and poor verified remedy
history may require confirmation even when the autonomy level would otherwise allow an action.

## Learned remedy safeguards

```toml
main.plugins.doctor.efficacy_min_verified = 4
main.plugins.doctor.efficacy_hold_below = 0.25
```

After enough verified outcomes exist for this patient, a remedy whose verified success rate is
below the configured threshold is held for confirmation. History never grants additional
authority.

## Scanning and thresholds

```toml
main.plugins.doctor.scan_every = 30
main.plugins.doctor.boot_grace_s = 25
main.plugins.doctor.min_free_mb = 200
main.plugins.doctor.max_temp_c = 80
main.plugins.doctor.journal_max_mb = 200
main.plugins.doctor.journal_keep_mb = 100
main.plugins.doctor.restart_loop_threshold = 5
main.plugins.doctor.services = ["pwnagotchi", "bettercap", "pwngrid-peer"]
```

## Runtime paths

```toml
main.plugins.doctor.log_path = "/etc/pwnagotchi/log/pwnagotchi.log"
main.plugins.doctor.config_path = "/etc/pwnagotchi/config.toml"
main.plugins.doctor.handshakes = "/root/handshakes"
main.plugins.doctor.incident_path = "/etc/pwnagotchi/doctor_incidents.json"
main.plugins.doctor.breaker_path = "/etc/pwnagotchi/doctor_breaker.json"
main.plugins.doctor.patient_path = "/var/lib/pwnagotchi/doctor/patient.json"
main.plugins.doctor.checkpoint_path = "/etc/pwnagotchi/doctor_known_good.json"
main.plugins.doctor.checkpoint_generations = 5
```

Patient Chart v2 writes only on meaningful change. Known-good history is bounded to 1–20
generations.

## Condition Packs

```toml
main.plugins.doctor.condition_dir = "/etc/pwnagotchi/doctor.d"
main.plugins.doctor.allow_pack_remedies = false
```

External/local packs are explain-only by default. Even with explicit opt-in they may reference
only actions Doctor already compiles and allows.

## Cached catalog

```toml
main.plugins.doctor.catalog_dir = "/var/lib/pwnagotchi/doctor/catalog.d"
main.plugins.doctor.enable_cached_catalog = false
```

Cached catalog packs are **always explain-only**. Use the packaged `catalog_fetch.py` only when
you intentionally want to stage a SHA-pinned HTTPS pack.

## Specialist provider hub

```toml
main.plugins.doctor.provider_dir = "/run/pwnagotchi/health.d"
main.plugins.doctor.provider_max_age_s = 300
```

Provider snapshots use `pwndoctor/provider/v1`. They may contribute fresh canonical evidence
and explain-only findings; they cannot define remedies. Stale/future-dated snapshots are rejected.

## Support bundle

```toml
main.plugins.doctor.support_dir = "/var/lib/pwnagotchi/doctor"
main.plugins.doctor.support_log_lines = 400
```

The bundle redacts common MAC/IP/email patterns and configured secret/location/identity values.
Inspect any archive before sharing publicly.

## UI

```toml
main.plugins.doctor.position = "0,0"
```
