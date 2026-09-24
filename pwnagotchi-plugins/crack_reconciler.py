"""crack_reconciler — merge cracking results back onto local captures.

Cracking results live in separate silos (wpa-sec "found" lists, a local hashcat potfile,
OnlineHashCrack exports). Nothing on the device reconciles them, so solved handshakes get
re-uploaded forever. This plugin ingests result files, maps cracked BSSIDs to your local
captures, and marks solved ones with a `.cracked` sidecar so uploaders can skip them.

It parses two common formats:
  * wpa-sec "found" lines:  ``bssid:station:essid:password``
  * hashcat 22000 potfile:  ``WPA*02*mic*apmac*stamac*essid*...:password``

Options (main.plugins.crack_reconciler.*):
    enabled       = true
    handshakes    = "/root/handshakes"
    potfiles      = ["/root/handshakes/wpa-sec.cracked.potfile", "/root/hashcat.potfile"]
    write_sidecar = true
    position      = "0,0"
"""
import glob
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_HEX = set("0123456789abcdef")


def normalize_hex(value):
    return "".join(c for c in str(value or "").lower() if c in _HEX)


def bssid_from_filename(name):
    base = os.path.basename(name)
    for suffix in (".pcapng", ".pcap"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    for token in reversed(base.split("_")):
        h = normalize_hex(token)
        if len(h) == 12:
            return h
    return None


def parse_results(text):
    """Return {bssid_hex: password} parsed from wpa-sec or hashcat-22000 potfile text."""
    cracked = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("WPA") and "*" in line and ":" in line:
            hashpart, pw = line.rsplit(":", 1)
            parts = hashpart.split("*")
            if len(parts) > 3:
                b = normalize_hex(parts[3])
                if len(b) == 12 and pw:
                    cracked[b] = pw
        else:
            fields = line.split(":")
            if len(fields) >= 4:
                b = normalize_hex(fields[0])
                if len(b) == 12 and fields[-1]:
                    cracked[b] = fields[-1]
    return cracked


class CrackReconciler(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Reconcile wpa-sec / hashcat results onto local captures; mark solved ones."

    def __init__(self):
        self.options = dict()
        self._cracked = {}      # bssid -> password
        self._report = []       # [{file, bssid, solved, password}]

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._potfiles = list(self.options.get("potfiles", []) or [])
        self._write_sidecar = bool(self.options.get("write_sidecar", True))
        logging.info("[crack_reconciler] loaded (%d potfile source(s))", len(self._potfiles))

    # -- core --------------------------------------------------------------------------
    def ingest(self, text):
        self._cracked.update(parse_results(text))
        return len(self._cracked)

    def load_potfiles(self):
        for p in self._potfiles:
            try:
                if os.path.exists(p):
                    with open(p, "rt", errors="ignore") as fp:
                        self.ingest(fp.read())
            except Exception as e:
                logging.debug("[crack_reconciler] could not read %s: %s", p, e)

    def is_solved(self, bssid):
        return normalize_hex(bssid) in self._cracked

    def reconcile(self):
        self.load_potfiles()
        report = []
        files = glob.glob(os.path.join(self._handshakes, "*.pcap")) + \
            glob.glob(os.path.join(self._handshakes, "*.pcapng"))
        for f in sorted(files):
            b = bssid_from_filename(f)
            if not b:
                continue
            solved = b in self._cracked
            entry = {"file": os.path.basename(f), "bssid": b, "solved": solved,
                     "password": self._cracked.get(b) if solved else None}
            report.append(entry)
            if solved and self._write_sidecar:
                try:
                    with open(f + ".cracked", "w") as fp:
                        fp.write("%s:%s\n" % (b, self._cracked[b]))
                except Exception as e:
                    logging.debug("[crack_reconciler] sidecar failed: %s", e)
        self._report = report
        logging.info("[crack_reconciler] %d/%d captures solved",
                     sum(1 for e in report if e["solved"]), len(report))
        return report

    # -- events ------------------------------------------------------------------------
    def on_internet_available(self, agent):
        # A hook point for future remote fetch; for now just re-run local reconciliation.
        self.reconcile()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        solved = sum(1 for e in self._report if e["solved"])
        return "%d/%d" % (solved, len(self._report))

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("cracked", LabeledValue(color=BLACK, label="solved:", value="0/0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("cracked", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("cracked"):
                ui.remove_element("cracked")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                e["file"], e["bssid"], "SOLVED" if e["solved"] else "-")
            for e in self._report
        ) or "<tr><td colspan=3>run reconcile first</td></tr>"
        return (
            "<html><body><h1>Crack Reconciler</h1><p>{}</p>"
            "<table border=1><tr><th>file</th><th>bssid</th><th>status</th></tr>{}"
            "</table></body></html>"
        ).format(self._ui_value(), rows)
