"""auto_timezone — set the system timezone from GPS location.

Keeps timestamps and time-of-day features correct while travelling. Reads a fix from gpsd,
resolves the timezone, and applies it with ``timedatectl`` only when it actually changes.
If the optional ``timezonefinder`` package is installed it resolves the precise IANA zone;
otherwise it falls back to a coarse longitude-based ``Etc/GMT`` offset (offline, no DST).

Options (main.plugins.auto_timezone.*):
    enabled          = true
    apply            = true       # false = log the target zone but don't change the system
    min_interval_min = 30         # minimum minutes between checks
    gpsd_host        = "127.0.0.1"
    gpsd_port        = 2947
    latitude         =            # optional manual override (skips gpsd)
    longitude        =
    position         = "0,0"      # UI position "x,y"
"""
import json
import logging
import socket
import subprocess
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def lon_to_offset(lon):
    off = int(round(float(lon) / 15.0))
    return max(-12, min(12, off))


def offset_to_etc_zone(offset):
    if offset == 0:
        return "Etc/UTC"
    # POSIX Etc/GMT signs are inverted: UTC+5 -> "Etc/GMT-5".
    return "Etc/GMT{:+d}".format(-offset)


def resolve_zone(lat, lon):
    """Precise IANA zone via timezonefinder if available, else coarse Etc/GMT fallback."""
    try:
        from timezonefinder import TimezoneFinder
        z = TimezoneFinder().timezone_at(lat=float(lat), lng=float(lon))
        if z:
            return z
    except Exception:
        pass
    return offset_to_etc_zone(lon_to_offset(lon))


class AutoTimezone(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Set the system timezone from GPS location (timezonefinder or Etc/GMT fallback)."

    def __init__(self):
        self.options = dict()
        self._last_check = 0
        self._status = "-"

    def on_loaded(self):
        self._apply = bool(self.options.get("apply", True))
        self._interval = float(self.options.get("min_interval_min", 30)) * 60.0
        self._gpsd_host = self.options.get("gpsd_host", "127.0.0.1")
        self._gpsd_port = int(self.options.get("gpsd_port", 2947))
        self._manual = (self.options.get("latitude"), self.options.get("longitude"))
        logging.info("[auto_timezone] loaded (apply=%s)", self._apply)

    # -- timezone application ----------------------------------------------------------
    @staticmethod
    def _current_zone():
        try:
            with open("/etc/timezone") as fp:
                return fp.read().strip()
        except Exception:
            return None

    def apply_zone(self, zone, runner=None, current=None):
        """Apply `zone` via timedatectl. Returns True if a change was made."""
        if current is None:
            current = self._current_zone()
        if zone == current:
            self._status = zone
            return False
        if not self._apply:
            logging.info("[auto_timezone] would set timezone -> %s (apply=false)", zone)
            self._status = zone + "?"
            return False
        runner = runner or (lambda cmd: subprocess.run(cmd, check=True))
        try:
            runner(["timedatectl", "set-timezone", zone])
            logging.info("[auto_timezone] timezone set -> %s", zone)
            self._status = zone
            return True
        except Exception as e:
            logging.warning("[auto_timezone] failed to set timezone %s: %s", zone, e)
            return False

    # -- gps ---------------------------------------------------------------------------
    def _read_gps(self):
        lat, lon = self._manual
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        try:
            with socket.create_connection((self._gpsd_host, self._gpsd_port), timeout=2) as s:
                s.sendall(b'?WATCH={"enable":true,"json":true};\n')
                s.settimeout(2)
                buf = b""
                deadline = time.time() + 3
                while time.time() < deadline:
                    buf += s.recv(4096)
                    for line in buf.split(b"\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        if obj.get("class") == "TPV" and "lat" in obj and "lon" in obj:
                            return float(obj["lat"]), float(obj["lon"])
        except Exception as e:
            logging.debug("[auto_timezone] gpsd read failed: %s", e)
        return None

    def _tick(self, force=False):
        now = time.time()
        if not force and (now - self._last_check) < self._interval:
            return
        self._last_check = now
        pos = self._read_gps()
        if not pos:
            return
        zone = resolve_zone(pos[0], pos[1])
        self.apply_zone(zone)

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self._tick(force=True)

    def on_epoch(self, agent, epoch, epoch_data):
        self._tick()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("auto_tz", LabeledValue(color=BLACK, label="tz:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("auto_tz", self._status.split("/")[-1])

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("auto_tz"):
                ui.remove_element("auto_tz")

    def on_webhook(self, path, request):
        return "<html><body><h1>Auto Timezone</h1><p>Current target: {}</p></body></html>".format(
            self._status)
