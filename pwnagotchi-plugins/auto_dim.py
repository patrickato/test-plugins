"""auto_dim — dim the display by ambient light (or a time schedule).

Brightness is static; nothing reacts to the room. This maps measured lux to a backlight
level, or falls back to a simple day/night time schedule when no light sensor is present.
Saves power and eyes. Backlight is driven via sysfs (`/sys/class/backlight`) or a GPIO PWM
pin; both are guarded so the plugin still computes a target level off-Pi.

Options (main.plugins.auto_dim.*):
    enabled         = true
    source          = "time"       # "time" or "lux"
    method          = "sysfs"      # "sysfs" or "gpio"
    backlight_path  =              # sysfs backlight dir; auto-detected if empty
    gpio_pin        = 18           # for method="gpio"
    min_brightness  = 10           # % (darkest)
    max_brightness  = 100          # % (brightest)
    lux_low         = 5            # lux at/below -> min_brightness
    lux_high        = 300          # lux at/above -> max_brightness
    day_start       = 8            # time-schedule day window (local hours)
    night_start     = 22
    day_brightness  = 100
    night_brightness = 20
    position        = "0,0"

Requires: a controllable backlight (sysfs backlight device or a PWM GPIO pin). For
source="lux": a light sensor + its library (optional). Falls back to the time schedule.
"""
import logging
import os
import time

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_BL_BASE = "/sys/class/backlight"


def brightness_for_lux(lux, lux_low, lux_high, min_b, max_b):
    if lux <= lux_low:
        return float(min_b)
    if lux >= lux_high:
        return float(max_b)
    frac = (lux - lux_low) / (lux_high - lux_low)
    return float(min_b + frac * (max_b - min_b))


def brightness_for_time(hour, day_start, night_start, day_b, night_b):
    return float(day_b if day_start <= hour < night_start else night_b)


class AutoDim(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Dim the display by ambient light or a day/night schedule."

    def __init__(self):
        self.options = dict()
        self._last_applied = None
        self._backend = None

    def on_loaded(self):
        self._source = self.options.get("source", "time")
        self._method = self.options.get("method", "sysfs")
        self._bl_path = self.options.get("backlight_path") or self._detect_backlight()
        self._gpio_pin = int(self.options.get("gpio_pin", 18))
        self._min_b = float(self.options.get("min_brightness", 10))
        self._max_b = float(self.options.get("max_brightness", 100))
        self._lux_low = float(self.options.get("lux_low", 5))
        self._lux_high = float(self.options.get("lux_high", 300))
        self._day_start = int(self.options.get("day_start", 8))
        self._night_start = int(self.options.get("night_start", 22))
        self._day_b = float(self.options.get("day_brightness", 100))
        self._night_b = float(self.options.get("night_brightness", 20))
        logging.info("[auto_dim] loaded (source=%s method=%s)", self._source, self._method)

    def _detect_backlight(self):
        try:
            entries = sorted(os.listdir(_BL_BASE))
            return os.path.join(_BL_BASE, entries[0]) if entries else None
        except Exception:
            return None

    # -- core (testable) ---------------------------------------------------------------
    def _read_lux(self):
        try:
            import board
            import adafruit_tsl2591
            return float(adafruit_tsl2591.TSL2591(board.I2C()).lux)
        except Exception:
            return None

    def current_brightness(self, hour=None, lux=None):
        if self._source == "lux":
            l = lux if lux is not None else self._read_lux()
            if l is not None:
                return round(brightness_for_lux(l, self._lux_low, self._lux_high,
                                                self._min_b, self._max_b))
        h = hour if hour is not None else time.localtime().tm_hour
        return round(brightness_for_time(h, self._day_start, self._night_start,
                                         self._day_b, self._night_b))

    # -- apply (guarded) ---------------------------------------------------------------
    def _apply(self, pct):
        self._last_applied = pct
        try:
            if self._method == "sysfs" and self._bl_path:
                with open(os.path.join(self._bl_path, "max_brightness")) as fp:
                    mx = int(fp.read().strip())
                val = max(0, min(mx, int(round(mx * pct / 100.0))))
                with open(os.path.join(self._bl_path, "brightness"), "w") as fp:
                    fp.write(str(val))
            elif self._method == "gpio":
                if self._backend is None:
                    from gpiozero import PWMOutputDevice
                    self._backend = PWMOutputDevice(self._gpio_pin)
                self._backend.value = max(0.0, min(1.0, pct / 100.0))
        except Exception as e:
            logging.debug("[auto_dim] apply failed: %s", e)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        target = self.current_brightness()
        if self._last_applied is None or abs(target - self._last_applied) >= 2:
            self._apply(target)

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("dim", LabeledValue(color=BLACK, label="dim:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            v = self._last_applied if self._last_applied is not None else self.current_brightness()
            ui.set("dim", "%d%%" % v)

    def on_unload(self, ui):
        try:
            if self._backend is not None:
                self._backend.close()
        except Exception:
            pass
        with ui._lock:
            if ui.has_element("dim"):
                ui.remove_element("dim")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>Auto-Dim</h1>"
                "<ul><li>source: {}</li><li>method: {}</li><li>current: {}%</li></ul>"
                "</body></html>").format(self._source, self._method,
                                         self._last_applied if self._last_applied is not None
                                         else self.current_brightness())
