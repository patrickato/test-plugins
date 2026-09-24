"""captive_portal — know when the link is captive or dead.

Pwnagotchi's "internet available" can be true while a captive portal (hotel/airport Wi-Fi)
actually blocks everything, so uploaders retry forever and waste attempts. This probes a
known "generate_204" endpoint and classifies the link as online / captive / offline, and
exposes that so other plugins can skip pointless uploads.

Options (main.plugins.captive_portal.*):
    enabled         = true
    check_url       = "http://connectivitycheck.gstatic.com/generate_204"
    expected_status = 204
    interval_secs   = 60
    position        = "0,0"

Requires: none (Python standard library; uses urllib).
"""
import logging
import time
import urllib.error
import urllib.request

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def classify_response(status, body, expected_status=204):
    """online (expected empty 204), captive (unexpected content), or offline (no response)."""
    if status is None:
        return "offline"
    if status == expected_status and not (body or "").strip():
        return "online"
    return "captive"


class CaptivePortal(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Detect captive portals / dead links so uploaders don't waste attempts."

    def __init__(self):
        self.options = dict()
        self._status = "unknown"
        self._last_check = 0

    def on_loaded(self):
        self._url = self.options.get("check_url",
                                     "http://connectivitycheck.gstatic.com/generate_204")
        self._expected = int(self.options.get("expected_status", 204))
        self._interval = float(self.options.get("interval_secs", 60))
        logging.info("[captive_portal] loaded (url=%s)", self._url)

    # -- core --------------------------------------------------------------------------
    def probe(self):
        status, body = None, ""
        try:
            req = urllib.request.Request(self._url, headers={"User-Agent": "pwnagotchi"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.getcode()
                body = resp.read(2048).decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:
            logging.debug("[captive_portal] probe failed: %s", e)
        self._status = classify_response(status, body, self._expected)
        return self._status

    def is_online(self):
        return self._status == "online"

    def _maybe_probe(self, now=None):
        now = now if now is not None else time.time()
        if (now - self._last_check) >= self._interval:
            self._last_check = now
            self.probe()

    # -- events ------------------------------------------------------------------------
    def on_internet_available(self, agent):
        # Pwnagotchi thinks internet is up — verify it isn't a captive portal.
        self.probe()

    def on_epoch(self, agent, epoch, epoch_data):
        self._maybe_probe()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        return {"online": "on", "captive": "cap", "offline": "off"}.get(self._status, "-")

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("captive", LabeledValue(color=BLACK, label="net:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("captive", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("captive"):
                ui.remove_element("captive")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>Captive Portal Check</h1>"
                "<p>status: <b>{}</b></p><p>probe url: {}</p></body></html>").format(
                    self._status, self._url)
