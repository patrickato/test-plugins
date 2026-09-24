"""eink_ghosting — schedule full refreshes to fight e-ink ghosting.

E-ink panels accumulate ghosting from repeated partial updates. This counts partial refreshes
and, after a budget of updates or a time interval (whichever comes first), triggers a full
refresh to clear the panel. The scheduling policy is the tested core; the actual full-refresh
call is a guarded best-effort against the display/view.

Options (main.plugins.eink_ghosting.*):
    enabled        = true
    max_partials   = 60        # full refresh after this many partial updates
    max_interval_s = 600       # ...or after this many seconds, whichever first
    show_counter   = true      # show partial-updates-since-last-full on the display
    position       = "0,0"
"""
import logging
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def should_full_refresh(partial_count, elapsed_s, max_partials, max_interval_s):
    if max_partials > 0 and partial_count >= max_partials:
        return True
    if max_interval_s > 0 and elapsed_s >= max_interval_s:
        return True
    return False


class EinkGhosting(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Periodic e-ink full refresh to prevent ghosting/burn-in."

    def __init__(self):
        self.options = dict()
        self._partials = 0
        self._fulls = 0
        self._last_full = time.time()
        self._ui = None
        self._refresh_fn = self._hardware_full_refresh

    def on_loaded(self):
        self._max_partials = int(self.options.get("max_partials", 60))
        self._max_interval = float(self.options.get("max_interval_s", 600))
        self._show_counter = bool(self.options.get("show_counter", True))
        self._last_full = time.time()
        logging.info("[eink_ghosting] loaded (every %d partials or %.0fs)",
                     self._max_partials, self._max_interval)

    # -- core (testable) ---------------------------------------------------------------
    def note_partial(self):
        self._partials += 1

    def maybe_refresh(self, now=None):
        now = now if now is not None else time.time()
        if should_full_refresh(self._partials, now - self._last_full,
                               self._max_partials, self._max_interval):
            self._trigger_full()
            self._partials = 0
            self._last_full = now
            self._fulls += 1
            return True
        return False

    def _trigger_full(self):
        try:
            self._refresh_fn()
        except Exception as e:
            logging.debug("[eink_ghosting] full refresh failed: %s", e)

    def _hardware_full_refresh(self):
        # Best-effort: ask the view to redraw fully. Forks differ on the exact API, so try
        # a forced update and fall back to a plain update.
        if self._ui is None:
            return
        try:
            self._ui.update(force=True)
        except TypeError:
            self._ui.update()

    # -- events ------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        self._ui = ui
        if not self._show_counter:
            return
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("eink", LabeledValue(color=BLACK, label="eink:", value="0",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        self._ui = ui
        self.note_partial()
        if self._show_counter:
            with ui._lock:
                if ui.has_element("eink"):
                    ui.set("eink", str(self._partials))

    def on_epoch(self, agent, epoch, epoch_data):
        self.maybe_refresh()

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("eink"):
                ui.remove_element("eink")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>E-ink Ghosting</h1>"
                "<ul><li>partials since last full: {}</li><li>full refreshes: {}</li>"
                "<li>budget: {} partials / {:.0f}s</li></ul></body></html>").format(
                    self._partials, self._fulls, self._max_partials, self._max_interval)
