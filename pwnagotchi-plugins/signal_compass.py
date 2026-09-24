"""signal_compass — warmer/colder RSSI guidance to find a device or AP.

RSSI is shown as a raw number and nothing turns it into "you're getting closer." This tracks
the signal of one target BSSID over recent scans and reports a warmer/colder trend plus a
rough proximity bucket — handy for locating your own misplaced AP or device. Set a target
BSSID, or let it lock onto the strongest AP.

Options (main.plugins.signal_compass.*):
    enabled        = true
    target         =            # BSSID to track (any case/separator); empty + auto = strongest
    auto_strongest = false      # lock onto the strongest AP when no target is set
    window         = 8          # RSSI samples kept for the trend
    position       = "0,0"
"""
import logging
import statistics

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_HEX = set("0123456789abcdef")


def normalize_hex(value):
    return "".join(c for c in str(value or "").lower() if c in _HEX)


def classify_proximity(rssi):
    if rssi >= -45:
        return "very close"
    if rssi >= -60:
        return "close"
    if rssi >= -72:
        return "near"
    if rssi >= -82:
        return "far"
    return "very far"


def trend_from(values):
    """'warmer' (rising RSSI), 'colder', or 'steady' from an ordered RSSI list."""
    if len(values) < 4:
        return "steady"
    half = len(values) // 2
    older = statistics.mean(values[:half])
    recent = statistics.mean(values[half:])
    d = recent - older
    if d > 2:
        return "warmer"
    if d < -2:
        return "colder"
    return "steady"


class SignalCompass(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Warmer/colder RSSI trend for a target BSSID to help locate it."

    def __init__(self):
        self.options = dict()
        self._target = None
        self._samples = []        # recent RSSI values

    def on_loaded(self):
        self._target = normalize_hex(self.options.get("target")) or None
        self._auto = bool(self.options.get("auto_strongest", False))
        self._window = int(self.options.get("window", 8))
        logging.info("[signal_compass] loaded (target=%s auto=%s)", self._target, self._auto)

    # -- core --------------------------------------------------------------------------
    def set_target(self, bssid):
        self._target = normalize_hex(bssid) or None
        self._samples = []

    def record(self, access_points):
        aps = [ap for ap in (access_points or []) if isinstance(ap, dict)]
        if not self._target and self._auto and aps:
            strongest = max(aps, key=lambda a: a.get("rssi", -999))
            self.set_target(strongest.get("mac"))
        if not self._target:
            return
        for ap in aps:
            if normalize_hex(ap.get("mac")) == self._target:
                rssi = ap.get("rssi")
                if rssi is not None:
                    self._samples.append(int(rssi))
                    self._samples = self._samples[-self._window:]
                break

    def status(self):
        if not self._samples:
            return {"target": self._target, "rssi": None, "trend": "steady", "proximity": None}
        rssi = self._samples[-1]
        return {"target": self._target, "rssi": rssi, "trend": trend_from(self._samples),
                "proximity": classify_proximity(rssi)}

    # -- events ------------------------------------------------------------------------
    def on_wifi_update(self, agent, access_points):
        self.record(access_points)

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        st = self.status()
        if st["rssi"] is None:
            return "-"
        arrow = {"warmer": "^", "colder": "v", "steady": "="}[st["trend"]]
        return "%s%d" % (arrow, st["rssi"])

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("sigcompass", LabeledValue(color=BLACK, label="sig:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("sigcompass", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("sigcompass"):
                ui.remove_element("sigcompass")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        try:
            if request is not None:
                t = request.args.get("target")
                if t:
                    self.set_target(t)
        except Exception:
            pass
        st = self.status()
        return (
            "<html><body><h1>Signal Compass</h1>"
            "<form><input name='target' placeholder='bssid' value='{}'>"
            "<button>Track</button></form>"
            "<ul><li>target: {}</li><li>rssi: {}</li><li>trend: {}</li>"
            "<li>proximity: {}</li></ul></body></html>"
        ).format(st["target"] or "", st["target"], st["rssi"], st["trend"], st["proximity"])
