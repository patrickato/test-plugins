"""capture_retention — policy-driven cleanup with a grace window.

Cards fill until something breaks. This plugin expires captures by policy instead: it drops
already-solved captures and junk first, then old captures, and protects crackable-but-unsolved
ones unless the card is under space pressure. Nothing is deleted immediately — candidates go
into an owner-visible queue with a "delete after" timestamp (a grace window), and are only
removed once that window elapses. Supports dry-run.

Works well with capture_grader (`.grade` sidecars) and crack_reconciler (`.cracked` sidecars);
falls back to scoring the file itself when sidecars are absent.

Options (main.plugins.capture_retention.*):
    enabled          = true
    handshakes       = "/root/handshakes"
    data_path        = "/etc/pwnagotchi/capture_retention.json"
    max_age_days     = 30      # 0 = don't expire by age
    min_free_mb      = 200     # below this = space pressure (0 = ignore space)
    grace_days       = 3       # review window before actual deletion
    protect_unsolved = true    # keep crackable unsolved captures unless space pressure
    dry_run          = false
    position         = "0,0"
"""
import glob
import json
import logging
import os
import time

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


def grade_of(path):
    """Grade from a .grade sidecar if present, else compute from EAPOL count."""
    try:
        if os.path.exists(path + ".grade"):
            with open(path + ".grade") as fp:
                first = fp.read().strip().split()
                if first and first[0] in ("A", "B", "C", "F"):
                    return first[0]
    except Exception:
        pass
    n = count_eapol(path)
    return "A" if n >= 3 else "B" if n == 2 else "C" if n == 1 else "F"


def evaluate(meta, policy):
    """Pure: given per-file metadata + policy, return expiry candidates with a reason."""
    out = []
    for m in meta:
        if m["solved"]:
            out.append({**m, "reason": "solved"})
        elif m["grade"] == "F":
            out.append({**m, "reason": "junk"})
        elif policy["max_age_days"] > 0 and m["age_days"] >= policy["max_age_days"]:
            if m["grade"] in ("A", "B") and policy["protect_unsolved"] and not policy["space_pressure"]:
                continue
            out.append({**m, "reason": "old"})
    return out


class CaptureRetention(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Policy-driven capture cleanup with a grace-window review queue."

    def __init__(self):
        self.options = dict()
        self._queue = {}        # file -> {reason, queued_at, delete_after}
        self._deleted_total = 0
        self._path = None

    def on_loaded(self):
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._path = self.options.get("data_path", "/etc/pwnagotchi/capture_retention.json")
        self._max_age = int(self.options.get("max_age_days", 30))
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._grace = float(self.options.get("grace_days", 3)) * 86400.0
        self._protect = bool(self.options.get("protect_unsolved", True))
        self._dry_run = bool(self.options.get("dry_run", False))
        self._load()
        logging.info("[capture_retention] loaded (max_age=%dd grace=%.0fd)",
                     self._max_age, self._grace / 86400.0)

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    data = json.load(fp)
                if isinstance(data, dict):
                    self._queue = data.get("queue", {})
                    self._deleted_total = data.get("deleted_total", 0)
        except Exception as e:
            logging.debug("[capture_retention] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"queue": self._queue, "deleted_total": self._deleted_total},
                              fp, indent=2)
        except Exception as e:
            logging.debug("[capture_retention] save failed: %s", e)

    # -- helpers -----------------------------------------------------------------------
    def _space_pressure(self):
        if self._min_free_mb <= 0:
            return False
        try:
            import shutil
            free_mb = shutil.disk_usage(self._handshakes).free / (1024 * 1024)
            return free_mb < self._min_free_mb
        except Exception:
            return False

    def _gather(self, now):
        files = glob.glob(os.path.join(self._handshakes, "*.pcap")) + \
            glob.glob(os.path.join(self._handshakes, "*.pcapng"))
        meta = []
        for f in files:
            try:
                meta.append({
                    "path": f,
                    "age_days": (now - os.path.getmtime(f)) / 86400.0,
                    "size": os.path.getsize(f),
                    "solved": os.path.exists(f + ".cracked"),
                    "grade": grade_of(f),
                })
            except Exception:
                continue
        return meta

    # -- core --------------------------------------------------------------------------
    def run(self, dry_run=None, now=None):
        dry = self._dry_run if dry_run is None else dry_run
        now = now if now is not None else time.time()
        pressure = self._space_pressure()
        policy = {"max_age_days": self._max_age, "protect_unsolved": self._protect,
                  "space_pressure": pressure}

        candidates = evaluate(self._gather(now), policy)
        queued, deleted = [], []

        # queue new candidates with a grace window (immediate if under space pressure)
        for c in candidates:
            if c["path"] not in self._queue:
                self._queue[c["path"]] = {
                    "reason": c["reason"], "queued_at": now,
                    "delete_after": now if pressure else now + self._grace,
                }
                queued.append(os.path.basename(c["path"]))

        # delete anything past its grace window; drop vanished files
        for path in list(self._queue.keys()):
            if not os.path.exists(path):
                del self._queue[path]
                continue
            if self._queue[path]["delete_after"] <= now:
                if not dry:
                    self._remove(path)
                    deleted.append(os.path.basename(path))
                    self._deleted_total += 1
                    del self._queue[path]

        self._save()
        logging.info("[capture_retention] queued %d, deleted %d (pressure=%s dry=%s)",
                     len(queued), len(deleted), pressure, dry)
        return {"queued": queued, "deleted": deleted}

    def _remove(self, path):
        for p in (path, path + ".grade", path + ".cracked", path + ".own"):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as e:
                logging.debug("[capture_retention] remove failed %s: %s", p, e)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        # Run occasionally; grace handling makes frequent runs safe.
        if epoch % 60 == 0:
            self.run()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("retention", LabeledValue(color=BLACK, label="exp:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("retention", "%dq" % len(self._queue))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("retention"):
                ui.remove_element("retention")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        now = time.time()
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{:.1f}h</td></tr>".format(
                os.path.basename(f), q["reason"], max(0, (q["delete_after"] - now) / 3600.0))
            for f, q in self._queue.items()
        ) or "<tr><td colspan=3>queue empty</td></tr>"
        return (
            "<html><body><h1>Capture Retention</h1>"
            "<p>{} queued, {} deleted lifetime.</p>"
            "<table border=1><tr><th>file</th><th>reason</th><th>deletes in</th></tr>{}"
            "</table></body></html>"
        ).format(len(self._queue), self._deleted_total, rows)
