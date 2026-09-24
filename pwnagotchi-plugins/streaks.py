"""streaks — longevity stats and personal records.

Tracks the numbers that make people attached to a device: days active, consecutive-day
streaks, and daily records (most unique networks in a day, most handshakes in a day). State
persists to a small JSON file, so it survives restarts. Shows "Nd Ks" (days / current
streak) on the display, with the full record board on the plugin web page.

Options (main.plugins.streaks.*):
    enabled   = true
    data_path = "/etc/pwnagotchi/streaks.json"
    position  = "0,0"
"""
import json
import logging
import os
from datetime import date, timedelta

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_DEFAULT_STATE = {
    "first_seen": None,
    "last_active_day": None,
    "days_alive": 0,
    "current_streak": 0,
    "longest_streak": 0,
    "networks_today": 0,
    "handshakes_today": 0,
    "most_networks_in_a_day": 0,
    "most_handshakes_in_a_day": 0,
}


class Streaks(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Longevity stats: days active, streaks, and daily records."

    def __init__(self):
        self.options = dict()
        self._state = dict(_DEFAULT_STATE)
        self._today_bssids = set()
        self._path = None

    def on_loaded(self):
        self._path = self.options.get("data_path", "/etc/pwnagotchi/streaks.json")
        self._load()
        logging.info("[streaks] loaded (days_alive=%d)", self._state.get("days_alive", 0))

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    data = json.load(fp)
                if isinstance(data, dict):
                    merged = dict(_DEFAULT_STATE)
                    merged.update(data)
                    self._state = merged
        except Exception as e:
            logging.debug("[streaks] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump(self._state, fp, indent=2)
        except Exception as e:
            logging.debug("[streaks] save failed: %s", e)

    # -- core logic (date injectable for testing) --------------------------------------
    @staticmethod
    def _today():
        return date.today().isoformat()

    def _apply_day(self, today_str):
        """Roll over to `today_str`; update days_alive + streaks. Returns True if new day."""
        st = self._state
        last = st.get("last_active_day")
        if last == today_str:
            return False
        if last is None:
            st["first_seen"] = today_str
            st["days_alive"] = 1
            st["current_streak"] = 1
        else:
            try:
                gap = (date.fromisoformat(today_str) - date.fromisoformat(last)).days
            except Exception:
                gap = 99
            st["days_alive"] = st.get("days_alive", 0) + 1
            st["current_streak"] = st.get("current_streak", 0) + 1 if gap == 1 else 1
        st["longest_streak"] = max(st.get("longest_streak", 0), st.get("current_streak", 1))
        st["last_active_day"] = today_str
        st["networks_today"] = 0
        st["handshakes_today"] = 0
        self._today_bssids = set()
        return True

    def record_activity(self, today=None):
        if self._apply_day(today or self._today()):
            self._save()

    def record_networks(self, access_points, today=None):
        self._apply_day(today or self._today())
        for ap in access_points or []:
            mac = (ap.get("mac") if isinstance(ap, dict) else None)
            if mac:
                self._today_bssids.add(str(mac).lower())
        self._state["networks_today"] = len(self._today_bssids)
        self._state["most_networks_in_a_day"] = max(
            self._state.get("most_networks_in_a_day", 0), self._state["networks_today"])
        self._save()

    def record_handshake(self, today=None):
        self._apply_day(today or self._today())
        self._state["handshakes_today"] = self._state.get("handshakes_today", 0) + 1
        self._state["most_handshakes_in_a_day"] = max(
            self._state.get("most_handshakes_in_a_day", 0), self._state["handshakes_today"])
        self._save()

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        self.record_activity()

    def on_wifi_update(self, agent, access_points):
        self.record_networks(access_points)

    def on_handshake(self, agent, filename, access_point, client_station):
        self.record_handshake()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        return "%dd %ds" % (self._state.get("days_alive", 0), self._state.get("current_streak", 0))

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("streaks", LabeledValue(color=BLACK, label="streak:", value="0d 0s",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("streaks", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("streaks"):
                ui.remove_element("streaks")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        st = self._state
        rows = "".join("<tr><td>{}</td><td>{}</td></tr>".format(k, st.get(k)) for k in (
            "first_seen", "days_alive", "current_streak", "longest_streak",
            "networks_today", "most_networks_in_a_day",
            "handshakes_today", "most_handshakes_in_a_day",
        ))
        return "<html><body><h1>Streaks &amp; Records</h1><table border=1>{}</table></body></html>".format(rows)
