"""boot_post — a power-on self-test card.

At startup, run a handful of cheap checks (clock sane, disk free, temperature, handshake
dir writable, default route present) and surface a single "POST n/m" summary on the display,
with the full breakdown at the plugin's web page. Gives you a one-glance "did everything come
up cleanly?" instead of reading logs.

Options (main.plugins.boot_post.*):
    enabled        = true
    handshakes     = "/root/handshakes"   # capture dir to check is writable
    min_free_mb    = 200                    # warn/fail threshold for free space on /
    max_temp_c     = 80                     # warn threshold for CPU temperature
    position       = "0,0"                  # UI position "x,y"
"""
import logging
import os
import shutil
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

OK, WARN, FAIL = "ok", "warn", "fail"


class BootPost(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Power-on self-test: one-glance summary that everything came up cleanly."

    def __init__(self):
        self.options = dict()
        self._results = []
        self._ran = False

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._max_temp_c = float(self.options.get("max_temp_c", 80))
        logging.info("[boot_post] loaded")

    def on_ready(self, agent):
        self._results = self.run_post()
        self._ran = True
        ok = sum(1 for r in self._results if r["status"] == OK)
        logging.info("[boot_post] POST %d/%d ok: %s", ok, len(self._results),
                     ", ".join("%s=%s" % (r["name"], r["status"]) for r in self._results))

    # -- checks (each returns a result dict; all injectable/guarded) --------------------
    def run_post(self):
        return [
            self.check_clock(),
            self.check_disk(),
            self.check_temp(),
            self.check_handshakes(),
            self.check_network(),
        ]

    def check_clock(self, now=None):
        t = now if now is not None else time.time()
        year = time.gmtime(t).tm_year
        if year >= 2024:
            return self._r("clock", OK, str(year))
        return self._r("clock", FAIL, "unset? %s" % year)

    def check_disk(self, path="/"):
        try:
            free_mb = shutil.disk_usage(path).free / (1024 * 1024)
        except Exception as e:
            return self._r("disk", WARN, "unknown (%s)" % e)
        status = OK if free_mb >= self._min_free_mb else FAIL
        return self._r("disk", status, "%d MB free" % free_mb)

    def check_temp(self):
        try:
            temp = float(pwnagotchi.temperature())
        except Exception as e:
            return self._r("temp", WARN, "unknown (%s)" % e)
        status = OK if temp < self._max_temp_c else WARN
        return self._r("temp", status, "%.0fC" % temp)

    def check_handshakes(self, path=None):
        path = path or self._handshakes
        try:
            if not os.path.isdir(path):
                return self._r("captures", WARN, "no dir")
            return self._r("captures", OK if os.access(path, os.W_OK) else FAIL,
                           "writable" if os.access(path, os.W_OK) else "read-only")
        except Exception as e:
            return self._r("captures", WARN, "unknown (%s)" % e)

    def check_network(self):
        try:
            with open("/proc/net/route") as fp:
                for line in fp.readlines()[1:]:
                    fields = line.strip().split()
                    if len(fields) >= 2 and fields[1] == "00000000":  # default route
                        return self._r("route", OK, fields[0])
            return self._r("route", WARN, "no default route")
        except Exception as e:
            return self._r("route", WARN, "unknown (%s)" % e)

    @staticmethod
    def _r(name, status, detail):
        return {"name": name, "status": status, "detail": detail}

    def summary(self):
        if not self._results:
            return "…"
        ok = sum(1 for r in self._results if r["status"] == OK)
        return "%d/%d" % (ok, len(self._results))

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("boot_post", LabeledValue(color=BLACK, label="POST:", value="…",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("boot_post", self.summary())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("boot_post"):
                ui.remove_element("boot_post")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(r["name"], r["status"], r["detail"])
            for r in self._results
        ) or "<tr><td colspan=3>POST not run yet</td></tr>"
        return (
            "<html><body><h1>Boot POST</h1><p>Summary: {}</p>"
            "<table border=1><tr><th>check</th><th>status</th><th>detail</th></tr>{}"
            "</table></body></html>"
        ).format(self.summary(), rows)
