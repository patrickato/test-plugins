# PwnDoctor v1 dependencies

## Runtime

PwnDoctor itself requires only:
- Jayofelony/Pwnagotchi custom-plugin support;
- the image's Python runtime;
- Python standard library.

No pip package is required by `doctor.py`.

## Optional system commands

Doctor probes/actions use commands only when present:

- `systemctl`
- `iw`
- `rfkill`
- `vcgencmd`
- `timedatectl`
- `journalctl`
- `dpkg`
- `uname`

Missing optional commands reduce coverage; they should not prevent Doctor from loading.

## Privileges

Read-only diagnosis can work with partial authority. Effectors such as service restart, rfkill,
journal vacuum or filesystem remediation require appropriate privileges. Pwnagotchi normally
runs plugins with sufficient system authority; Doctor still applies its own policy gates.

## Network

Core Doctor operation is offline-first and requires no network.

`catalog_fetch.py` is an optional manual utility. When invoked it requires HTTPS and a caller-
supplied SHA-256. Fetched packs enter the cached catalog trust class and remain explain-only.

## Storage

Recommended locations:
- runtime: custom-plugin directory;
- bundled packs: beside `doctor.py`;
- owner packs: `/etc/pwnagotchi/doctor.d/`;
- Patient Chart/support/cache: `/var/lib/pwnagotchi/doctor/`;
- provider snapshots: `/run/pwnagotchi/health.d/` (normally tmpfs).

Persistent writes are bounded/change-gated where practical.

## Development

CI reference: Python 3.13 with dependencies in
`pwnagotchi-plugins/requirements-dev.txt`.
