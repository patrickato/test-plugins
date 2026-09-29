# Originals preserved before rebuilding in plugins-wip

These are exact, unmodified copies of source plugins that were rebuilt
in patrickato/plugins-wip, kept here specifically so the originals are
not lost if a rebuild needs to be abandoned/reverted for any reason.

- `blemon_plugin.py` - copied verbatim from `itsdarklikehell/pwnagotchi-plugins/blemon_plugin.py` - merged with `bluetoothsniffer.py` into `bluetooth-recon-suite` (`BluetoothReconNG`)
- `blemon_plugin.config.original.toml` - its real upstream config, copied verbatim from `itsdarklikehell/pwnagotchi-plugins/configs/blemon_plugin.toml`
- `bluetoothsniffer.py` - copied verbatim from `itsdarklikehell/pwnagotchi-plugins/bluetoothsniffer.py` - merged with `blemon_plugin.py` into `bluetooth-recon-suite` (`BluetoothReconNG`)
- `bluetoothsniffer.config.original.toml` - its real upstream config, copied verbatim from `itsdarklikehell/pwnagotchi-plugins/configs/bluetoothsniffer.toml`
- `mad_hatter.py` - copied verbatim from `alienmajik/pwnagotchi_plugins/mad_hatter.py` - rebuilt as `mad-hatter-suite` (`MadHatterNG`, file `MadHatterNG.py`). No real upstream `config.toml`/`config.yaml` was found for this one anywhere (its `reference-configs/mad_hatter.toml` entry is machine-generated from the plugin's own `__defaults__` dict, not a real found sample - see `reference-configs/MANIFEST.md`), so there is no `mad_hatter.config.original.toml` here.
- `fix_region.py` - copied verbatim from `itsdarklikehell/pwnagotchi-plugins/fix_region.py` - fixed and rebuilt as `fix-region-suite` (`FixRegionNG`, file `fix_region_ng.py`).
- `fix_region.config.original.toml` - its real upstream config, copied verbatim from `itsdarklikehell/pwnagotchi-plugins/configs/fix_region.toml`.
- `sigstr.py` - copied verbatim from `bryzz42o/Pwnagotchi-fsociety-plugins/sigstr.py` (v1.0.6) - fixed and rebuilt as `sigstr-suite` (`SigStrNG`, file `sigstr_ng.py`). No real upstream `config.toml`/`config.yaml` was found for this one anywhere, so there is no `sigstr.config.original.toml` here.

See `../NOTES.md` for the full writeup of what was wrong with each original
and what the rebuilds do differently.
