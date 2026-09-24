"""rtl433_ambient — passively log 433 MHz sensors via an RTL-SDR.

If an RTL-SDR is attached, this runs ``rtl_433 -F json`` in the background and aggregates the
ambient devices it hears (weather stations, TPMS, remote thermometers, etc.) by model+id, with
sighting counts, last-seen, and the latest readings. Pure environment awareness — it only
listens.

Guarded: if the ``rtl_433`` binary or an SDR isn't present, the plugin idles quietly.

Options (main.plugins.rtl433_ambient.*):
    enabled     = true
    rtl_433_bin = "rtl_433"
    extra_args  = []            # extra CLI args, e.g. ["-f","433.92M","-R","40"]
    max_devices = 200           # cap on distinct devices tracked
    position    = "0,0"

Requires: the `rtl_433` binary on PATH and an RTL-SDR dongle.
"""
import json
import logging
import shutil
import subprocess
import threading
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_READING_KEYS = ("temperature_C", "temperature_F", "humidity", "battery_ok",
                 "wind_avg_km_h", "pressure_hPa", "pressure_kPa", "moisture",
                 "tire_pressure_kPa", "rain_mm")


def device_key(event):
    """Stable key for a device from an rtl_433 JSON event, or None."""
    if not isinstance(event, dict):
        return None
    model = event.get("model")
    if not model:
        return None
    for k in ("id", "sensor_id", "channel", "device"):
        if k in event and event[k] is not None:
            return "%s/%s" % (model, event[k])
    return str(model)


def extract_readings(event):
    return {k: event[k] for k in _READING_KEYS if k in event}


class RTL433Ambient(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Passively log 433 MHz ambient sensors via an RTL-SDR."

    def __init__(self):
        self.options = dict()
        self._devices = {}
        self._events = 0
        self._proc = None
        self._thread = None
        self._running = False
        self._available = False

    def on_loaded(self):
        self._bin = self.options.get("rtl_433_bin", "rtl_433")
        self._extra = list(self.options.get("extra_args", []) or [])
        self._max_devices = int(self.options.get("max_devices", 200))
        self._available = shutil.which(self._bin) is not None
        logging.info("[rtl433_ambient] loaded (available=%s)", self._available)

    # -- core (testable) ---------------------------------------------------------------
    def update(self, event, now=None):
        key = device_key(event)
        if not key:
            return None
        now = now if now is not None else time.time()
        d = self._devices.get(key)
        if d is None:
            if len(self._devices) >= self._max_devices:
                return None
            d = {"count": 0, "last": {}, "last_seen": now}
            self._devices[key] = d
        d["count"] += 1
        d["last_seen"] = now
        readings = extract_readings(event)
        if readings:
            d["last"] = readings
        self._events += 1
        return key

    def summary(self):
        return {"devices": len(self._devices), "events": self._events}

    # -- subprocess reader (guarded, not unit-tested) ----------------------------------
    def on_ready(self, agent):
        if not self._available:
            logging.warning("[rtl433_ambient] '%s' not found on PATH; idling", self._bin)
            return
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True, name="rtl433")
        self._thread.start()

    def _reader_loop(self):
        cmd = [self._bin, "-F", "json"] + self._extra
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                          text=True, bufsize=1)
        except Exception as e:
            logging.warning("[rtl433_ambient] could not start %s: %s", cmd, e)
            return
        try:
            for line in self._proc.stdout:
                if not self._running:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    self.update(json.loads(line))
                except Exception:
                    continue
        except Exception as e:
            logging.debug("[rtl433_ambient] reader stopped: %s", e)

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("rtl433", LabeledValue(color=BLACK, label="433:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("rtl433", "%dd" % len(self._devices) if self._devices else ("-" if self._available else "off"))

    def on_unload(self, ui):
        self._running = False
        try:
            if self._proc:
                self._proc.terminate()
        except Exception:
            pass
        with ui._lock:
            if ui.has_element("rtl433"):
                ui.remove_element("rtl433")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(k, d["count"], d["last"])
            for k, d in sorted(self._devices.items(), key=lambda kv: -kv[1]["count"])
        ) or "<tr><td colspan=3>nothing heard yet</td></tr>"
        return (
            "<html><body><h1>rtl_433 Ambient</h1><p>{} device(s), {} event(s).</p>"
            "<table border=1><tr><th>device</th><th>count</th><th>last readings</th></tr>{}"
            "</table></body></html>"
        ).format(len(self._devices), self._events, rows)
