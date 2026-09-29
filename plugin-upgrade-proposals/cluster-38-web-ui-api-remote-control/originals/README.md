# Originals preserved before rebuilding in plugins-wip

These are exact, unmodified copies of source plugins that were rebuilt
in patrickato/plugins-wip, kept here specifically so the originals are
not lost if a rebuild needs to be abandoned/reverted for any reason.

- `web2ssh.py` - copied verbatim from `wpa-2/pwnagotchi-plugins/web2ssh.py`
  - rebuilt as `web2ssh-suite` (`Web2SSHNG`, file `web2ssh_ng.py`). No
  real upstream `config.toml`/`config.yaml` was found for this one
  anywhere (its `reference-configs/web2ssh.toml` entry was generated
  from a scan of the plugin's own `self.options` usage, not a real
  found sample - see `reference-configs/MANIFEST.md`), so there is no
  `web2ssh.config.original.toml` here.

See `../NOTES.md` for the full writeup of what was wrong with the
original and what the rebuild does differently.
