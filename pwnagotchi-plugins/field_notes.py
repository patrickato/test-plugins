"""field_notes — jot a note to the current session/location.

Attach quick text notes ("cool spot", "my house", "test rig") from the plugin web page or a
phone. Each note is timestamped and, when a gpsd fix is available, stamped with lat/lon, so
you can review them later alongside captures and tracks. A small counter shows how many
notes you've made this session.

Options (main.plugins.field_notes.*):
    enabled   = true
    data_path = "/etc/pwnagotchi/field_notes.json"
    gpsd_host = "127.0.0.1"
    gpsd_port = 2947
    position  = "0,0"
"""
import html
import json
import logging
import os
import socket
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class FieldNotes(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Attach timestamped, geo-stamped notes to the current session."

    def __init__(self):
        self.options = dict()
        self._notes = []
        self._path = None

    def on_loaded(self):
        self._path = self.options.get("data_path", "/etc/pwnagotchi/field_notes.json")
        self._gpsd_host = self.options.get("gpsd_host", "127.0.0.1")
        self._gpsd_port = int(self.options.get("gpsd_port", 2947))
        self._load()
        logging.info("[field_notes] loaded (%d notes)", len(self._notes))

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    data = json.load(fp)
                if isinstance(data, list):
                    self._notes = data
        except Exception as e:
            logging.debug("[field_notes] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump(self._notes, fp, indent=2)
        except Exception as e:
            logging.debug("[field_notes] save failed: %s", e)

    # -- core --------------------------------------------------------------------------
    def add_note(self, text, lat=None, lon=None, ts=None):
        text = (str(text) if text is not None else "").strip()
        if not text:
            return None
        ts = ts if ts is not None else time.time()
        record = {
            "id": (max((n.get("id", 0) for n in self._notes), default=0) + 1),
            "ts": ts,
            "when": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            "text": text[:500],
            "lat": lat,
            "lon": lon,
        }
        self._notes.append(record)
        self._save()
        logging.info("[field_notes] noted: %s", record["text"])
        return record

    def _read_gps(self):
        try:
            with socket.create_connection((self._gpsd_host, self._gpsd_port), timeout=1.5) as s:
                s.sendall(b'?WATCH={"enable":true,"json":true};\n')
                s.settimeout(1.5)
                deadline = time.time() + 2
                buf = b""
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
        except Exception:
            pass
        return None

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("field_notes", LabeledValue(color=BLACK, label="notes:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("field_notes", str(len(self._notes)))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("field_notes"):
                ui.remove_element("field_notes")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        # Add via POST form field 'text' or GET ?note=...
        text = None
        try:
            if request is not None:
                if getattr(request, "method", "GET") == "POST":
                    text = request.form.get("text")
                else:
                    text = request.args.get("note")
        except Exception:
            text = None
        if text:
            pos = self._read_gps()
            self.add_note(text, lat=pos[0] if pos else None, lon=pos[1] if pos else None)

        items = "".join(
            "<li>[{}] {}{}</li>".format(
                html.escape(n.get("when", "")),
                html.escape(n.get("text", "")),
                "" if n.get("lat") is None else " ({:.5f},{:.5f})".format(n["lat"], n["lon"]),
            )
            for n in reversed(self._notes)
        ) or "<li>(no notes yet)</li>"
        return (
            "<html><body><h1>Field Notes</h1>"
            "<form method='POST'><input name='text' size=40 autofocus>"
            "<button type='submit'>Add</button></form>"
            "<p>{} note(s). Tip: /plugins/field_notes/?note=hello also works.</p>"
            "<ul>{}</ul></body></html>"
        ).format(len(self._notes), items)
