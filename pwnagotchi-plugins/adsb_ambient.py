"""adsb_ambient — aircraft overhead from a local dump1090 feed.

If you run dump1090 (an RTL-SDR on 1090 MHz), this polls its ``aircraft.json`` and tracks the
planes currently overhead plus the total distinct aircraft seen this session. Ambient
awareness / a fun event source — it only reads dump1090's existing feed.

Guarded: if the feed URL isn't reachable, the plugin idles.

Options (main.plugins.adsb_ambient.*):
    enabled       = true
    url           = "http://127.0.0.1:8080/data/aircraft.json"
    interval_secs = 15
    max_seen      = 5000
    position      = "0,0"

Requires: a running dump1090 (e.g. dump1090-fa / dump1090-mutability) serving aircraft.json,
and an RTL-SDR.
"""
import json
import logging
import time
import urllib.request

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def parse_aircraft(obj):
    """Normalize a dump1090 aircraft.json dict into a list of aircraft summaries."""
    out = []
    if not isinstance(obj, dict):
        return out
    for a in obj.get("aircraft", []) or []:
        if not isinstance(a, dict):
            continue
        hexid = a.get("hex")
        if not hexid:
            continue
        out.append({
            "hex": str(hexid).lower().strip(),
            "flight": (a.get("flight") or "").strip(),
            "altitude": a.get("alt_baro", a.get("altitude")),
            "rssi": a.get("rssi"),
        })
    return out


class ADSBAmbient(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Track aircraft overhead from a local dump1090 feed."

    def __init__(self):
        self.options = dict()
        self._seen = set()
        self._current = []
        self._last_fetch = 0
        self._reachable = None

    def on_loaded(self):
        self._url = self.options.get("url", "http://127.0.0.1:8080/data/aircraft.json")
        self._interval = float(self.options.get("interval_secs", 15))
        self._max_seen = int(self.options.get("max_seen", 5000))
        logging.info("[adsb_ambient] loaded (url=%s)", self._url)

    # -- core (testable) ---------------------------------------------------------------
    def update(self, aircraft_list, now=None):
        now = now if now is not None else time.time()
        self._current = aircraft_list or []
        for a in self._current:
            if len(self._seen) < self._max_seen:
                self._seen.add(a["hex"])
        self._last_time = now
        return {"current": len(self._current), "distinct": len(self._seen)}

    # -- fetch (guarded, not unit-tested) ----------------------------------------------
    def _fetch(self):
        try:
            with urllib.request.urlopen(self._url, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8", "ignore"))
            self._reachable = True
            return data
        except Exception as e:
            if self._reachable is not False:
                logging.warning("[adsb_ambient] feed unreachable (%s): %s", self._url, e)
            self._reachable = False
            return None

    def _poll(self, now=None):
        now = now if now is not None else time.time()
        if (now - self._last_fetch) < self._interval:
            return
        self._last_fetch = now
        data = self._fetch()
        if data is not None:
            self.update(parse_aircraft(data), now)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        self._poll()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("adsb", LabeledValue(color=BLACK, label="adsb:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            if self._reachable is False:
                ui.set("adsb", "off")
            else:
                ui.set("adsb", str(len(self._current)))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("adsb"):
                ui.remove_element("adsb")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                a["hex"], a["flight"] or "?", a["altitude"], a["rssi"])
            for a in self._current
        ) or "<tr><td colspan=4>none overhead</td></tr>"
        return (
            "<html><body><h1>ADS-B Ambient</h1>"
            "<p>{} overhead now, {} distinct this session.</p>"
            "<table border=1><tr><th>hex</th><th>flight</th><th>alt</th><th>rssi</th></tr>{}"
            "</table></body></html>"
        ).format(len(self._current), len(self._seen), rows)
