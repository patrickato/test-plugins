"""Plugin template — copy this to start a new plugin.

Rename the file to your plugin name (e.g. ``sd_wear.py``), rename the class, and fill in
the metadata. Only keep the hooks you actually use. See ``reference/API_NOTES.md`` for the
full hook list and rules.
"""
import logging

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class PluginTemplate(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Template plugin — a starting point, safe to run, does nothing useful."

    def __init__(self):
        # Ensure the instance is valid before options are injected by the loader.
        self.options = dict()
        self._ready = False

    # -- lifecycle ---------------------------------------------------------------------
    def on_loaded(self):
        # Read options defensively with defaults.
        self._label = str(self.options.get("label", "TMPL"))
        self._enabled_note = bool(self.options.get("verbose", False))
        logging.info("[plugin_template] loaded (label=%s)", self._label)

    def on_ready(self, agent):
        # Agent is available; safe to touch runtime state here.
        self._ready = True
        if self._enabled_note:
            logging.info("[plugin_template] ready")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("tmpl_val"):
                ui.remove_element("tmpl_val")
        logging.info("[plugin_template] unloaded")

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        # Position is display-dependent; expose it as an option with a sane default.
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element(
            "tmpl_val",
            LabeledValue(
                color=BLACK,
                label=f"{self._label}:",
                value="-",
                position=pos,
                label_font=fonts.Small,
                text_font=fonts.Small,
            ),
        )

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("tmpl_val", "ok" if self._ready else "…")

    # -- web (optional) ----------------------------------------------------------------
    def on_webhook(self, path, request):
        # Reached at http://<pi>:8080/plugins/plugin_template/
        return "<html><body><h1>plugin_template</h1><p>It works.</p></body></html>"
