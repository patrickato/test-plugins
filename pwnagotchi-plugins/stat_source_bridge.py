"""stat_source_bridge — feed real values into Korrie71 Theme Manager.

Korrie71's Theme Manager has a module-level ``STAT_SOURCE`` callback that its lazy text
formatter calls for placeholder keys it doesn't know itself. This plugin installs a bridge on
that hook so a Theme Manager theme can show live Pwnagotchi values via extra ``{pwn_*}`` tokens
(e.g. ``{pwn_temp}``, ``{pwn_handshakes}``) — without merging renderers or duplicating
collectors.

It is **non-destructive**: it captures whatever ``STAT_SOURCE`` is already set to (Theme
Manager's own ``_live_stat``) and delegates to it for keys it doesn't handle, and it re-installs
itself if Theme Manager loads after this plugin and overwrites the hook. Flat, prefixed token
names are used on purpose — Theme Manager expands text with ``str.format_map``, where dotted
names would raise and blank the whole line.

Options (main.plugins.stat_source_bridge.*):
    enabled  = true
    prefix   = "pwn_"          # token prefix: {pwn_temp}, {pwn_cpu}, ...
    keys     = ["temp","cpu","mem","uptime","handshakes","name"]
    position = "0,0"

Requires: Korrie71's Theme Manager installed & loaded (this plugin does nothing without it).
"""
import logging
import socket
import sys

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

DEFAULT_KEYS = ["temp", "cpu", "mem", "uptime", "handshakes", "name"]


def build_bridge(value_fn, prior):
    """Return a STAT_SOURCE callable: our values first, else delegate to `prior`."""
    def bridged(key):
        v = value_fn(key)
        if v is not None:
            return v
        if prior is not None:
            try:
                return prior(key)
            except Exception:
                return None
        return None
    bridged._is_bridge = True
    bridged._prior = prior
    return bridged


class StatSourceBridge(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Bridge live Pwnagotchi values into Korrie71 Theme Manager's STAT_SOURCE."

    def __init__(self):
        self.options = dict()
        self._handshakes = 0
        self._installed = False
        self._module = None

    def on_loaded(self):
        self._prefix = self.options.get("prefix", "pwn_")
        self._keys = list(self.options.get("keys", DEFAULT_KEYS))
        logging.info("[stat_source_bridge] loaded (prefix=%s)", self._prefix)

    # -- values (testable) -------------------------------------------------------------
    def _stats(self):
        d = {}
        try:
            d["temp"] = "%dC" % round(float(pwnagotchi.temperature()))
        except Exception:
            pass
        try:
            d["cpu"] = "%d%%" % round(float(pwnagotchi.cpu_load()) * 100)
        except Exception:
            pass
        try:
            d["mem"] = "%d%%" % round(float(pwnagotchi.mem_usage()) * 100)
        except Exception:
            pass
        try:
            up = int(pwnagotchi.uptime())
            d["uptime"] = "%dh%02dm" % (up // 3600, (up % 3600) // 60)
        except Exception:
            pass
        d["handshakes"] = str(self._handshakes)
        try:
            d["name"] = socket.gethostname()
        except Exception:
            pass
        return {k: v for k, v in d.items() if k in self._keys}

    def value_for(self, key):
        if not key.startswith(self._prefix):
            return None
        short = key[len(self._prefix):]
        if short not in self._keys:
            return None
        return self._stats().get(short)

    # -- install (guarded) -------------------------------------------------------------
    def _find_theme_manager(self):
        for name, mod in list(sys.modules.items()):
            if mod is None:
                continue
            try:
                if hasattr(mod, "STAT_SOURCE") and hasattr(mod, "_Lazy"):
                    return mod
            except Exception:
                continue
        return None

    def install(self):
        mod = self._find_theme_manager()
        if mod is None:
            self._installed = False
            return False
        current = getattr(mod, "STAT_SOURCE", None)
        if getattr(current, "_is_bridge", False):
            self._installed = True          # already ours
            self._module = mod
            return True
        # wrap whatever Theme Manager (or nothing) currently has
        mod.STAT_SOURCE = build_bridge(self.value_for, current)
        self._installed = True
        self._module = mod
        logging.info("[stat_source_bridge] installed into %s", getattr(mod, "__name__", "?"))
        return True

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.install()

    def on_handshake(self, agent, filename, access_point, client_station):
        self._handshakes += 1

    def on_epoch(self, agent, epoch, epoch_data):
        # Re-install if Theme Manager loaded later and overwrote the hook.
        if not self._installed or (self._module is not None
                                   and not getattr(getattr(self._module, "STAT_SOURCE", None),
                                                   "_is_bridge", False)):
            self.install()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("bridge", LabeledValue(color=BLACK, label="tmbridge:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("bridge", "on" if self._installed else "off")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("bridge"):
                ui.remove_element("bridge")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        tokens = ", ".join("{%s%s}" % (self._prefix, k) for k in self._keys)
        return ("<html><body><h1>Theme Manager Stat Bridge</h1>"
                "<p>installed: {}</p><p>exposes tokens: {}</p>"
                "<p>current values: {}</p></body></html>").format(
                    self._installed, tokens, self._stats())
