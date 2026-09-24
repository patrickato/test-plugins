# Reference material — real Pwnagotchi plugin API

These files are copied **verbatim** from the Jayofelony Pwnagotchi source so our plugins are
written against the true API, not from memory. Do not edit them — they are ground truth.

| File | Copied from (jayofelony/pwnagotchi) | Why it's here |
|------|-------------------------------------|---------------|
| `pwnagotchi_plugins_init.py` | `pwnagotchi/plugins/__init__.py` | The plugin base class, loader, and event dispatch — the authoritative hook contract. |
| `pwnagotchi_ui_components.py` | `pwnagotchi/ui/components.py` | UI widget signatures (`Text`, `LabeledValue`, `Line`, `Rect`, …). |
| `example_memtemp.py` | `pwnagotchi/plugins/default/memtemp.py` | Canonical example: options, `on_ui_setup`/`on_ui_update`/`on_unload`, thread-safe UI writes. |
| `example_gps.py` | `pwnagotchi/plugins/default/gps.py` | Second example: `on_ready`, `on_handshake`, config, file output. |

`API_NOTES.md` distils these into the rules we actually follow when writing a plugin.

## Licensing / provenance
Upstream Pwnagotchi is **GPLv3**. This project is also GPLv3 (see repo `LICENSE`), so including
these files is license-compatible. They remain under their original copyright — this folder is
reference only and ships no modified upstream code. Source:
<https://github.com/jayofelony/pwnagotchi>.
