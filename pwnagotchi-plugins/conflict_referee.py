"""conflict_referee — spot plugins fighting over the same resource.

A big share of "why is my screen/pin broken" problems are silent plugin collisions. This
inspects the enabled plugins' config and flags when two of them claim the same UI position or
the same GPIO pin, naming the plugins and the resource. Read-only: it reports, it doesn't
change anything.

Options (main.plugins.conflict_referee.*):
    enabled  = true
    position = "0,0"
"""
import logging

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def parse_position(value):
    try:
        parts = [int(x) for x in str(value).split(",")]
        if len(parts) == 2:
            return (parts[0], parts[1])
    except Exception:
        pass
    return None


def extract_resources(plugins_cfg):
    """From a main.plugins config dict, collect each enabled plugin's UI positions + pins."""
    positions, pins = {}, {}
    for name, opts in (plugins_cfg or {}).items():
        if not isinstance(opts, dict) or not opts.get("enabled", False):
            continue
        for k, v in opts.items():
            lk = k.lower()
            if "position" in lk:
                p = parse_position(v)
                if p:
                    positions[name] = p
            elif "gpio" in lk or lk == "pin" or lk.endswith("_pin"):
                try:
                    pins.setdefault(name, set()).add(int(v))
                except (TypeError, ValueError):
                    pass
    return {"positions": positions, "pins": pins}


def find_conflicts(resources):
    conflicts = []
    pos_groups = {}
    for name, pos in resources["positions"].items():
        pos_groups.setdefault(pos, []).append(name)
    for pos, names in pos_groups.items():
        if len(names) > 1:
            conflicts.append({"type": "ui_position", "resource": "%d,%d" % pos,
                              "plugins": sorted(names)})
    pin_owner = {}
    for name, pinset in resources["pins"].items():
        for pin in pinset:
            pin_owner.setdefault(pin, []).append(name)
    for pin, names in pin_owner.items():
        if len(names) > 1:
            conflicts.append({"type": "gpio_pin", "resource": str(pin),
                              "plugins": sorted(names)})
    return conflicts


class ConflictReferee(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Detect plugins colliding on a UI position or GPIO pin."

    def __init__(self):
        self.options = dict()
        self._conflicts = []

    def on_loaded(self):
        logging.info("[conflict_referee] loaded")

    # -- core --------------------------------------------------------------------------
    def refresh(self, plugins_cfg=None):
        if plugins_cfg is None:
            try:
                plugins_cfg = pwnagotchi.config.get("main", {}).get("plugins", {})
            except Exception:
                plugins_cfg = {}
        self._conflicts = find_conflicts(extract_resources(plugins_cfg))
        if self._conflicts:
            logging.warning("[conflict_referee] %d conflict(s): %s", len(self._conflicts),
                            "; ".join("%s@%s=%s" % (c["type"], c["resource"], c["plugins"])
                                      for c in self._conflicts))
        return self._conflicts

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.refresh()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("referee", LabeledValue(color=BLACK, label="conf:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("referee", "ok" if not self._conflicts else str(len(self._conflicts)))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("referee"):
                ui.remove_element("referee")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        self.refresh()
        if not self._conflicts:
            return "<html><body><h1>Conflict Referee</h1><p>No conflicts. 🎉</p></body></html>"
        rows = "".join(
            "<tr><td>{type}</td><td>{resource}</td><td>{plugins}</td></tr>".format(
                type=c["type"], resource=c["resource"], plugins=", ".join(c["plugins"]))
            for c in self._conflicts)
        return ("<html><body><h1>Conflict Referee</h1>"
                "<table border=1><tr><th>type</th><th>resource</th><th>plugins</th></tr>{}"
                "</table></body></html>").format(rows)
