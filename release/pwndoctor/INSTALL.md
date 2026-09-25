# Installing PwnDoctor v1

## Recommended install

1. Back up your Pwnagotchi config:

```bash
sudo cp -a /etc/pwnagotchi/config.toml /etc/pwnagotchi/config.toml.before-pwndoctor
```

2. Extract the exact PwnDoctor release archive.

3. Run the conservative installer from the extracted directory:

```bash
sudo ./install.sh
```

The installer:
- installs `doctor.py` and bundled `doctor_packs/`;
- backs up an existing Doctor runtime/packs with a timestamp;
- creates required Doctor state directories;
- **does not edit** `/etc/pwnagotchi/config.toml`.

4. Review `examples/doctor.config.toml`. For a first run, add at least:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

5. Restart Pwnagotchi:

```bash
sudo systemctl restart pwnagotchi
```

6. Verify load:

```bash
sudo systemctl status pwnagotchi --no-pager
sudo tail -n 250 /etc/pwnagotchi/log/pwnagotchi.log | grep -i doctor
```

7. Open the Doctor WebUI page and review status, findings and self-test.

## Install paths

Default Jayofelony custom-plugin path:

`/etc/pwnagotchi/custom-plugins/`

The actual path is controlled by `main.custom_plugins`. To override the installer destination:

```bash
sudo PWN_CUSTOM_PLUGINS=/your/custom/path ./install.sh
```

Runtime state defaults:

- Patient Chart: `/var/lib/pwnagotchi/doctor/patient.json`
- support bundles/catalog cache: `/var/lib/pwnagotchi/doctor/`
- owner Condition Packs: `/etc/pwnagotchi/doctor.d/`
- provider snapshots: `/run/pwnagotchi/health.d/`
- incidents/breaker/known-good state: configured paths in `doctor.config.toml`

## Upgrade

Run the newer release's `install.sh`. Existing runtime and first-party pack files are backed up.
Patient Chart v1 migrates to v2 automatically. A Doctor that encounters a Patient Chart schema
newer than it understands leaves that chart read-only instead of overwriting it.

## Rollback

Restore the timestamped `doctor.py.bak-*` and matching `doctor_packs.bak-*` together, then
restart Pwnagotchi.

Do not intentionally downgrade Patient Chart data. If rollback encounters a newer chart schema,
the older runtime should refuse to overwrite it.

## Uninstall

1. Set `main.plugins.doctor.enabled = false`.
2. Restart Pwnagotchi.
3. Remove `doctor.py` and `doctor_packs/` if desired.
4. Keep Doctor state if you may reinstall. Delete it only when you intentionally want a fresh
   patient/history.

## After install

Keep `observe + dry_run` until you have reviewed the device. Then follow
`docs/PHYSICAL_VALIDATION.md` before promoting the exact RC artifact to stable v1.
