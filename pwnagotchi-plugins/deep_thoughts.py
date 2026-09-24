"""deep_thoughts — rotating shower-thoughts on the screen.

Displays a slowly-rotating stream of little musings — the "shower thoughts" vibe. Ships an
offline pack of thoughts and can load your own from a file (one per line). Rotates on a timer,
sequentially or at random. Purely cosmetic and offline.

Options (main.plugins.deep_thoughts.*):
    enabled       = true
    interval_secs = 45         # seconds between thoughts
    random        = true       # random order (false = sequential)
    thoughts_file =            # optional path to a custom pack (one thought per line)
    position      = "0,0"
"""
import logging
import os
import random
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Text
from pwnagotchi.ui.view import BLACK

DEFAULT_THOUGHTS = [
    "if you capture a handshake in an empty room, does it make a sound?",
    "every network is temporary, but the pcap is forever.",
    "the beast does not chase packets. the packets come to the beast.",
    "wifi is just radio with commitment issues.",
    "somewhere, a router is broadcasting its heart out to no one.",
    "a channel is only crowded if you are listening.",
    "the best handshake is the one you didn't have to ask for.",
    "you cannot deauth your way to inner peace.",
    "all SSIDs are cries for attention. some are just quieter.",
    "the fastest way to fill an SD card is to forget you have one.",
    "monitor mode: watching, always watching, judging silently.",
    "an idle pwnagotchi still dreams in 802.11.",
    "the signal fades, but the memory of -42 dBm lingers.",
    "hidden networks aren't hidden. they're shy.",
    "entropy always wins, but we capture the packets anyway.",
]


class DeepThoughts(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Rotating shower-thoughts on the display (offline)."

    def __init__(self):
        self.options = dict()
        self._thoughts = list(DEFAULT_THOUGHTS)
        self._idx = 0
        self._last_change = 0
        self._current = ""

    def on_loaded(self):
        self._interval = float(self.options.get("interval_secs", 45))
        self._random = bool(self.options.get("random", True))
        self._thoughts = self._load_thoughts(self.options.get("thoughts_file"))
        self._current = self._pick()
        logging.info("[deep_thoughts] loaded (%d thoughts)", len(self._thoughts))

    def _load_thoughts(self, path):
        if path:
            try:
                with open(path, "rt", errors="ignore") as fp:
                    lines = [ln.strip() for ln in fp if ln.strip() and not ln.startswith("#")]
                if lines:
                    return lines
            except Exception as e:
                logging.debug("[deep_thoughts] custom pack load failed: %s", e)
        return list(DEFAULT_THOUGHTS)

    # -- core --------------------------------------------------------------------------
    def _pick(self):
        if not self._thoughts:
            return ""
        if self._random:
            return random.choice(self._thoughts)
        t = self._thoughts[self._idx % len(self._thoughts)]
        self._idx += 1
        return t

    def maybe_rotate(self, now):
        if (now - self._last_change) >= self._interval:
            self._last_change = now
            self._current = self._pick()
            return True
        return False

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("deep_thoughts", Text(value=self._current, position=pos,
                       font=fonts.Small, color=BLACK, wrap=True, max_length=40))

    def on_ui_update(self, ui):
        self.maybe_rotate(time.time())
        with ui._lock:
            ui.set("deep_thoughts", self._current)

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("deep_thoughts"):
                ui.remove_element("deep_thoughts")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>Deep Thoughts</h1><blockquote>{}</blockquote>"
                "<p>{} thoughts in the pack.</p></body></html>").format(
                    self._current, len(self._thoughts))
