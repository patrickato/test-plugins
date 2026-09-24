"""sd_wear — estimate SD-card write wear and remaining life.

SD death kills more Pis than anything, and nothing measures it. This plugin reads sectors
written from ``/proc/diskstats`` for the root device, accumulates total bytes written
(surviving reboots, where the kernel counter resets), and estimates wear against a
configurable endurance rating (TBW) plus a projected days-to-end-of-life from the current
write rate. Shows written GB on the display and warns past a threshold.

To avoid adding wear itself, it persists its own state only occasionally.

Options (main.plugins.sd_wear.*):
    enabled       = true
    device        =            # e.g. "mmcblk0"; auto-detected from / mount if empty
    rated_tbw     = 30         # endurance rating in terabytes-written
    warn_pct      = 80         # warn when wear reaches this % of rating
    data_path     = "/etc/pwnagotchi/sd_wear.json"
    persist_secs  = 600        # minimum seconds between state saves
    position      = "0,0"
"""
import json
import logging
import os
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

SECTOR = 512


def strip_partition(dev):
    """/dev/mmcblk0p2 -> mmcblk0, nvme0n1p2 -> nvme0n1, sda2 -> sda."""
    name = os.path.basename(dev)
    if "mmcblk" in name or "nvme" in name:
        i = name.rfind("p")
        if i > 0 and name[i + 1:].isdigit():
            return name[:i]
        return name
    return name.rstrip("0123456789")


def root_device_from_mounts(text):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "/":
            return strip_partition(parts[0])
    return None


def parse_diskstats(text, device):
    """Return sectors_written for `device`, or None if not found."""
    for line in text.splitlines():
        f = line.split()
        if len(f) >= 10 and f[2] == device:
            try:
                return int(f[9])
            except ValueError:
                return None
    return None


def estimate(cumulative_bytes, elapsed_s, rated_bytes):
    written_gb = cumulative_bytes / 1e9
    pct = (100.0 * cumulative_bytes / rated_bytes) if rated_bytes > 0 else 0.0
    rate_per_day = (cumulative_bytes / elapsed_s * 86400.0) if elapsed_s > 0 else 0.0
    remaining = max(0.0, rated_bytes - cumulative_bytes)
    projected_days = (remaining / rate_per_day) if rate_per_day > 0 else None
    return {"written_gb": written_gb, "pct": pct,
            "rate_gb_per_day": rate_per_day / 1e9, "projected_days": projected_days}


class SDWear(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Estimate SD-card write wear and projected remaining life."

    def __init__(self):
        self.options = dict()
        self._device = None
        self._last_sectors = None
        self._cumulative = 0
        self._first_time = None
        self._last_save = 0
        self._path = None

    def on_loaded(self):
        self._path = self.options.get("data_path", "/etc/pwnagotchi/sd_wear.json")
        self._rated_bytes = float(self.options.get("rated_tbw", 30)) * 1e12
        self._warn_pct = float(self.options.get("warn_pct", 80))
        self._persist_secs = float(self.options.get("persist_secs", 600))
        self._device = self.options.get("device") or self._detect_device()
        self._load()
        logging.info("[sd_wear] loaded (device=%s)", self._device)

    def _detect_device(self):
        try:
            with open("/proc/mounts") as fp:
                return root_device_from_mounts(fp.read())
        except Exception:
            return None

    # -- persistence -------------------------------------------------------------------
    def _load(self):
        try:
            if self._path and os.path.exists(self._path):
                with open(self._path) as fp:
                    d = json.load(fp)
                self._cumulative = d.get("cumulative_bytes", 0)
                self._first_time = d.get("first_time")
        except Exception as e:
            logging.debug("[sd_wear] load failed: %s", e)

    def _save(self):
        try:
            if self._path:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "w") as fp:
                    json.dump({"cumulative_bytes": self._cumulative,
                               "first_time": self._first_time}, fp)
                self._last_save = time.time()
        except Exception as e:
            logging.debug("[sd_wear] save failed: %s", e)

    # -- core --------------------------------------------------------------------------
    def update(self, current_sectors, now):
        """Accumulate written bytes, handling the kernel counter resetting on reboot."""
        if self._first_time is None:
            self._first_time = now
        if self._last_sectors is None:
            self._last_sectors = current_sectors
            return self._cumulative
        if current_sectors >= self._last_sectors:
            delta = current_sectors - self._last_sectors
        else:
            delta = current_sectors      # counter reset (reboot): count from zero
        self._cumulative += delta * SECTOR
        self._last_sectors = current_sectors
        return self._cumulative

    def _sample(self, now=None):
        now = now if now is not None else time.time()
        if not self._device:
            return
        try:
            with open("/proc/diskstats") as fp:
                sectors = parse_diskstats(fp.read(), self._device)
        except Exception as e:
            logging.debug("[sd_wear] diskstats read failed: %s", e)
            return
        if sectors is None:
            return
        self.update(sectors, now)
        if (now - self._last_save) >= self._persist_secs:
            self._save()
            est = self.report(now)
            if est["pct"] >= self._warn_pct:
                logging.warning("[sd_wear] wear at %.1f%% of rating", est["pct"])

    def report(self, now=None):
        now = now if now is not None else time.time()
        elapsed = (now - self._first_time) if self._first_time else 0
        return estimate(self._cumulative, elapsed, self._rated_bytes)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        self._sample()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("sd_wear", LabeledValue(color=BLACK, label="sd:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("sd_wear", "%.0fG" % self.report()["written_gb"])

    def on_unload(self, ui):
        self._save()
        with ui._lock:
            if ui.has_element("sd_wear"):
                ui.remove_element("sd_wear")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        est = self.report()
        proj = "unknown" if est["projected_days"] is None else "%.0f days" % est["projected_days"]
        return (
            "<html><body><h1>SD Wear</h1>"
            "<ul><li>device: {}</li><li>written: {:.1f} GB ({:.2f}% of rating)</li>"
            "<li>rate: {:.2f} GB/day</li><li>projected life left: {}</li></ul></body></html>"
        ).format(self._device, est["written_gb"], est["pct"], est["rate_gb_per_day"], proj)
