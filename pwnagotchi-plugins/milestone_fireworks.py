"""milestone_fireworks — a little celebration when you hit a milestone.

Watches the running handshake count and, when it crosses a milestone (10, 50, 100, ... and
every 1000 after), throws a brief party: a celebratory face + message on the display for a
few seconds. Pairs nicely with the achievements/streaks plugins. Purely cosmetic.

Options (main.plugins.milestone_fireworks.*):
    enabled        = true
    milestones     = [10, 25, 50, 100, 250, 500, 1000]  # plus every 1000 after the last
    celebrate_secs = 8
    face           = "(^o^)/"
    message        = "MILESTONE!"
    data_path      = "/etc/pwnagotchi/milestone_fireworks.json"
    position       = "0,0"
"""
import json
import logging
import os
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

DEFAULT_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]


def crossed_milestones(old, new, milestones):
    """Milestones strictly greater than `old` and <= `new` (fixed list + every-1000 tail)."""
    if new <= old:
        return []
    hits = [m for m in milestones if old < m <= new]
    step_base = max(milestones) if milestones else 1000
    step = 1000
    # every `step` after the largest fixed milestone
    start = (old // step + 1) * step
    for m in range(start, new + 1, step):
        if m > step_base and m not in hits:
            hits.append(m)
    return sorted(set(hits))


class MilestoneFireworks(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Celebrate handshake-count milestones with a brief on-screen party."

    def __init__(self):
        self.options = dict()
        self._count = 0
        self._celebrating_until = 0
        self._last_milestone = None
        self._path = None

    def on_loaded(self):
        self._milestones = sorted(set(self.options.get("milestones", DEFAULT_MILESTONES)))
        self._celebrate_secs = float(self.options.get("celebrate_secs", 8))
        self._face = self.options.get("face", "(^o^)/")
        self._message = self.options.get("message", "MILESTONE!")
        self._path = self.options.get("data_path", "/etc/pwnagotchi/milestone_fireworks.json")
        self._load()
        logging.info("[milestone_fireworks] loaded (count=%d)", self._count)

    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    self._count = json.load(fp).get("count", 0)
        except Exception as e:
            logging.debug("[milestone_fireworks] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"count": self._count}, fp)
        except Exception as e:
            logging.debug("[milestone_fireworks] save failed: %s", e)

    # -- core --------------------------------------------------------------------------
    def add(self, n=1, now=None):
        """Increment the count; return the milestone celebrated (or None)."""
        now = now if now is not None else time.time()
        old = self._count
        self._count += n
        self._save()
        hits = crossed_milestones(old, self._count, self._milestones)
        if hits:
            self._last_milestone = hits[-1]
            self._celebrating_until = now + self._celebrate_secs
            logging.info("[milestone_fireworks] milestone reached: %d", self._last_milestone)
            return self._last_milestone
        return None

    def celebrating(self, now=None):
        now = now if now is not None else time.time()
        return now < self._celebrating_until

    # -- events ------------------------------------------------------------------------
    def on_handshake(self, agent, filename, access_point, client_station):
        self.add(1)

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("fireworks", LabeledValue(color=BLACK, label="", value="",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            if self.celebrating():
                ui.set("fireworks", "%s %s %d" % (self._face, self._message, self._last_milestone))
                ui.set("face", self._face)
            else:
                ui.set("fireworks", "")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("fireworks"):
                ui.remove_element("fireworks")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>Milestone Fireworks</h1>"
                "<p>count: {} — last milestone: {}</p></body></html>").format(
                    self._count, self._last_milestone or "-")
