# Pwnagotchi Gap Plugins

Original plugins that fill real gaps in the Pwnagotchi ecosystem. See
[`BUILD_LIST.md`](BUILD_LIST.md) for the broader plugin roadmap.

## P06 — PwnDoctor

PwnDoctor is now at **v1.0.0-rc1** on the v1 release branch.

Primary files:
- `doctor.py`
- `doctor.config.toml` — complete v1 configuration reference
- `doctor_packs/` — bundled first-party Condition Packs
- `doctor.d/` — external-pack examples
- `CONDITION_PACK_SCHEMA.md`
- `DOCTOR_ROADMAP.md`
- `DOCTOR_COMPATIBILITY_CONTRACT.md`

The standalone release package is assembled from `release/pwndoctor/` and includes installer,
documentation, validation recorder, catalog-fetch utility, tests, manifest/checksums and
compatibility matrix.

PwnDoctor v1 is software-complete but remains **physical-validation pending** until the exact RC
artifact passes the real Jayofelony/Pi checklist.

## Layout

- `reference/` — upstream plugin API reference
- `templates/` — plugin templates
- `tests/` — off-Pi test harness
- `<name>.py` / `<name>.config.toml` — individual plugins

## Develop

```bash
pip install -r requirements-dev.txt
PYTHONPATH= python -m pytest -q
```

## Doctor dependencies

PwnDoctor itself requires no pip package. It conditionally uses standard system commands such as
`systemctl`, `iw`, `rfkill`, `vcgencmd`, `timedatectl`, `journalctl`, `dpkg` and
`uname`. Missing optional commands reduce coverage rather than preventing load.

## License

GPLv3.
