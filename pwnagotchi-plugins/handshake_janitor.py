"""handshake_janitor — de-duplicate capture files, keep the best per BSSID.

The ecosystem is great at *capturing* handshakes and does nothing to manage them afterward.
This plugin groups capture files by BSSID, scores each file by how complete its handshake is
(number of EAPOL frames — more of the 4-way is better), keeps the best one per BSSID, and
either archives or deletes the rest to reclaim SD space.

Safe by default: the action is "archive" (move duplicates into a `duplicates/` subfolder),
not delete, and it can run in dry-run mode first.

Options (main.plugins.handshake_janitor.*):
    enabled       = true
    handshakes    = "/root/handshakes"
    action        = "archive"     # "archive" (move) or "delete"
    archive_dir   =               # defaults to <handshakes>/duplicates
    dry_run       = false
    interval_hours = 6            # minimum hours between automatic sweeps
    position      = "0,0"
"""
import glob
import logging
import os
import shutil
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_HEX = set("0123456789abcdef")


def normalize_hex(value):
    return "".join(c for c in str(value or "").lower() if c in _HEX)


def bssid_from_filename(name):
    """Extract a 12-hex BSSID from a pwnagotchi/bettercap capture filename, or None."""
    base = os.path.basename(name)
    for suffix in (".pcapng", ".pcap"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    # Try each underscore-separated token from the right; BSSID is usually the last one,
    # but tolerate a trailing counter (essid_aabbccddeeff_2).
    for token in reversed(base.split("_")):
        h = normalize_hex(token)
        if len(h) == 12:
            return h
    return None


def group_by_bssid(files):
    groups = {}
    for f in files:
        b = bssid_from_filename(f)
        if b:
            groups.setdefault(b, []).append(f)
    return groups


def plan(scored):
    """Given [{path,score,size,mtime}, ...], return (keep, [drops])."""
    keep = max(scored, key=lambda x: (x["score"], x["size"], x["mtime"]))
    drops = [x for x in scored if x is not keep]
    return keep, drops


def count_eapol(path):
    """Heuristic completeness score: count EAPOL (ethertype 0x888e) occurrences."""
    try:
        with open(path, "rb") as fp:
            return fp.read().count(b"\x88\x8e")
    except Exception:
        return 0


class HandshakeJanitor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "De-duplicate capture files, keeping the most complete handshake per BSSID."

    def __init__(self):
        self.options = dict()
        self._analyzer = count_eapol
        self._last_run = 0
        self._reclaimed_files = 0
        self._reclaimed_bytes = 0
        self._log = []

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._action = self.options.get("action", "archive")
        self._archive_dir = self.options.get("archive_dir") or os.path.join(
            self._handshakes, "duplicates")
        self._dry_run = bool(self.options.get("dry_run", False))
        self._interval = float(self.options.get("interval_hours", 6)) * 3600.0
        logging.info("[handshake_janitor] loaded (action=%s dry_run=%s)",
                     self._action, self._dry_run)

    # -- core --------------------------------------------------------------------------
    def run(self, dry_run=None):
        dry = self._dry_run if dry_run is None else dry_run
        results = []
        try:
            files = glob.glob(os.path.join(self._handshakes, "*.pcap")) + \
                glob.glob(os.path.join(self._handshakes, "*.pcapng"))
        except Exception as e:
            logging.warning("[handshake_janitor] cannot list %s: %s", self._handshakes, e)
            return results

        for bssid, paths in group_by_bssid(files).items():
            if len(paths) < 2:
                continue
            scored = []
            for p in paths:
                try:
                    scored.append({"path": p, "score": self._analyzer(p),
                                   "size": os.path.getsize(p), "mtime": os.path.getmtime(p)})
                except Exception:
                    continue
            if len(scored) < 2:
                continue
            keep, drops = plan(scored)
            dropped_names = []
            for d in drops:
                dropped_names.append(os.path.basename(d["path"]))
                if not dry:
                    self._dispose(d["path"])
                self._reclaimed_files += 1
                self._reclaimed_bytes += d["size"]
            entry = {"bssid": bssid, "kept": os.path.basename(keep["path"]),
                     "kept_score": keep["score"], "dropped": dropped_names,
                     "action": "dry_run" if dry else self._action}
            self._log.append(entry)
            results.append(entry)
            logging.info("[handshake_janitor] %s: kept %s (score %d), %s %d dup(s)",
                         bssid, entry["kept"], keep["score"], entry["action"], len(dropped_names))
        return results

    def _dispose(self, path):
        try:
            if self._action == "delete":
                os.remove(path)
            else:
                os.makedirs(self._archive_dir, exist_ok=True)
                dest = os.path.join(self._archive_dir, os.path.basename(path))
                n = 1
                while os.path.exists(dest):
                    dest = os.path.join(self._archive_dir,
                                        "%s.%d" % (os.path.basename(path), n))
                    n += 1
                shutil.move(path, dest)
        except Exception as e:
            logging.warning("[handshake_janitor] dispose failed for %s: %s", path, e)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        now = time.time()
        if (now - self._last_run) >= self._interval:
            self._last_run = now
            self.run()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("janitor", LabeledValue(color=BLACK, label="dedup:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("janitor", str(self._reclaimed_files))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("janitor"):
                ui.remove_element("janitor")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                e["bssid"], e["kept"], len(e["dropped"]), e["action"])
            for e in reversed(self._log)
        ) or "<tr><td colspan=4>nothing yet</td></tr>"
        return (
            "<html><body><h1>Handshake Janitor</h1>"
            "<p>Reclaimed {} file(s), {} bytes.</p>"
            "<table border=1><tr><th>bssid</th><th>kept</th><th>dropped</th><th>action</th></tr>"
            "{}</table></body></html>"
        ).format(self._reclaimed_files, self._reclaimed_bytes, rows)
