"""daily_digest — a rendered end-of-day summary card.

No daily rollup exists. This tallies the day's activity (handshakes, unique networks, uptime)
and, at the day boundary, renders a small summary card (PNG) to a folder — a nice artifact to
keep or push to a phone. Counters persist so a restart mid-day doesn't lose the tally.

Options (main.plugins.daily_digest.*):
    enabled     = true
    digest_dir  = "/root/digests"
    data_path   = "/etc/pwnagotchi/daily_digest.json"
    width       = 480
    height      = 320
    position    = "0,0"

Requires: none (Pillow ships with Pwnagotchi for the PNG render).
"""
import json
import logging
import os
from datetime import date

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def render_card(summary, path, size=(480, 320)):
    """Render a simple digest PNG. Returns the path, or None if Pillow is unavailable."""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    lines = [
        "Daily Digest  %s" % summary["date"],
        "",
        "Handshakes: %d" % summary["handshakes"],
        "Networks seen: %d" % summary["networks"],
        "Uptime: %d s" % summary["uptime"],
    ]
    y = 20
    for ln in lines:
        d.text((20, y), ln, fill="black")
        y += 40
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
    except Exception:
        return None
    return path


class DailyDigest(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Render a daily summary card (captures, networks, uptime)."

    def __init__(self):
        self.options = dict()
        self._day = None
        self._handshakes = 0
        self._networks = set()
        self._path = None

    def on_loaded(self):
        self._digest_dir = self.options.get("digest_dir", "/root/digests")
        self._path = self.options.get("data_path", "/etc/pwnagotchi/daily_digest.json")
        self._w = int(self.options.get("width", 480))
        self._h = int(self.options.get("height", 320))
        self._load()
        logging.info("[daily_digest] loaded (day=%s)", self._day)

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    d = json.load(fp)
                self._day = d.get("day")
                self._handshakes = d.get("handshakes", 0)
                self._networks = set(d.get("networks", []))
        except Exception as e:
            logging.debug("[daily_digest] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"day": self._day, "handshakes": self._handshakes,
                               "networks": sorted(self._networks)}, fp)
        except Exception as e:
            logging.debug("[daily_digest] save failed: %s", e)

    # -- core --------------------------------------------------------------------------
    @staticmethod
    def _today():
        return date.today().isoformat()

    def build_summary(self, day):
        try:
            uptime = int(pwnagotchi.uptime())
        except Exception:
            uptime = 0
        return {"date": day, "handshakes": self._handshakes,
                "networks": len(self._networks), "uptime": uptime}

    def _finalize(self, day):
        summary = self.build_summary(day)
        path = os.path.join(self._digest_dir, "digest-%s.png" % day)
        render_card(summary, path, (self._w, self._h))
        logging.info("[daily_digest] wrote digest for %s (%d handshakes)", day, summary["handshakes"])
        return summary, path

    def _ensure_day(self, today):
        if self._day is None:
            self._day = today
            self._save()
            return None
        if today != self._day:
            result = self._finalize(self._day)
            self._day = today
            self._handshakes = 0
            self._networks = set()
            self._save()
            return result
        return None

    def record_handshake(self, today=None):
        self._ensure_day(today or self._today())
        self._handshakes += 1
        self._save()

    def record_networks(self, access_points, today=None):
        self._ensure_day(today or self._today())
        before = len(self._networks)
        for ap in access_points or []:
            mac = ap.get("mac") if isinstance(ap, dict) else None
            if mac:
                self._networks.add(str(mac).lower())
        if len(self._networks) != before:      # persist only when new networks appear
            self._save()

    def maybe_rollover(self, today=None):
        return self._ensure_day(today or self._today())

    # -- events ------------------------------------------------------------------------
    def on_handshake(self, agent, filename, access_point, client_station):
        self.record_handshake()

    def on_wifi_update(self, agent, access_points):
        self.record_networks(access_points)

    def on_epoch(self, agent, epoch, epoch_data):
        self.maybe_rollover()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("digest", LabeledValue(color=BLACK, label="dg:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("digest", str(self._handshakes))

    def on_unload(self, ui):
        self._save()
        with ui._lock:
            if ui.has_element("digest"):
                ui.remove_element("digest")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        s = self.build_summary(self._day or self._today())
        try:
            saved = sorted(f for f in os.listdir(self._digest_dir) if f.endswith(".png"))
        except Exception:
            saved = []
        return ("<html><body><h1>Daily Digest</h1>"
                "<p>Today: {handshakes} handshakes, {networks} networks, uptime {uptime}s.</p>"
                "<p>Saved cards: {n}</p></body></html>").format(n=len(saved), **s)
