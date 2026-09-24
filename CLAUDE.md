# CLAUDE.md — Pwnagotchi plugin project

## What this repo is
A collection of **original Pwnagotchi plugins** that fill genuine gaps in the ecosystem
(nothing that duplicates a bundled or known-good community plugin). The scope is tracked in
`pwnagotchi-plugins/BUILD_LIST.md` (plugins P01–P46, grouped in batches A–I).

## Target platform (assume this unless told otherwise)
- Jayofelony Pwnagotchi image, Debian Trixie aarch64, **Python 3.13**.
- Reference display context: 480×320 TFT and common e-ink panels.
- Plugins must **degrade cleanly** when optional hardware/dependencies are absent — never
  crash the agent because a sensor, adapter, or module isn't present.

## Ground-truth API — read before coding
`pwnagotchi-plugins/reference/` holds the **real** upstream API, copied verbatim
(do not edit): the plugin base/loader, UI components, and two example plugins.
`pwnagotchi-plugins/reference/API_NOTES.md` distils the hooks and rules. Code against these,
not from memory. Key points:
- One `.py` file per plugin; filename = plugin name. One class subclassing
  `pwnagotchi.plugins.Plugin`.
- Metadata as literal class attrs: `__author__`, `__version__`, `__license__ = 'GPL3'`,
  `__description__`.
- Config via `self.options` (dict from `main.plugins.<name>.*`); read with `.get(k, default)`.
- Hooks: `on_loaded`, `on_ready(agent)`, `on_config_changed(config)`, `on_ui_setup(ui)`,
  `on_ui_update(ui)`, `on_unload(ui)`, `on_webhook(path, request)`,
  `on_internet_available(agent)`, `on_wifi_update(agent, aps)`,
  `on_handshake(agent, filename, ap, client)`, `on_epoch(agent, epoch, epoch_data)`, etc.
- `on_loaded` runs in its own thread; other events are queued and run serially off the main
  thread. Guard UI writes with `with ui._lock:`.

## Per-plugin deliverables (all four, every time)
A plugin isn't done until it has:
1. `<name>.py` — the plugin, matching the real API and house rules above.
2. `<name>.config.toml` — example config block documenting **every** option + default
   (Pwnagotchi merges these into the single `/etc/pwnagotchi/config.toml`). The header must
   include a `# Requires:` line.
3. `tests/test_<name>.py` — off-Pi unit test using the fakes in `tests/conftest.py`.
4. A short usage note (README section or header docstring): what it does, options, hardware.

## Documenting dependencies (required)
Any pip package, system binary/service, or hardware a plugin needs goes in **all three**:
- the plugin's module docstring (an `Options`/notes block already there),
- a `# Requires:` line at the top of its `config.toml`, and
- the Dependencies table in `pwnagotchi-plugins/README.md` (flip the "Built" mark to ✅).
If a plugin needs nothing beyond the stdlib (+ Pillow/numpy, which ship with Pwnagotchi),
say `Requires: none` explicitly. Keep optional deps clearly marked "optional".

## Testing
- Off-Pi harness lives in `pwnagotchi-plugins/tests/conftest.py` — it registers a fake
  `pwnagotchi` package so plugins import and run under plain pytest, no hardware.
- Fixtures: `load_plugin(rel_path, options=...)`, `ui` (FakeUI), `agent` (FakeAgent).
- Run: `cd pwnagotchi-plugins && PYTHONPATH= python -m pytest -q`
  (deps: `pip install -r requirements-dev.txt`).
- Always run tests before committing a plugin. Add a fast test for the happy path plus a
  "missing options / missing hardware" path.

## House rules
- Log via `logging` with a `[<name>]` prefix; no `print`.
- Keep SD writes modest; persist under `/etc/pwnagotchi/` or a configured path.
- Namespace UI element keys as `<name>_<field>`.
- Web handlers are bounded request/response — never hold a long-lived/streaming connection
  through Pwnagotchi's web server.
- New plugin? Copy `templates/plugin_template.py` + `templates/plugin_template.config.toml`.

## Git workflow
- Develop on branch `claude/happy-newton-60zxt8`; push there (`git push -u origin ...`).
- Do not open a PR unless explicitly asked.
- Commit trailers used in this project:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_0165vmpo5zQfCE2UaoNh7ojB
  ```
- Do not put model identifiers anywhere except commit trailers/chat.

## Layout
```
CLAUDE.md                     ← this file
pwnagotchi-plugins/
  BUILD_LIST.md               ← the roadmap (P01–P46)
  reference/                  ← real upstream API (read-only ground truth)
  templates/                  ← plugin + config starting points
  tests/                      ← off-Pi harness (conftest.py) + per-plugin tests
  <name>.py / <name>.config.toml   ← plugins land here as we build them
  requirements-dev.txt, pytest.ini
```
