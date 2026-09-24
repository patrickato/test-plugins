"""own_network_allowlist — mark the owner's own APs as authorized practice.

Pwnagotchi has no first-class notion of "this is my own gear." This plugin lets you list
your home/lab BSSIDs and/or SSIDs; handshakes captured from them are tagged as authorized
practice (a sibling ``.own`` marker file plus a JSON ledger entry) and kept separate from
ordinary field logs. A small display counter shows how many of your own networks are
currently in range.

Nothing is deleted or moved — tagging is additive and non-destructive.

Options (main.plugins.own_network_allowlist.*):
    enabled   = true
    bssids    = ["aa:bb:cc:dd:ee:ff", ...]   # your own AP MACs (any separator/case)
    ssids     = ["MyHomeWifi", ...]          # your own SSIDs (exact, case-insensitive)
    data_path = "/etc/pwnagotchi/own_network_allowlist.json"   # ledger location
    position  = "0,0"                         # UI position "x,y"
"""
import json
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def normalize_mac(value):
    """Lowercase a MAC and strip separators so 'AA-BB..' == 'aabb..' == 'aa:bb:..'."""
    if not value:
        return ""
    keep = "0123456789abcdef"
    return "".join(c for c in str(value).lower() if c in keep)


class OwnNetworkAllowlist(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Tag the owner's own APs as authorized practice; keep them out of field logs."

    def __init__(self):
        self.options = dict()
        self._own_macs = set()
        self._own_ssids = set()
        self._seen_now = set()   # own bssids currently in range (this scan)
        self._ledger_path = None

    # -- lifecycle ---------------------------------------------------------------------
    def on_loaded(self):
        self._own_macs = {normalize_mac(m) for m in self.options.get("bssids", []) if m}
        self._own_ssids = {str(s).strip().lower() for s in self.options.get("ssids", []) if s}
        self._ledger_path = self.options.get(
            "data_path", "/etc/pwnagotchi/own_network_allowlist.json"
        )
        logging.info(
            "[own_network_allowlist] loaded: %d MAC(s), %d SSID(s)",
            len(self._own_macs), len(self._own_ssids),
        )

    # -- matching ----------------------------------------------------------------------
    def is_own(self, ap):
        """True if a bettercap AP dict (keys 'mac'/'hostname') is on the allowlist."""
        if not isinstance(ap, dict):
            return False
        if normalize_mac(ap.get("mac")) in self._own_macs:
            return True
        hostname = ap.get("hostname")
        if hostname and str(hostname).strip().lower() in self._own_ssids:
            return True
        return False

    # -- events ------------------------------------------------------------------------
    def on_wifi_update(self, agent, access_points):
        seen = set()
        for ap in access_points or []:
            if self.is_own(ap):
                mac = normalize_mac(ap.get("mac"))
                if mac:
                    seen.add(mac)
        self._seen_now = seen

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.is_own(access_point):
            return
        # Non-destructive tagging: sibling marker + ledger entry.
        try:
            with open(filename + ".own", "w") as fp:
                fp.write("authorized-practice\n")
        except Exception as e:
            logging.debug("[own_network_allowlist] could not write marker: %s", e)
        self._append_ledger(filename, access_point)
        logging.info(
            "[own_network_allowlist] authorized-practice capture: %s (%s)",
            os.path.basename(filename), access_point.get("hostname") or access_point.get("mac"),
        )

    def _append_ledger(self, filename, ap):
        record = {
            "file": filename,
            "mac": ap.get("mac"),
            "ssid": ap.get("hostname"),
        }
        try:
            data = []
            if self._ledger_path and os.path.exists(self._ledger_path):
                with open(self._ledger_path) as fp:
                    data = json.load(fp)
                    if not isinstance(data, list):
                        data = []
            data.append(record)
            if self._ledger_path:
                os.makedirs(os.path.dirname(self._ledger_path), exist_ok=True)
                with open(self._ledger_path, "w") as fp:
                    json.dump(data, fp, indent=2)
        except Exception as e:
            logging.debug("[own_network_allowlist] ledger write failed: %s", e)

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element(
            "own_nets",
            LabeledValue(color=BLACK, label="own:", value="0", position=pos,
                         label_font=fonts.Small, text_font=fonts.Small),
        )

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("own_nets", str(len(self._seen_now)))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("own_nets"):
                ui.remove_element("own_nets")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = ""
        try:
            if self._ledger_path and os.path.exists(self._ledger_path):
                with open(self._ledger_path) as fp:
                    for rec in json.load(fp):
                        rows += "<tr><td>{}</td><td>{}</td></tr>".format(
                            rec.get("ssid") or "?", rec.get("mac") or "?")
        except Exception:
            pass
        return (
            "<html><body><h1>Own-Network Allowlist</h1>"
            "<p>{} MAC(s), {} SSID(s) configured; {} own network(s) in range now.</p>"
            "<h2>Authorized-practice captures</h2><table border=1>"
            "<tr><th>SSID</th><th>BSSID</th></tr>{}</table></body></html>"
        ).format(len(self._own_macs), len(self._own_ssids), len(self._seen_now), rows)
