# PwnDoctor v1 troubleshooting

## Doctor does not load

```bash
grep -n "main.custom_plugins" /etc/pwnagotchi/config.toml
ls -la /etc/pwnagotchi/custom-plugins/doctor.py
grep -n "main.plugins.doctor" /etc/pwnagotchi/config.toml
sudo systemctl status pwnagotchi --no-pager
sudo tail -n 250 /etc/pwnagotchi/log/pwnagotchi.log | grep -i doctor
```

Start with `autofix = "observe"` and `dry_run = true`.

## Bundled packs missing

`doctor_packs/` must sit beside `doctor.py`. Re-run `install.sh` from the assembled package.

## External pack diagnoses but does not treat

Expected by default. `/etc/pwnagotchi/doctor.d/` is explain-only unless the owner explicitly
sets `allow_pack_remedies = true`. Cached catalog packs remain explain-only regardless.

## Catalog pack does not load

Check:
- `enable_cached_catalog = true`;
- file exists in `catalog_dir`;
- JSON schema is `condition-pack/v1`;
- applicability/version gates match;
- Doctor page/logs for pack errors.

Use the linter/simulator before deployment.

## Provider snapshot ignored

Provider JSON must:
- use `pwndoctor/provider/v1`;
- have a valid namespaced id;
- have an `observed_at` timestamp within `provider_max_age_s`;
- fit size/count bounds.

Stale/future-dated providers are rejected intentionally.

## Action says awaiting confirmation unexpectedly

Possible reasons include:
- `confirm_required`;
- reboot-class action gate;
- recovery posture;
- poor verified per-device remedy efficacy.

Read the finding's treatment decision trace for the exact gate/reason.

## Downstream finding remains but is not auto-treated

Root-cause suppression may be active. Doctor still diagnoses the symptom but avoids redundant
automatic treatment while a more fundamental active cause explains it.

## Recovery mode is active

Common triggers:
- SD/media I/O errors;
- root filesystem read-only;
- invalid config plus crash/restart-loop evidence.

Preserve data first. Mutations require explicit owner confirmation.

## Verification unknown

The action ran but Doctor could not prove success or failure. Unknown is deliberately not
reported as fixed.

## Patient Chart reports a newer schema

Do not delete it merely to silence the warning. An older Doctor intentionally leaves a future
chart read-only. Upgrade Doctor or restore the matching newer runtime.

## Support request

Generate the sanitized support bundle from the Doctor page and inspect it before sharing. Keep
the exact release version, compatibility fingerprint and physical-validation record with reports.
