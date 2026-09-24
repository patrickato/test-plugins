# PwnDoctor dependencies and requirements

## Required

- A Jayofelony/Pwnagotchi installation with custom-plugin loading enabled.
- Python runtime provided by the Pwnagotchi image.
- No additional pip package is required by `doctor.py` itself.

## System commands Doctor may use

Doctor probes/actions call system tools only when available. Missing tools should reduce diagnostic coverage rather than prevent the plugin from loading.

- `systemctl` — service state/restart counters/actions;
- `iw` — monitor-interface evidence;
- `rfkill` — wireless block evidence/remedy;
- `vcgencmd` — Raspberry Pi power/throttle evidence when available;
- `timedatectl` — clock/NTP evidence/remedy;
- `journalctl` — journal usage and bounded vacuum action;
- `dpkg` — known-good package fingerprint;
- standard Linux `/proc`, `/sys`, filesystem and socket interfaces.

On current Jayofelony images these are generally present as part of the OS/Pwnagotchi stack. PwnDoctor does not install missing packages automatically.

## Privileges

Pwnagotchi normally runs with privileges sufficient for its own service/radio management. Read-only diagnosis can function with less authority, but guarded effectors such as service restart, rfkill changes or journal vacuum require appropriate system privileges.

## Network

No network connection is required for core Doctor operation or first-party Condition Packs.

Some probes distinguish default-route/DNS state. Those probes are diagnostic; PwnDoctor does not require Internet connectivity to load.

## Hardware

No extra hardware is required for Doctor.

Pi-specific evidence sources are optional. The plugin is designed to tolerate absent `vcgencmd`, missing display hardware, unavailable radio probes and similar partial coverage.

## Storage

Recommended writable locations:
- custom plugin: `/etc/pwnagotchi/custom-plugins/doctor.py`;
- first-party packs: `/etc/pwnagotchi/custom-plugins/doctor_packs/`;
- user packs: `/etc/pwnagotchi/doctor.d/`;
- Patient Chart: `/var/lib/pwnagotchi/doctor/patient.json`.

Patient Chart persistence is change-gated to avoid unnecessary SD writes.

## Development/test requirements

For off-Pi development in this repository:
- Python 3.13 is the CI reference;
- `pytest` and Pillow are installed from `pwnagotchi-plugins/requirements-dev.txt`;
- the fake Pwnagotchi harness under `pwnagotchi-plugins/tests/` supplies the plugin API surface used by tests.