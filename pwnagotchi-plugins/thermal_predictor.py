"""thermal_predictor — act before the throttle, not after.

Everything on a Pi reacts to heat *after* throttling starts. This plugin samples CPU
temperature over a sliding window, fits the slope (°C/min), and predicts how long until the
throttle threshold is reached. When that lead time drops below a configured cushion it raises
an early warning (so cooling can spin up or optional load can be shed) instead of waiting for
the throttle.

It's observational: it warns and exposes state, but doesn't own fan/power policy (see
fan_curve / a resource governor for that).

Options (main.plugins.thermal_predictor.*):
    enabled       = true
    threshold_c   = 80         # throttle threshold to predict against
    lead_seconds  = 120        # warn when predicted time-to-threshold drops below this
    window_secs   = 180        # sliding window used for the slope fit
    position      = "0,0"
"""
import logging
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def linreg_slope(points):
    """Least-squares slope (per second) of (t, temp) points; 0 if not enough data."""
    n = len(points)
    if n < 2:
        return 0.0
    mean_t = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    var = sum((p[0] - mean_t) ** 2 for p in points)
    if var == 0:
        return 0.0
    cov = sum((p[0] - mean_t) * (p[1] - mean_y) for p in points)
    return cov / var


def predict_time_to(current, slope_per_s, threshold):
    """Seconds until `threshold` at the current rise rate; 0 if already there, None if not rising."""
    if current >= threshold:
        return 0.0
    if slope_per_s <= 0:
        return None
    return (threshold - current) / slope_per_s


class ThermalPredictor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Predict thermal throttling from the temperature slope and warn early."

    def __init__(self):
        self.options = dict()
        self._samples = []      # list of (t, temp)
        self._warned = False

    def on_loaded(self):
        self._threshold = float(self.options.get("threshold_c", 80))
        self._lead = float(self.options.get("lead_seconds", 120))
        self._window = float(self.options.get("window_secs", 180))
        logging.info("[thermal_predictor] loaded (threshold=%.0fC lead=%.0fs)",
                     self._threshold, self._lead)

    # -- core --------------------------------------------------------------------------
    def add_sample(self, temp, now):
        self._samples.append((now, temp))
        cutoff = now - self._window
        self._samples = [s for s in self._samples if s[0] >= cutoff]
        return self.status()

    def slope_per_s(self):
        return linreg_slope(self._samples)

    def status(self):
        if not self._samples:
            return {"temp": None, "slope_per_min": 0.0, "eta_s": None, "state": "ok"}
        current = self._samples[-1][1]
        s = self.slope_per_s()
        eta = predict_time_to(current, s, self._threshold)
        if current >= self._threshold:
            state = "warn"
        elif s <= 0:
            state = "ok"
        elif eta is not None and eta <= self._lead:
            state = "warn"
        else:
            state = "rising"
        return {"temp": current, "slope_per_min": s * 60.0, "eta_s": eta, "state": state}

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        try:
            temp = float(pwnagotchi.temperature())
        except Exception:
            return
        st = self.add_sample(temp, time.time())
        if st["state"] == "warn":
            if not self._warned:
                self._warned = True
                eta = "now" if not st["eta_s"] else "%.0fs" % st["eta_s"]
                logging.warning("[thermal_predictor] throttle predicted in %s (%.0fC, %+.1f C/min)",
                                eta, st["temp"], st["slope_per_min"])
        else:
            self._warned = False

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        st = self.status()
        if st["state"] == "warn":
            return "WARN"
        if st["temp"] is None:
            return "-"
        return "%+.0f/m" % st["slope_per_min"]

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("thermal", LabeledValue(color=BLACK, label="th:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("thermal", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("thermal"):
                ui.remove_element("thermal")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        st = self.status()
        eta = "n/a" if st["eta_s"] is None else ("now" if st["eta_s"] == 0 else "%.0fs" % st["eta_s"])
        return (
            "<html><body><h1>Thermal Predictor</h1><ul>"
            "<li>temp: {temp}</li>"
            "<li>trend: {slope:+.1f} C/min</li>"
            "<li>predicted time to {thr:.0f}C: {eta}</li>"
            "<li>state: {state}</li></ul></body></html>"
        ).format(temp=st["temp"], slope=st["slope_per_min"], thr=self._threshold,
                 eta=eta, state=st["state"])
