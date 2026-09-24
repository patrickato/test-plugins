# PwnDoctor compatibility policy

## Target

PwnDoctor targets the current Jayofelony Pwnagotchi plugin API and image family used by this project.

Current development evidence is:
- source/API review against Jayofelony upstream;
- Python 3.13 automated test harness;
- CI/off-Pi behavior tests.

Physical compatibility is not claimed until the release checklist has been executed on real hardware.

## Custom-plugin path

Current Jayofelony defaults create and use `/etc/pwnagotchi/custom-plugins/`, controlled by `main.custom_plugins`.

## Portability

Collectors are individually guarded. Pi-specific tools such as `vcgencmd` are optional evidence sources rather than assumptions that must exist for Doctor to load.

## Upstream changes

Future Jayofelony releases may change Python APIs, service layout, image files, kernel/firmware or update behavior. A future compatibility-pack/fingerprint system is planned so Doctor can identify known vs unknown upstream environments rather than blindly assuming compatibility.

## Evidence labels

Release documentation should distinguish:
- CI/off-Pi tested;
- physically tested on a named Pi/image;
- community reported;
- unknown/unverified.