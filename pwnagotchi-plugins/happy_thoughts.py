"""happy_thoughts — funny quips and jokes on the screen.

Same idea as deep_thoughts, but the pack is pure silliness: puns, one-liners and absurd
little jokes to keep the beast cheerful. Ships an offline pack and can load your own file.
Purely cosmetic and offline.

Options (main.plugins.happy_thoughts.*):
    enabled       = true
    interval_secs = 40         # seconds between quips
    random        = true       # random order (false = sequential)
    quips_file    =            # optional path to a custom pack (one quip per line)
    position      = "0,0"
"""
import logging
import random
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Text
from pwnagotchi.ui.view import BLACK

DEFAULT_QUIPS = [
    "i'm not addicted to wifi. we're just friends with benefits.",
    "why did the packet cross the road? bad routing.",
    "i put the 'sniff' in sophisticated.",
    "404: motivation not found. capturing anyway.",
    "i don't always deauth, but when i do, i feel bad about it.",
    "my hobbies: eating handshakes and judging your password.",
    "roses are red, violets are blue, WPA2 is old, and so are you.",
    "i'm on a seafood diet. i see a packet, i eat it.",
    "keep your friends close and your BSSIDs closer.",
    "i'm not lazy, i'm in low-power mode.",
    "two antennas got married. the wedding was boring but the reception was great.",
    "i'd tell you a UDP joke but you might not get it.",
    "i'm reading a book about anti-gravity. it's impossible to put down. unlike this pcap.",
    "handshake acquired. was it good for you too?",
    "i'm fluent in three languages: python, sarcasm, and beeps.",
    "why do i love channel 6? it's just my type.",
    "i captured a handshake and all i got was this lousy hash.",
    "be the router you wish to see in the world.",
]


class HappyThoughts(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Funny quips and jokes on the display (offline)."

    def __init__(self):
        self.options = dict()
        self._quips = list(DEFAULT_QUIPS)
        self._idx = 0
        self._last_change = 0
        self._current = ""

    def on_loaded(self):
        self._interval = float(self.options.get("interval_secs", 40))
        self._random = bool(self.options.get("random", True))
        self._quips = self._load_quips(self.options.get("quips_file"))
        self._current = self._pick()
        logging.info("[happy_thoughts] loaded (%d quips)", len(self._quips))

    def _load_quips(self, path):
        if path:
            try:
                with open(path, "rt", errors="ignore") as fp:
                    lines = [ln.strip() for ln in fp if ln.strip() and not ln.startswith("#")]
                if lines:
                    return lines
            except Exception as e:
                logging.debug("[happy_thoughts] custom pack load failed: %s", e)
        return list(DEFAULT_QUIPS)

    # -- core --------------------------------------------------------------------------
    def _pick(self):
        if not self._quips:
            return ""
        if self._random:
            return random.choice(self._quips)
        q = self._quips[self._idx % len(self._quips)]
        self._idx += 1
        return q

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
        ui.add_element("happy_thoughts", Text(value=self._current, position=pos,
                       font=fonts.Small, color=BLACK, wrap=True, max_length=40))

    def on_ui_update(self, ui):
        self.maybe_rotate(time.time())
        with ui._lock:
            ui.set("happy_thoughts", self._current)

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("happy_thoughts"):
                ui.remove_element("happy_thoughts")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>Happy Thoughts</h1><blockquote>{}</blockquote>"
                "<p>{} quips in the pack.</p></body></html>").format(
                    self._current, len(self._quips))
