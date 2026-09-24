"""capture_grader — grade each capture so you only keep/upload crackable ones.

Uploaders fire on every capture, including dead ones. This plugin grades a capture by how
much of the WPA 4-way handshake it contains (number of EAPOL frames) and marks whether it's
plausibly crackable. It writes a small `.grade` sidecar next to each capture and shows the
last grade + a running tally on the display.

Grading is a fast, dependency-free byte heuristic (counts EAPOL ethertype 0x888e). It is a
triage signal, not a cracking guarantee; a future scapy-based analyzer could refine PMKID /
beacon detection.

Options (main.plugins.capture_grader.*):
    enabled       = true
    handshakes    = "/root/handshakes"
    write_sidecar = true          # write <capture>.grade files
    position      = "0,0"
"""
import glob
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def count_eapol(path):
    try:
        with open(path, "rb") as fp:
            return fp.read().count(b"\x88\x8e")
    except Exception:
        return 0


def classify(eapol_frames):
    """Map EAPOL-frame count to a grade + crackability.

    >=3 near-complete/complete 4-way -> A; 2 usable pair -> B; 1 partial -> C; 0 -> F.
    """
    if eapol_frames >= 3:
        grade = "A"
    elif eapol_frames == 2:
        grade = "B"
    elif eapol_frames == 1:
        grade = "C"
    else:
        grade = "F"
    return {"eapol": eapol_frames, "grade": grade, "crackable": eapol_frames >= 2}


def grade_file(path):
    result = classify(count_eapol(path))
    result["file"] = os.path.basename(path)
    return result


class CaptureGrader(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Grade captures by handshake completeness; flag crackable vs junk."

    def __init__(self):
        self.options = dict()
        self._counts = {"A": 0, "B": 0, "C": 0, "F": 0}
        self._last = None

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._write_sidecar = bool(self.options.get("write_sidecar", True))
        logging.info("[capture_grader] loaded")

    # -- core --------------------------------------------------------------------------
    def grade(self, filename):
        result = grade_file(filename)
        self._last = result
        self._counts[result["grade"]] = self._counts.get(result["grade"], 0) + 1
        if self._write_sidecar:
            try:
                with open(filename + ".grade", "w") as fp:
                    fp.write("%s eapol=%d crackable=%s\n" % (
                        result["grade"], result["eapol"], result["crackable"]))
            except Exception as e:
                logging.debug("[capture_grader] sidecar write failed: %s", e)
        logging.info("[capture_grader] %s -> %s (eapol=%d, crackable=%s)",
                     result["file"], result["grade"], result["eapol"], result["crackable"])
        return result

    def sweep(self):
        files = glob.glob(os.path.join(self._handshakes, "*.pcap")) + \
            glob.glob(os.path.join(self._handshakes, "*.pcapng"))
        return [grade_file(f) for f in sorted(files)]

    # -- events ------------------------------------------------------------------------
    def on_handshake(self, agent, filename, access_point, client_station):
        self.grade(filename)

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        if not self._last:
            return "-"
        return "%s(%dok)" % (self._last["grade"], self._counts["A"] + self._counts["B"])

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("grade", LabeledValue(color=BLACK, label="grade:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("grade", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("grade"):
                ui.remove_element("grade")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        graded = self.sweep()
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                g["file"], g["grade"], g["eapol"], "yes" if g["crackable"] else "no")
            for g in graded
        ) or "<tr><td colspan=4>no captures</td></tr>"
        crackable = sum(1 for g in graded if g["crackable"])
        return (
            "<html><body><h1>Capture Grader</h1>"
            "<p>{} capture(s), {} crackable.</p>"
            "<table border=1><tr><th>file</th><th>grade</th><th>eapol</th><th>crackable</th></tr>"
            "{}</table></body></html>"
        ).format(len(graded), crackable, rows)
