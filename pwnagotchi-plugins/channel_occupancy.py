"""channel_occupancy — log which Wi-Fi channels are busiest over time.

Useful and unlogged: this tallies how many APs are seen on each channel across every scan,
building a cumulative occupancy picture (plus a live per-scan unique-BSSID count). Shows the
busiest channel on the display and a simple bar heatmap on the web page.

Options (main.plugins.channel_occupancy.*):
    enabled   = true
    data_path = "/etc/pwnagotchi/channel_occupancy.json"
    position  = "0,0"
"""
import json
import logging
import os
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class ChannelOccupancy(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Log Wi-Fi channel occupancy over time; show the busiest channel."

    def __init__(self):
        self.options = dict()
        self._obs = {}            # channel(int) -> cumulative AP observations
        self._session = {}        # channel(int) -> set(bssid) this session
        self._records = 0
        self._path = None

    def on_loaded(self):
        self._path = self.options.get("data_path", "/etc/pwnagotchi/channel_occupancy.json")
        self._load()
        logging.info("[channel_occupancy] loaded (%d channels seen)", len(self._obs))

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    d = json.load(fp)
                self._obs = {int(k): int(v) for k, v in d.get("obs", {}).items()}
        except Exception as e:
            logging.debug("[channel_occupancy] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"obs": {str(k): v for k, v in self._obs.items()}}, fp)
        except Exception as e:
            logging.debug("[channel_occupancy] save failed: %s", e)

    # -- core --------------------------------------------------------------------------
    def record(self, access_points):
        for ap in access_points or []:
            if not isinstance(ap, dict):
                continue
            ch = ap.get("channel")
            if ch is None:
                continue
            try:
                ch = int(ch)
            except (TypeError, ValueError):
                continue
            self._obs[ch] = self._obs.get(ch, 0) + 1
            mac = ap.get("mac")
            if mac:
                self._session.setdefault(ch, set()).add(str(mac).lower())
        self._records += 1
        if self._records % 50 == 0:
            self._save()

    def busiest(self):
        """(channel, unique_bssids_this_session) or None — falls back to cumulative obs."""
        if self._session:
            ch = max(self._session, key=lambda c: len(self._session[c]))
            return ch, len(self._session[ch])
        if self._obs:
            ch = max(self._obs, key=lambda c: self._obs[c])
            return ch, self._obs[ch]
        return None

    # -- events ------------------------------------------------------------------------
    def on_wifi_update(self, agent, access_points):
        self.record(access_points)

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        b = self.busiest()
        return "-" if not b else "%d(%d)" % (b[0], b[1])

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("chan", LabeledValue(color=BLACK, label="ch:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("chan", self._ui_value())

    def on_unload(self, ui):
        self._save()
        with ui._lock:
            if ui.has_element("chan"):
                ui.remove_element("chan")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        if not self._obs:
            return "<html><body><h1>Channel Occupancy</h1><p>no data yet</p></body></html>"
        peak = max(self._obs.values())
        rows = ""
        for ch in sorted(self._obs):
            width = int(200 * self._obs[ch] / peak) if peak else 0
            rows += ("<tr><td>ch {}</td><td><div style='background:#39c;height:12px;"
                     "width:{}px'></div></td><td>{}</td></tr>").format(ch, width, self._obs[ch])
        return ("<html><body><h1>Channel Occupancy</h1><table>{}</table></body></html>").format(rows)
