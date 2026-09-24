# Installing PwnDoctor

## Before you start

Back up `/etc/pwnagotchi/config.toml` before enabling any new plugin.

Current Jayofelony images use `/etc/pwnagotchi/custom-plugins/` as the canonical custom-plugin path, while the actual path is controlled by `main.custom_plugins` in `/etc/pwnagotchi/config.toml`.

## Manual install

1. Copy `doctor.py` into your configured custom-plugin directory.

```bash
sudo mkdir -p /etc/pwnagotchi/custom-plugins
sudo cp doctor.py /etc/pwnagotchi/custom-plugins/doctor.py
```

2. Copy first-party bundled Condition Packs next to the plugin:

```bash
sudo rm -rf /etc/pwnagotchi/custom-plugins/doctor_packs
sudo cp -a doctor_packs /etc/pwnagotchi/custom-plugins/doctor_packs
```

3. Create the optional local user-pack directory:

```bash
sudo mkdir -p /etc/pwnagotchi/doctor.d
```

4. Copy the example Doctor configuration into `/etc/pwnagotchi/config.toml` and review the autonomy settings before restart.

Start conservatively:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

After you have reviewed findings and confirmed expected behavior, move to `conservative` and disable dry-run if desired.

5. Restart Pwnagotchi:

```bash
sudo systemctl restart pwnagotchi
```

6. Watch the log:

```bash
sudo tail -f /etc/pwnagotchi/log/pwnagotchi.log | grep -i doctor
```

7. Open the plugin page in the Pwnagotchi WebUI under the Doctor plugin route.

## Upgrade

Before replacing an existing Doctor:

```bash
sudo cp -a /etc/pwnagotchi/custom-plugins/doctor.py /etc/pwnagotchi/custom-plugins/doctor.py.bak
sudo cp -a /etc/pwnagotchi/custom-plugins/doctor_packs /etc/pwnagotchi/custom-plugins/doctor_packs.bak 2>/dev/null || true
```

Then copy the new release files and restart Pwnagotchi.

Patient Chart, incidents, breaker state and known-good state are runtime data and should not be deleted during a normal upgrade.

## Roll back

Restore the previous `doctor.py` and matching `doctor_packs/` together. Do not mix a new runtime with an older first-party Medical Library unless the release notes explicitly say it is compatible.

## Uninstall

1. Set `main.plugins.doctor.enabled = false`.
2. Restart Pwnagotchi.
3. Remove `doctor.py` and `doctor_packs/` from the custom-plugin directory if desired.
4. Keep `/var/lib/pwnagotchi/doctor/` and `/etc/pwnagotchi/doctor*.json` if you may reinstall and want to retain Patient Chart/incident history; delete them only if you intentionally want a clean slate.

## Important

The RC package will include an installer helper, but it will **not** silently edit your main `config.toml`. Configuration remains an explicit owner action.