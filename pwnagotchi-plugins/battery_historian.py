"""battery_historian — learned runtime curve and aging warning.

UPS plugins show the instantaneous battery percentage and nothing else. This plugin samples
percentage + charge state over time, records each discharge session (how long a given % drop
took), and from that estimates a learned full-charge runtime and current time-to-empty. When
recent discharge sessions drain noticeably faster than earlier ones, it flags likely cell
aging.

It does not talk to specific UPS hardware directly; it reads the standard Linux power-supply
sysfs (which several UPS HAT drivers expose) or a plain file, so it layers on top of whatever
already reports your battery.

Options (main.plugins.battery_historian.*):
    enabled       = true
    source        = "sysfs"    # "sysfs" or "file"
    power_supply  =            # sysfs name (e.g. "bat"); auto-detected if empty
    file_path     =            # for source="file": a file containing the percentage
    data_path     = "/etc/pwnagotchi/battery_historian.json"
    min_drop_pct  = 10         # min % drop for a session to count toward the learned curve
    position      = "0,0"
"""
import json
import logging
import os
import statistics
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_SYS_BASE = "/sys/class/power_supply"


def read_battery(base_dir):
    """Return (pct:int, charging:bool) from a power_supply sysfs dir, or None."""
    try:
        with open(os.path.join(base_dir, "capacity")) as fp:
            pct = int(fp.read().strip())
    except Exception:
        return None
    charging = False
    try:
        with open(os.path.join(base_dir, "status")) as fp:
            charging = fp.read().strip().lower() in ("charging", "full")
    except Exception:
        pass
    return pct, charging


def rate_per_hour(session):
    dropped = session["start_pct"] - session["end_pct"]
    dur_h = session["duration_s"] / 3600.0
    return (dropped / dur_h) if (dur_h > 0 and dropped > 0) else None


def learned_full_runtime_h(history, min_drop=10):
    """Median full 100%->0% runtime (hours) from sessions with a meaningful drop."""
    rates = [r for r in (rate_per_hour(s) for s in history
                         if (s["start_pct"] - s["end_pct"]) >= min_drop) if r]
    if not rates:
        return None
    return 100.0 / statistics.median(rates)


def aging_factor(history, min_drop=10):
    """Recent vs earliest discharge rate. >1 means draining faster now (aging)."""
    rates = [r for r in (rate_per_hour(s) for s in history
                         if (s["start_pct"] - s["end_pct"]) >= min_drop) if r]
    if len(rates) < 4:
        return None
    k = max(1, len(rates) // 3)
    early = statistics.median(rates[:k])
    recent = statistics.median(rates[-k:])
    return (recent / early) if early > 0 else None


class BatteryHistorian(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Learned battery runtime curve and cell-aging warning."

    def __init__(self):
        self.options = dict()
        self._session = None
        self._history = []
        self._last_pct = None
        self._charging = False
        self._path = None

    def on_loaded(self):
        self._source = self.options.get("source", "sysfs")
        self._supply = self.options.get("power_supply") or self._detect_supply()
        self._file_path = self.options.get("file_path")
        self._path = self.options.get("data_path", "/etc/pwnagotchi/battery_historian.json")
        self._min_drop = int(self.options.get("min_drop_pct", 10))
        self._load()
        logging.info("[battery_historian] loaded (source=%s supply=%s)", self._source, self._supply)

    def _detect_supply(self):
        try:
            for name in sorted(os.listdir(_SYS_BASE)):
                tp = os.path.join(_SYS_BASE, name, "type")
                if os.path.exists(tp):
                    with open(tp) as fp:
                        if fp.read().strip().lower() == "battery":
                            return name
        except Exception:
            pass
        return None

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    d = json.load(fp)
                self._history = d.get("history", [])
        except Exception as e:
            logging.debug("[battery_historian] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"history": self._history[-100:]}, fp)
        except Exception as e:
            logging.debug("[battery_historian] save failed: %s", e)

    # -- reading -----------------------------------------------------------------------
    def _read(self):
        if self._source == "file" and self._file_path:
            try:
                with open(self._file_path) as fp:
                    return int(float(fp.read().strip())), False
            except Exception:
                return None
        if self._supply:
            return read_battery(os.path.join(_SYS_BASE, self._supply))
        return None

    # -- core state machine ------------------------------------------------------------
    def update(self, pct, charging, now):
        self._last_pct = pct
        self._charging = charging
        if charging:
            self._close_session()
            return self.current_stats(now)
        # discharging
        if self._session is None:
            self._session = {"start_time": now, "start_pct": pct, "end_pct": pct, "last_time": now}
        elif pct <= self._session["end_pct"]:
            self._session["end_pct"] = pct
            self._session["last_time"] = now
        return self.current_stats(now)

    def _close_session(self):
        s = self._session
        self._session = None
        if not s:
            return
        dur = s["last_time"] - s["start_time"]
        if dur > 0 and (s["start_pct"] - s["end_pct"]) > 0:
            self._history.append({"start_time": s["start_time"], "start_pct": s["start_pct"],
                                  "end_pct": s["end_pct"], "duration_s": dur})
            self._save()

    def current_stats(self, now):
        rate = None
        eta_h = None
        if self._session:
            live = {"start_pct": self._session["start_pct"], "end_pct": self._session["end_pct"],
                    "duration_s": self._session["last_time"] - self._session["start_time"]}
            rate = rate_per_hour(live)
            if rate and self._last_pct is not None:
                eta_h = self._last_pct / rate
        return {"pct": self._last_pct, "charging": self._charging, "rate_per_hr": rate,
                "eta_to_empty_h": eta_h,
                "learned_runtime_h": learned_full_runtime_h(self._history, self._min_drop),
                "aging": aging_factor(self._history, self._min_drop)}

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        reading = self._read()
        if reading:
            self.update(reading[0], reading[1], time.time())

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("battery", LabeledValue(color=BLACK, label="bat:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            pct = self._last_pct
            ui.set("battery", "-" if pct is None else "%d%%%s" % (pct, "+" if self._charging else ""))

    def on_unload(self, ui):
        self._save()
        with ui._lock:
            if ui.has_element("battery"):
                ui.remove_element("battery")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        st = self.current_stats(time.time())
        aging = "unknown" if st["aging"] is None else (
            "%.0f%% faster than when new" % ((st["aging"] - 1) * 100) if st["aging"] > 1.1
            else "healthy")
        learned = "unknown" if st["learned_runtime_h"] is None else "%.1f h" % st["learned_runtime_h"]
        return (
            "<html><body><h1>Battery Historian</h1>"
            "<ul><li>now: {}%{}</li><li>learned full runtime: {}</li>"
            "<li>aging: {}</li><li>discharge sessions recorded: {}</li></ul></body></html>"
        ).format(st["pct"], " (charging)" if st["charging"] else "", learned, aging, len(self._history))
