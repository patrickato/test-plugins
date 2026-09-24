"""pet_quips — the pet talks back.

Gives the beast a little voice: a random quip when it captures a handshake, and mood-fitting
lines when it gets lonely, bored or excited. Quips show on the display for a few seconds.
Purely cosmetic and offline; each category has a default pack you can override in config.

Options (main.plugins.pet_quips.*):
    enabled     = true
    show_secs   = 6            # how long a quip stays up
    quips.handshake = ["...", ...]   # optional overrides per category
    quips.lonely    = [...]
    quips.bored     = [...]
    quips.excited   = [...]
    position    = "0,0"
"""
import logging
import random
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Text
from pwnagotchi.ui.view import BLACK

DEFAULT_QUIPS = {
    "handshake": [
        "gotcha!", "nom nom, tasty hash.", "another one for the pile.",
        "handshake secured, feeling smug.", "did you see that? i did that.",
    ],
    "lonely": [
        "anybody out there?", "so quiet i can hear the RF.",
        "i miss my pwnagotchi friends.", "just me and the noise floor.",
    ],
    "bored": [
        "same three networks. thrilling.", "is this all there is?",
        "i've counted the beacons twice.", "wake me when something new appears.",
    ],
    "excited": [
        "so many networks! i love it here.", "the air is THICK with packets!",
        "best. location. ever.", "my antenna is tingling!",
    ],
}


class PetQuips(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "The pet reacts with quips on handshakes and mood changes."

    def __init__(self):
        self.options = dict()
        self._quips = {k: list(v) for k, v in DEFAULT_QUIPS.items()}
        self._current = ""
        self._until = 0

    def on_loaded(self):
        self._show_secs = float(self.options.get("show_secs", 6))
        overrides = self.options.get("quips", {}) or {}
        for cat in self._quips:
            if overrides.get(cat):
                self._quips[cat] = list(overrides[cat])
        logging.info("[pet_quips] loaded")

    # -- core --------------------------------------------------------------------------
    def quip_for(self, category):
        pack = self._quips.get(category)
        return random.choice(pack) if pack else ""

    def say(self, category, now=None):
        now = now if now is not None else time.time()
        text = self.quip_for(category)
        if text:
            self._current = text
            self._until = now + self._show_secs
        return text

    def showing(self, now=None):
        now = now if now is not None else time.time()
        return now < self._until

    # -- events ------------------------------------------------------------------------
    def on_handshake(self, agent, filename, access_point, client_station):
        self.say("handshake")

    def on_lonely(self, agent):
        self.say("lonely")

    def on_bored(self, agent):
        self.say("bored")

    def on_excited(self, agent):
        self.say("excited")

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("pet_quips", Text(value="", position=pos, font=fonts.Small,
                       color=BLACK, wrap=True, max_length=40))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("pet_quips", self._current if self.showing() else "")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("pet_quips"):
                ui.remove_element("pet_quips")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        counts = ", ".join("%s:%d" % (k, len(v)) for k, v in self._quips.items())
        return ("<html><body><h1>Pet Quips</h1><p>last: {}</p>"
                "<p>packs: {}</p></body></html>").format(self._current or "-", counts)
