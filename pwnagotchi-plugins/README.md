# Pwnagotchi Gap Plugins

Original plugins that fill real gaps in the Pwnagotchi ecosystem — see
[`BUILD_LIST.md`](BUILD_LIST.md) for the roadmap (P01–P46).

## Layout
- `reference/` — the real upstream plugin API, copied verbatim (ground truth; don't edit).
- `templates/` — copy `plugin_template.py` + `plugin_template.config.toml` to start a plugin.
- `tests/` — off-Pi test harness (`conftest.py` fakes the `pwnagotchi` package) + tests.
- `<name>.py` / `<name>.config.toml` — plugins land at the top level as they're built.

## Develop
```bash
pip install -r requirements-dev.txt
PYTHONPATH= python -m pytest -q      # run from this directory
```
Read `reference/API_NOTES.md` and the project `CLAUDE.md` before writing a plugin.

## License
GPLv3 (see repo `LICENSE`), matching upstream Pwnagotchi.
