"""why_no_handshakes — troubleshoot the #1 complaint.

"I'm not getting any handshakes" is the most common Pwnagotchi question. This checks the few
things that actually matter — is there a monitor-mode interface, are any APs in range, are
there clients to capture from, and do captures already exist — and tells you the likely cause
and what to do. Read-only.

Options (main.plugins.why_no_handshakes.*):
    enabled    = true
    handshakes = "/root/handshakes"
    position   = "0,0"

Requires: none (uses `iw`/`ip`, usually present). Read-only.
"""
import glob
import logging
import os
import subprocess

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_SEV_RANK = {"high": 0, "warn": 1, "info": 2}


def iw_has_monitor(iw_text):
    current_type = None
    for raw in (iw_text or "").splitlines():
        line = raw.strip()
        if line.startswith("Interface "):
            if line.split(None, 1)[1].endswith("mon"):
                return True
        elif line.startswith("type ") and line.split(None, 1)[1] == "monitor":
            return True
    return current_type == "monitor"


def analyze(evidence):
    pcaps = evidence.get("pcap_count", 0)
    findings = []
    if pcaps > 0:
        findings.append({"severity": "info",
                         "symptom": "capturing is working (%d handshake file(s) present)" % pcaps,
                         "cause": "handshakes are being written",
                         "suggestion": "nothing to fix — see capture_grader for quality"})
        return findings

    if not evidence.get("monitor_present", False):
        findings.append({"severity": "high", "symptom": "no monitor-mode interface found",
                         "cause": "the Wi-Fi adapter isn't in monitor mode (or isn't capable)",
                         "suggestion": "confirm the adapter supports monitor mode and bettercap's "
                                       "interface is set correctly"})
    if evidence.get("ap_count", 0) == 0:
        findings.append({"severity": "high", "symptom": "no access points seen recently",
                         "cause": "recon isn't running, channels are restricted, or antenna issue",
                         "suggestion": "check the antenna, widen the channel list, and verify "
                                       "bettercap/recon is active"})
    elif evidence.get("client_count", 0) == 0:
        findings.append({"severity": "warn", "symptom": "APs seen but no clients",
                         "cause": "handshakes need a device (re)connecting to an AP",
                         "suggestion": "be patient, move to a busier area, and make sure deauth "
                                       "(assoc) is enabled in your personality"})
    if (evidence.get("monitor_present") and evidence.get("ap_count", 0) > 0
            and evidence.get("client_count", 0) > 0):
        findings.append({"severity": "warn", "symptom": "conditions look fine but no captures yet",
                         "cause": "it may just need time, or the handshake path is misconfigured",
                         "suggestion": "give it time; verify bettercap.handshakes points at your "
                                       "handshakes dir"})
    if not findings:
        findings.append({"severity": "info", "symptom": "still gathering data",
                         "cause": "", "suggestion": "let it run a few minutes"})
    findings.sort(key=lambda f: _SEV_RANK.get(f["severity"], 9))
    return findings


class WhyNoHandshakes(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Troubleshoot why no handshakes are being captured (read-only)."

    def __init__(self):
        self.options = dict()
        self._ap_count = 0
        self._client_count = 0
        self._findings = []

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        logging.info("[why_no_handshakes] loaded")

    # -- gathering ---------------------------------------------------------------------
    @staticmethod
    def _run(cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)

    def _monitor_present(self, runner=None):
        runner = runner or self._run
        try:
            return iw_has_monitor(runner(["iw", "dev"]))
        except Exception:
            return False

    def _pcap_count(self):
        try:
            return len(glob.glob(os.path.join(self._handshakes, "*.pcap")))
        except Exception:
            return 0

    def refresh(self, runner=None):
        evidence = {"monitor_present": self._monitor_present(runner),
                    "pcap_count": self._pcap_count(),
                    "ap_count": self._ap_count, "client_count": self._client_count}
        self._findings = analyze(evidence)
        return self._findings

    # -- events ------------------------------------------------------------------------
    def on_wifi_update(self, agent, access_points):
        aps = [a for a in (access_points or []) if isinstance(a, dict)]
        self._ap_count = len(aps)
        self._client_count = sum(len(a.get("clients", []) or []) for a in aps)

    def on_ready(self, agent):
        self.refresh()

    def on_epoch(self, agent, epoch, epoch_data):
        if epoch % 20 == 0:
            self.refresh()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        if self._findings and self._findings[0]["severity"] == "info" and "working" in self._findings[0]["symptom"]:
            return "ok"
        issues = sum(1 for f in self._findings if f["severity"] in ("high", "warn"))
        return "%d?" % issues if issues else "ok"

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("hswhy", LabeledValue(color=BLACK, label="hs?:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("hswhy", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("hswhy"):
                ui.remove_element("hswhy")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        self.refresh()
        rows = "".join(
            "<tr><td>{severity}</td><td>{symptom}</td><td>{cause}</td><td>{suggestion}</td></tr>"
            .format(**f) for f in self._findings)
        return ("<html><body><h1>Why No Handshakes?</h1>"
                "<table border=1><tr><th>severity</th><th>symptom</th><th>cause</th>"
                "<th>what to do</th></tr>{}</table></body></html>").format(rows)
