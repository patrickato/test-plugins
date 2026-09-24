# Pwnagotchi plugin API — the rules we follow

Distilled from the copied upstream source in this folder. When in doubt, read the actual
files here rather than guessing.

## Anatomy of a plugin
- A plugin is **one `.py` file** whose name is the plugin name (e.g. `sd_wear.py` → `sd_wear`).
- It defines exactly one class subclassing `pwnagotchi.plugins.Plugin`.
- Class-level metadata strings (parsed statically, so keep them literal):
  ```python
  __author__ = 'name <email or url>'
  __version__ = '0.1.0'
  __license__ = 'GPL3'
  __description__ = 'One line describing the plugin.'
  ```
- Config arrives as `self.options` (a dict) populated from
  `main.plugins.<name>.*` in `/etc/pwnagotchi/config.toml`. Always read options with
  `.get(key, default)` and validate — the user may omit or mistype them.
- Define `def __init__(self): self.options = dict()` so the instance is valid before load.

## Lifecycle & threading (important)
- `on_loaded` runs in **its own thread** and may block (some plugins use it as a main loop).
- Every other event is **queued per-plugin and processed serially** by one worker thread.
  So within a single plugin your hooks won't overlap, but they run off the main thread.
- UI writes must be guarded: wrap `ui.set/add_element/remove_element` in `with ui._lock:`
  when called from `on_ui_update`/`on_unload` (see `example_memtemp.py`).
- Do heavy/slow work off the UI path; never block `on_ui_update`.

## The hooks we actually have (verified against source)
Lifecycle: `on_loaded(self)`, `on_config_changed(self, config)`, `on_ui_setup(self, ui)`,
`on_ready(self, agent)`, `on_ui_update(self, ui)`, `on_unload(self, ui)`,
`on_webhook(self, path, request)`, `on_internet_available(self, agent)`.

Data/RF: `on_wifi_update(self, agent, access_points)`,
`on_unfiltered_ap_list(self, agent, access_points)`,
`on_association(self, agent, access_point)`,
`on_deauthentication(self, agent, access_point, client_station)`,
`on_handshake(self, agent, filename, access_point, client_station)`,
`on_epoch(self, agent, epoch, epoch_data)`, `on_channel_hop(self, agent, channel)`,
`on_free_channel(...)`, `on_bcap_sys_log(self, agent, event)` (and other `on_bcap_*`).

Peers: `on_peer_detected(self, agent, peer)`, `on_peer_lost(self, agent, peer)`.

Mood (fired on state changes): `on_bored`, `on_sad`, `on_excited`, `on_lonely`,
`on_grateful`, `on_angry`, `on_sleep`, `on_wait`, `on_rebooting`, `on_display_setup`.

> Only implement the hooks you need — unknown/absent hooks are simply skipped.

## UI
- Build elements in `on_ui_setup(self, ui)`:
  ```python
  from pwnagotchi.ui.components import LabeledValue, Text
  from pwnagotchi.ui.view import BLACK
  import pwnagotchi.ui.fonts as fonts
  ui.add_element('mine_val', LabeledValue(color=BLACK, label='X:', value='-',
                 position=(x, y), label_font=fonts.Small, text_font=fonts.Small))
  ```
- Update in `on_ui_update(self, ui)` with `with ui._lock: ui.set('mine_val', text)`.
- Remove in `on_unload(self, ui)` with `with ui._lock: ui.remove_element('mine_val')`.
- Namespace element keys with the plugin name to avoid collisions (`<name>_<field>`).
- Positions vary by display; `ui.is_waveshare_v2()` etc. let you branch. Keep positions
  configurable via options where practical.

## Web UI
- Implement `on_webhook(self, path, request)` (Flask request). Return HTML/JSON.
- Reached at `http://<pi>:8080/plugins/<name>/`. Keep handlers bounded request/response —
  never hold a long-lived/streaming connection through Pwnagotchi's web server.

## `pwnagotchi` helpers you can use
`pwnagotchi.mem_usage()`, `pwnagotchi.cpu_load()`, `pwnagotchi.temperature(celsius=True)`,
`pwnagotchi.uptime()`, `pwnagotchi.config` (the parsed config dict).

## House rules for this project
- Guard every optional dependency/hardware access; degrade cleanly if absent (a plugin must
  never crash the agent because a sensor/adapter isn't there).
- Log via `logging` with a clear prefix; no prints.
- Persist plugin data under `/etc/pwnagotchi/` or a configured path; keep SD writes modest.
- Ship an example config block (`<name>.config.toml`) documenting every option + default.
- Every plugin gets an off-Pi unit test using the fakes in `tests/` (no real hardware).
