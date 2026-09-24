"""display_setup_helper — figure out why the screen isn't working.

Getting an SPI TFT or e-ink panel working is the #1 newbie wall. This read-only advisor
inspects the boot config (dtoverlay / SPI), the framebuffer devices under /sys, and reports
what it found plus concrete suggestions (which overlay to add, enable SPI, check wiring). It
never edits config on its own — it tells you what to change.

Options (main.plugins.display_setup_helper.*):
    enabled     = true
    config_path =              # boot config; auto-detected (/boot/firmware/config.txt or /boot/config.txt)
    position    = "0,0"

Requires: none (reads /boot config + /sys/class/graphics). Read-only.
"""
import glob
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

# (substring in overlay, friendly panel name) — first match wins
KNOWN_PANELS = [
    ("tft35a", '3.5" ILI9486 SPI (tft35a)'),
    ("mhs35", '3.5" MHS35 SPI'),
    ("waveshare35", 'Waveshare 3.5" SPI'),
    ("pitft35", 'Adafruit PiTFT 3.5"'),
    ("ili9486", "ILI9486 SPI"),
    ("ili9341", "ILI9341 SPI"),
    ("epaper", "e-Paper / e-ink"),
    ("epd", "e-Paper / e-ink"),
    ("waveshare", "Waveshare SPI"),
    ("fbtft", "generic fbtft SPI"),
]


def parse_config_overlays(text):
    overlays = []
    spi = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("dtoverlay="):
            overlays.append(line.split("=", 1)[1].strip())
        elif line.replace(" ", "").startswith("dtparam=spi=on"):
            spi = True
    return overlays, spi


def detect_panel(overlays):
    joined = " ".join(overlays).lower()
    for key, name in KNOWN_PANELS:
        if key in joined:
            return name
    return None


def parse_fb_devices(graphics_dir):
    devs = []
    for path in sorted(glob.glob(os.path.join(graphics_dir, "fb*"))):
        name = os.path.basename(path)
        size = None
        try:
            with open(os.path.join(path, "virtual_size")) as fp:
                size = fp.read().strip()
        except Exception:
            pass
        devs.append({"name": name, "size": size})
    return devs


def suggest(evidence):
    """evidence: {overlays, spi, fbs} -> {panel, findings, config_lines}."""
    overlays = evidence.get("overlays", [])
    spi = evidence.get("spi", False)
    fbs = evidence.get("fbs", [])
    panel = detect_panel(overlays)
    tft_fbs = [d for d in fbs if d["name"] != "fb0"]   # fb0 is usually HDMI/primary

    findings = []
    config_lines = []
    if tft_fbs:
        findings.append("Framebuffer device(s) present: " +
                        ", ".join("%s (%s)" % (d["name"], d["size"] or "?") for d in tft_fbs))
        if panel:
            findings.append("Panel looks like: %s" % panel)
        else:
            findings.append("A secondary framebuffer exists but the panel type is unrecognized.")
    else:
        if panel:
            findings.append("Overlay for %s is configured, but no TFT framebuffer appeared." % panel)
            findings.append("Check SPI is enabled and the wiring/module; a reboot may be needed.")
        else:
            findings.append("No TFT framebuffer detected and no known display overlay configured.")
            findings.append("If you have an SPI TFT, enable SPI and add the correct overlay:")
            config_lines.append("dtparam=spi=on")
            config_lines.append("dtoverlay=tft35a:rotate=90   # example for a 3.5\" ILI9486")
    if not spi and not tft_fbs:
        if "dtparam=spi=on" not in config_lines:
            config_lines.insert(0, "dtparam=spi=on")
    return {"panel": panel, "findings": findings, "config_lines": config_lines}


class DisplaySetupHelper(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Detect the display panel and suggest the right overlay/config (read-only)."

    def __init__(self):
        self.options = dict()
        self._report = None

    def on_loaded(self):
        self._config_path = self.options.get("config_path") or self._detect_config_path()
        self._graphics = "/sys/class/graphics"
        logging.info("[display_setup_helper] loaded (config=%s)", self._config_path)

    @staticmethod
    def _detect_config_path():
        for p in ("/boot/firmware/config.txt", "/boot/config.txt"):
            if os.path.exists(p):
                return p
        return "/boot/config.txt"

    # -- core --------------------------------------------------------------------------
    def analyze(self):
        text = ""
        try:
            with open(self._config_path, "rt", errors="ignore") as fp:
                text = fp.read()
        except Exception:
            pass
        overlays, spi = parse_config_overlays(text)
        fbs = parse_fb_devices(self._graphics)
        self._report = suggest({"overlays": overlays, "spi": spi, "fbs": fbs})
        return self._report

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.analyze()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("disp", LabeledValue(color=BLACK, label="disp:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            r = self._report or {}
            ui.set("disp", (r.get("panel") or "?")[:16])

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("disp"):
                ui.remove_element("disp")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        r = self.analyze()
        findings = "".join("<li>%s</li>" % f for f in r["findings"])
        cfg = ("<pre>%s</pre>" % "\n".join(r["config_lines"])) if r["config_lines"] else ""
        return ("<html><body><h1>Display Setup Helper</h1>"
                "<ul>{}</ul>{}<p>config file: {}</p></body></html>").format(
                    findings, cfg, self._config_path)
