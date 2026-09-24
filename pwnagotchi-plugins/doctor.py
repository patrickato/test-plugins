"""doctor — a concise "what's wrong, why, and what to do" surface.

Diagnosis on Pwnagotchi is manual log-reading. This plugin scans recent log evidence plus a
couple of live signals (disk free, temperature) against a rule set and reports plain-language
findings: the symptom, the likely cause, and a suggested next action. Shows an issue count on
the display; full findings on the web page.

It reads state only — it never restarts services or changes anything.

Options (main.plugins.doctor.*):
    enabled     = true
    log_path    = "/etc/pwnagotchi/log/pwnagotchi.log"
    log_lines   = 400          # how many trailing log lines to scan
    min_free_mb = 200          # low-disk threshold
    max_temp_c  = 80           # high-temperature threshold
    position    = "0,0"
"""
import logging
import os

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_SEV_RANK = {"high": 0, "warn": 1, "info": 2}

# Log-pattern rules: a line matches when it contains ALL tokens (lowercased).
RULES = [
    {"id": "wifi_driver", "tokens": ["wifi", "error"], "min_count": 5, "severity": "high",
     "symptom": "repeated Wi-Fi errors in the log",
     "cause": "the Wi-Fi driver or monitor interface may be wedged",
     "suggestion": "restart the wlan/monitor interface or reboot; check adapter power/USB"},
    {"id": "bettercap_down", "tokens": ["bettercap", "connection refused"], "min_count": 1,
     "severity": "high", "symptom": "cannot reach bettercap",
     "cause": "bettercap isn't running or its API is unreachable",
     "suggestion": "check/restart bettercap.service"},
    {"id": "pwngrid", "tokens": ["pwngrid", "error"], "min_count": 1, "severity": "warn",
     "symptom": "pwngrid errors",
     "cause": "the pwngrid peer service is unhappy",
     "suggestion": "check pwngrid-peer.service and network reachability"},
    {"id": "bt_tether", "tokens": ["bt-tether", "error"], "min_count": 1, "severity": "warn",
     "symptom": "bluetooth tether errors",
     "cause": "the phone/BT tether pairing or link failed",
     "suggestion": "re-pair the phone or check bt-tether settings"},
    {"id": "crash_loop", "tokens": ["traceback"], "min_count": 3, "severity": "high",
     "symptom": "repeated tracebacks",
     "cause": "something is crashing repeatedly",
     "suggestion": "read the traceback; disable the offending plugin to isolate"},
    {"id": "plugin_load", "tokens": ["error while loading"], "min_count": 1, "severity": "warn",
     "symptom": "a plugin failed to load",
     "cause": "a plugin raised during import/enable",
     "suggestion": "check the named plugin's config and dependencies"},
]


def diagnose(evidence):
    """Pure: evidence dict -> sorted findings list."""
    findings = []
    free = evidence.get("disk_free_mb")
    if free is not None and free < evidence.get("min_free_mb", 200):
        findings.append({"id": "low_disk", "severity": "high",
                         "symptom": "low free disk (%d MB)" % free,
                         "cause": "the SD card is nearly full",
                         "suggestion": "prune captures/logs; see capture_retention"})
    temp = evidence.get("temp_c")
    if temp is not None and temp >= evidence.get("max_temp_c", 80):
        findings.append({"id": "high_temp", "severity": "warn",
                         "symptom": "high temperature (%.0fC)" % temp,
                         "cause": "sustained load or poor cooling",
                         "suggestion": "add cooling; see thermal_predictor/fan_curve"})

    lines = (evidence.get("log", "") or "").lower().splitlines()
    for rule in RULES:
        count = sum(1 for ln in lines if all(tok in ln for tok in rule["tokens"]))
        if count >= rule["min_count"]:
            f = {k: rule[k] for k in ("id", "severity", "symptom", "cause", "suggestion")}
            f["count"] = count
            findings.append(f)

    findings.sort(key=lambda f: _SEV_RANK.get(f["severity"], 9))
    return findings


class Doctor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Read-only health diagnosis: symptom, likely cause, suggested action."

    def __init__(self):
        self.options = dict()
        self._findings = []

    def on_loaded(self):
        self._log_path = self.options.get("log_path", "/etc/pwnagotchi/log/pwnagotchi.log")
        self._log_lines = int(self.options.get("log_lines", 400))
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._max_temp_c = float(self.options.get("max_temp_c", 80))
        logging.info("[doctor] loaded")

    # -- evidence gathering ------------------------------------------------------------
    def _tail_log(self):
        try:
            with open(self._log_path, "rt", errors="ignore") as fp:
                return "".join(fp.readlines()[-self._log_lines:])
        except Exception:
            return ""

    def _disk_free_mb(self):
        try:
            import shutil
            return int(shutil.disk_usage("/").free / (1024 * 1024))
        except Exception:
            return None

    def _temp(self):
        try:
            return float(pwnagotchi.temperature())
        except Exception:
            return None

    def run(self):
        evidence = {"log": self._tail_log(), "disk_free_mb": self._disk_free_mb(),
                    "temp_c": self._temp(), "min_free_mb": self._min_free_mb,
                    "max_temp_c": self._max_temp_c}
        self._findings = diagnose(evidence)
        if self._findings:
            logging.info("[doctor] %d finding(s): %s", len(self._findings),
                         ", ".join(f["id"] for f in self._findings))
        return self._findings

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.run()

    def on_epoch(self, agent, epoch, epoch_data):
        if epoch % 30 == 0:
            self.run()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        if not self._findings:
            return "OK"
        return "%d!" % len(self._findings)

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("doctor", LabeledValue(color=BLACK, label="dr:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("doctor", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("doctor"):
                ui.remove_element("doctor")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        self.run()
        if not self._findings:
            body = "<p>No issues detected. 🎉</p>"
        else:
            body = "<table border=1><tr><th>severity</th><th>symptom</th><th>likely cause</th>" \
                   "<th>suggested action</th></tr>" + "".join(
                "<tr><td>{severity}</td><td>{symptom}</td><td>{cause}</td><td>{suggestion}</td></tr>"
                .format(**f) for f in self._findings) + "</table>"
        return "<html><body><h1>Doctor</h1>{}</body></html>".format(body)
