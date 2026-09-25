# PwnDoctor v1 compatibility policy

## Target

PwnDoctor v1 targets the current Jayofelony Pwnagotchi custom-plugin API/image family used by
this project.

Current evidence for `1.0.0-rc1` is automated/off-Pi until a real-device validation row is
added.

## Evidence labels

- `ci_validated`
- `physical_validated`
- `community_reported`
- `unknown`
- `known_incompatible`

Unknown is not compatible-by-default.

## Compatibility fingerprint

Patient Chart/status uses a privacy-light fingerprint:
- Pwnagotchi version;
- Python version;
- architecture;
- kernel;
- OS id/version/build where available.

It excludes hostname, MAC, SSID, IP, GPS and owner identity.

## Optional capabilities

Pi/system commands and specialist providers are guarded. Missing optional evidence reduces
coverage rather than blocking plugin load.

## Public contracts locked for v1 RC

- `condition-pack/v1`
- Patient Chart schema 2
- `pwndoctor/status/v1`
- `pwndoctor/provider/v1`
- `pwndoctor/physical-validation/v1`

## Physical evidence

Stable v1 promotion requires the exact CI-tested RC archive to pass the physical checklist on a
named Pi/Jayofelony image. The guided recorder generates the candidate matrix row only when all
required checks pass.
