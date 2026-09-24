# PwnDoctor troubleshooting

## Doctor does not appear

Check:

```bash
grep -n "main.custom_plugins" /etc/pwnagotchi/config.toml
ls -l /etc/pwnagotchi/custom-plugins/doctor.py
grep -n "main.plugins.doctor" /etc/pwnagotchi/config.toml
sudo systemctl status pwnagotchi --no-pager
sudo tail -n 200 /etc/pwnagotchi/log/pwnagotchi.log | grep -i doctor
```

## Doctor loads but no bundled packs appear

Confirm `doctor_packs/` is beside `doctor.py` in the same custom-plugin directory.

## User pack is detected but does not auto-fix

That is the default security policy. External packs are explain-only unless `allow_pack_remedies = true`, and even then they may only use actions already compiled into Doctor.

## Doctor says verification unknown

This means the action ran but the evidence required to prove success/failure was unavailable. It is intentionally not reported as fixed.

## Doctor repeatedly tries the same repair

The persistent circuit breaker should stop repeated attempts after its budget. If it does not, preserve the breaker file and logs for a support bundle; that is a release-blocking defect.

## Device becomes unreachable after an action

Use local/USB access if possible, restore the prior plugin release/config backup, and capture the incident/breaker/Patient Chart files before deleting anything. Connectivity-affecting remedies should be placed behind confirm-required or stricter policy during RC testing.

## Read-only filesystem / SD errors

Do not repeatedly force writes. Preserve irreplaceable config/state to independent storage first and replace suspect media.