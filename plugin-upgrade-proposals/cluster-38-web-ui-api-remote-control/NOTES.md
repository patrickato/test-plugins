# Cluster 38 - Web UI / API / Remote control

Status: **IN PROGRESS** - 1 removed, being worked through the
remaining 7 in groups of 5 per the user's request.

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, "## Web UI / API /
Remote control" section, Group 60 in the elimination log.

## Excluded from this cluster (already handled elsewhere)

- `cmd_server.py` / `webcfg_ng.py` - see Cluster 24
- `wpa-sec-list.py` / `wpa-sec_ng.py` - see Cluster 26

## Record-only, no action needed (not found anywhere in this environment)

- `pwmenu` - mobile-first field console for captures/cracking/exports/whitelists
- `pwnagotchi-http-module` - serves handshake pcaps via HTTP (targets the Bookworm image)
- `Pwny-WG` - WireGuard VPN + handshake sync over SSH; only a `README.md`
  exists in this environment (`wpa-2/pwnagotchi-plugins/Pwny-WG/`), no
  actual plugin script anywhere

## Removed at the user's request (1)

- **pwnwatch.py** - meant to receive commands from a companion
  "pwnagotchi-watch" app and report session stats. `on_webhook`
  references `self.ready`, which is never set anywhere in the class -
  a guaranteed `AttributeError` on the very first webhook call. Its one
  real response path (`Response(str(self.handshakes), ...)`) is built
  but the return value is discarded (no `return` statement) - execution
  falls through to `abort(404)` regardless, so even before the crash
  bug the plugin never actually served anything. `parseSessionStats`
  depends on an unrelated, unreviewed "session-stats" plugin's
  `save_directory` config key being present - an undeclared hard
  dependency. Despite the plugin's stated purpose ("receive commands
  from pwnagotchi-watch"), there is no command-parsing or dispatch
  logic anywhere in the file at all - only session-stats file reading.

## Still pending decisions - working through in groups of 5

Full findings for all 7 remaining plugins were presented to the user
in this session's findings table. Being decided in two groups:

**Group 1 (first 5):** `web2ssh.py`, `pwnmothership.py`,
`state-api.py`, `Pwny-Tailscale` (`tailscale.py`), `httpserver.py`.

**Group 2 (remaining 2):** `pwnmenu.py`/`pwnmenucmd.py`,
`handshaker.py`.

Key findings, summarized (see this session's findings table for full
detail):

- **web2ssh.py** - flagged as the top security priority in this whole
  audit: `Flask.run()` blocks `on_loaded()` forever (device-hanging
  bug, same class as httpserver.py/pwnmenu.py below); its own
  config-reading logic never actually receives real config data at
  all, so the username/password/port a user sets in `config.toml` are
  silently ignored and it always falls back to the hardcoded default
  `changeme`/`changeme` guarding **arbitrary root shell command
  execution** (`shell=True`, one-click shutdown/reboot buttons built
  in) over plaintext HTTP Basic Auth.
- **pwnmothership.py** / **state-api.py** - near-identical code
  lineage, same purpose (expose live pwnagotchi status as JSON for
  external tools/dashboards), same real bug: an unguarded
  `for peer in peers_response:` crashes with `TypeError` whenever the
  local mesh-peers API call fails, since `peers_response` stays `None`
  on failure. Flagged as a natural merge candidate.
- **Pwny-Tailscale** (`tailscale.py`) - the best-engineered plugin in
  this batch (retry logic, config validation, a real webhook status
  page) but `self.last_sync_time` is only set if `on_loaded()`
  completes successfully; if it returns early (missing required
  option, missing `tailscale`/`rsync` binary), the webhook status page
  crashes with `AttributeError` - exactly when a misconfigured user
  would go looking for what's wrong. Connection retries also block the
  main loop for up to ~45-60s on failure.
- **httpserver.py** - `self.httpd.serve_forever()` called directly in
  `on_loaded()` - blocks forever, hangs the whole device at startup;
  its request-handler subclass also has a broken `__init__` signature
  that would crash on every request even if the hang were fixed; no
  auth, serves the handshakes folder to the whole network.
- **pwnmenu.py** / **pwnmenucmd.py** - `on_loaded()` blocks forever on
  a socket `.accept()` loop (same device-hanging class of bug); reads
  a hardcoded file path at module IMPORT time with no guard; only
  functions on `displayhatmini` hardware (not the user's MPI3501
  touchscreen); the companion CLI script calls `logging.info(...)`
  without ever importing `logging`.
- **handshaker.py** - `on_loaded()` calls `self.load_data(...)`, a
  method that is never defined anywhere in the class - guaranteed
  `AttributeError` on every load; its webhook (the plugin's entire
  "access info without SSH" purpose) is a no-op.

## Related

Not yet identified: whether any merges beyond
pwnmothership.py/state-api.py make sense across this cluster - the
deferred post-all-clusters review task will also revisit this.
