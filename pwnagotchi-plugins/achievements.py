"""achievements — a real milestone/badge system.

`age` tracks raw stats but there's no achievement layer. This maintains lifetime stats
(handshakes, unique networks, unique peers, active days) and unlocks achievements from a
catalog as thresholds are met — including a hidden one. Unlocked badges persist; the display
shows unlocked/total and the web page is a trophy cabinet.

Options (main.plugins.achievements.*):
    enabled   = true
    data_path = "/etc/pwnagotchi/achievements.json"
    position  = "0,0"

Requires: none (Python standard library).
"""
import json
import logging
import os
import time
from datetime import date

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

# id, name, description, check(stats)->bool, hidden
ACHIEVEMENTS = [
    ("first_blood", "First Blood", "Capture your first handshake.",
     lambda s: s.get("handshakes", 0) >= 1, False),
    ("handshake_10", "Getting Warmed Up", "Capture 10 handshakes.",
     lambda s: s.get("handshakes", 0) >= 10, False),
    ("handshake_100", "Centurion", "Capture 100 handshakes.",
     lambda s: s.get("handshakes", 0) >= 100, False),
    ("handshake_1000", "Millennium", "Capture 1000 handshakes.",
     lambda s: s.get("handshakes", 0) >= 1000, False),
    ("networker", "Networker", "See 100 distinct networks.",
     lambda s: s.get("networks", 0) >= 100, False),
    ("explorer", "Explorer", "See 1000 distinct networks.",
     lambda s: s.get("networks", 0) >= 1000, False),
    ("social", "Say Hello", "Meet another unit.",
     lambda s: s.get("peers", 0) >= 1, False),
    ("herd", "The Herd", "Meet 10 distinct units.",
     lambda s: s.get("peers", 0) >= 10, False),
    ("dedicated", "Dedicated", "Active on 7 different days.",
     lambda s: s.get("days", 0) >= 7, False),
    ("veteran", "Veteran", "Active on 30 different days.",
     lambda s: s.get("days", 0) >= 30, False),
    ("night_owl", "Night Owl", "Capture a handshake between 2 and 5 AM.",
     lambda s: bool(s.get("night")), True),
]


def evaluate(stats, unlocked):
    """Return newly-unlockable achievement ids (catalog order)."""
    done = set(unlocked)
    return [a[0] for a in ACHIEVEMENTS if a[0] not in done and a[3](stats)]


class Achievements(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Unlockable achievements/trophies from lifetime stats."

    def __init__(self):
        self.options = dict()
        self._handshakes = 0
        self._net_set = set()
        self._peer_set = set()
        self._day_set = set()
        self._night = False
        self._unlocked = []
        self._recent = None
        self._recent_at = 0
        self._path = None

    def on_loaded(self):
        self._path = self.options.get("data_path", "/etc/pwnagotchi/achievements.json")
        self._load()
        logging.info("[achievements] loaded (%d/%d unlocked)", len(self._unlocked), len(ACHIEVEMENTS))

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    d = json.load(fp)
                self._handshakes = d.get("handshakes", 0)
                self._net_set = set(d.get("networks", []))
                self._peer_set = set(d.get("peers", []))
                self._day_set = set(d.get("days", []))
                self._night = d.get("night", False)
                self._unlocked = d.get("unlocked", [])
        except Exception as e:
            logging.debug("[achievements] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"handshakes": self._handshakes,
                               "networks": sorted(self._net_set),
                               "peers": sorted(self._peer_set),
                               "days": sorted(self._day_set),
                               "night": self._night,
                               "unlocked": self._unlocked}, fp)
        except Exception as e:
            logging.debug("[achievements] save failed: %s", e)

    # -- stats + unlock ----------------------------------------------------------------
    def stats(self):
        return {"handshakes": self._handshakes, "networks": len(self._net_set),
                "peers": len(self._peer_set), "days": len(self._day_set), "night": self._night}

    def _check_unlocks(self):
        new = evaluate(self.stats(), self._unlocked)
        if new:
            self._unlocked.extend(new)
            names = [a[1] for a in ACHIEVEMENTS if a[0] == new[-1]]
            self._recent = names[0] if names else new[-1]
            self._recent_at = time.time()
            for aid in new:
                logging.info("[achievements] unlocked: %s", aid)
            self._save()
        return new

    def record_handshake(self, hour=None):
        self._handshakes += 1
        if hour is not None and 2 <= hour < 5:
            self._night = True
        self._save()
        return self._check_unlocks()

    def record_networks(self, access_points):
        before = len(self._net_set)
        for ap in access_points or []:
            mac = ap.get("mac") if isinstance(ap, dict) else None
            if mac:
                self._net_set.add(str(mac).lower())
        if len(self._net_set) != before:
            self._save()
            return self._check_unlocks()
        return []

    def record_peer(self, peer_id):
        if peer_id and peer_id not in self._peer_set:
            self._peer_set.add(peer_id)
            self._save()
            return self._check_unlocks()
        return []

    def record_day(self, today):
        if today not in self._day_set:
            self._day_set.add(today)
            self._save()
            return self._check_unlocks()
        return []

    @staticmethod
    def _peer_id(peer):
        for attr in ("identity", "name", "fingerprint"):
            v = getattr(peer, attr, None) if not isinstance(peer, dict) else peer.get(attr)
            if v:
                return str(v)
        return str(peer)[:64] if peer is not None else None

    # -- events ------------------------------------------------------------------------
    def on_handshake(self, agent, filename, access_point, client_station):
        self.record_handshake(hour=time.localtime().tm_hour)

    def on_wifi_update(self, agent, access_points):
        self.record_networks(access_points)

    def on_peer_detected(self, agent, peer):
        self.record_peer(self._peer_id(peer))

    def on_epoch(self, agent, epoch, epoch_data):
        self.record_day(date.today().isoformat())

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("ach", LabeledValue(color=BLACK, label="ach:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("ach", "%d/%d" % (len(self._unlocked), len(ACHIEVEMENTS)))

    def on_unload(self, ui):
        self._save()
        with ui._lock:
            if ui.has_element("ach"):
                ui.remove_element("ach")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        done = set(self._unlocked)
        rows = ""
        for aid, name, desc, _check, hidden in ACHIEVEMENTS:
            got = aid in done
            if hidden and not got:
                rows += "<tr><td>???</td><td>Hidden achievement</td><td>locked</td></tr>"
            else:
                rows += "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    name, desc, "✅" if got else "locked")
        return ("<html><body><h1>Achievements ({}/{})</h1>"
                "<table border=1><tr><th>name</th><th>description</th><th>status</th></tr>{}"
                "</table></body></html>").format(len(done), len(ACHIEVEMENTS), rows)
