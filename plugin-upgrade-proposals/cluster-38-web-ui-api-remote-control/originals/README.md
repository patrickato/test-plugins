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
- `handshaker.py` - copied verbatim from
  `itsdarklikehell/pwnagotchi-plugins/handshaker.py` (an earlier,
  functionally-identical mirror also exists at
  `pwnagotchi-unofficial/plugins_archive/allordacia/Pwnagotchi-Handshaker/handshaker.py`,
  not separately preserved here) - rebuilt as `handshaker-suite`
  (`HandshakerNG`, file `handshaker_ng.py`). Its
  `reference-configs/handshaker.toml` entry was a genuine exact-match
  find (`itsdarklikehell/pwnagotchi-plugins/configs/handshaker.toml`),
  so there is no separate `handshaker.config.original.toml` copy here
  either - the real upstream sample is already preserved at that path.

See `../NOTES.md` for the full writeup of what was wrong with the
original and what the rebuild does differently.
