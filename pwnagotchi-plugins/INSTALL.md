# Installing test-plugins

Most files here are standard Jayofelony/Pwnagotchi custom plugins.

## Custom plugin directory

Current Jayofelony defaults normally use:

```toml
main.custom_plugins = "/etc/pwnagotchi/custom-plugins/"
```

## Ordinary single-file plugins

Copy the plugin `.py`, copy/review its `.config.toml` settings, then restart Pwnagotchi.

## PwnDoctor

PwnDoctor v1 is a multi-file release and should be installed from the assembled package rather
than by copying only `doctor.py`.

Build the standalone package from repository root:

```bash
python3 release/pwndoctor/build_release.py --output /tmp/pwndoctor-dist
```

Then from the generated `pwndoctor-<version>/` directory:

```bash
sudo ./install.sh
```

Review `examples/doctor.config.toml` and start with:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

Restart:

```bash
sudo systemctl restart pwnagotchi
```

The standalone package's `docs/INSTALL.md`, `docs/CONFIGURATION.md`,
`docs/USAGE.md` and `docs/PHYSICAL_VALIDATION.md` are the authoritative PwnDoctor
installation/release instructions.
