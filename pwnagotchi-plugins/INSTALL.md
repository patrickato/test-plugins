# Installing these plugins

These are standard Jayofelony/Pwnagotchi **custom plugins**. Each is a single `.py` file plus
an example `config.toml` block.

## 1. Put the plugin file in your custom-plugins directory
Find (or set) your custom plugins path in `/etc/pwnagotchi/config.toml`:

```toml
main.custom_plugins = "/etc/pwnagotchi/custom-plugins/"
```

Copy the plugin you want there, e.g.:

```bash
sudo mkdir -p /etc/pwnagotchi/custom-plugins/
sudo cp boot_post.py /etc/pwnagotchi/custom-plugins/
```

## 2. Add its config block
Open the plugin's `<name>.config.toml`, copy the block, and paste it into
`/etc/pwnagotchi/config.toml`. At minimum:

```toml
main.plugins.boot_post.enabled = true
```

Check the plugin's `Requires:` line first and install any pip/system/hardware deps it needs
(see the dependency table in `README.md`). Plugins with `Requires: none` run as-is.

## 3. Restart Pwnagotchi
```bash
sudo systemctl restart pwnagotchi
```

Watch the log to confirm it loaded:

```bash
sudo tail -f /etc/pwnagotchi/log/pwnagotchi.log | grep '\[<name>\]'
```

Web-facing plugins expose a page at `http://<pi>:8080/plugins/<name>/`.

## Notes
- Only enable a UI plugin's display element at a `position` that isn't already taken — run the
  `conflict_referee` plugin to catch position/GPIO collisions.
- Everything here is **source/CI-validated only**. Confirm display legibility, touch, and any
  real hardware on your own device before relying on a plugin in the field.
- Start with a no-hardware one (`boot_post`, `own_network_allowlist`, `streaks`) to get a feel
  for the install flow.
