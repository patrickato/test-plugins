"""fan_curve — real temperature-driven PWM fan control.

Most Pi fan setups are crude on/off. This drives a PWM fan from a configurable
temperature→duty curve with hysteresis, so the fan ramps smoothly and doesn't chatter near
the switch-on point. Pairs naturally with thermal_predictor (which can warn before the curve
even needs to react).

Hardware: a PWM-capable fan on a GPIO pin. The GPIO backend (gpiozero preferred, RPi.GPIO
fallback) is imported lazily and guarded — off a Pi, or with no backend installed, the plugin
still computes and reports duty, it just can't drive a pin.

Options (main.plugins.fan_curve.*):
    enabled      = true
    gpio_pin     = 18          # BCM pin driving the fan
    pwm_freq     = 100         # PWM frequency (Hz)
    curve        = [[50,0],[55,40],[65,70],[75,100]]   # [tempC, duty%]
    min_duty     = 30          # once on, never run slower than this (fans stall low)
    hysteresis_c = 4           # switch-off is this many C below switch-on
    invert       = false       # true for active-low fan circuits
    position     = "0,0"

Requires: pip `gpiozero` (or `RPi.GPIO`); PWM available on the pin; a PWM-capable fan.
"""
import logging
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def duty_for(temp, curve):
    """Piecewise-linear duty (%) for a temperature over a sorted [tempC, duty%] curve."""
    if not curve:
        return 0.0
    pts = sorted(curve, key=lambda p: p[0])
    if temp <= pts[0][0]:
        return float(pts[0][1])
    if temp >= pts[-1][0]:
        return float(pts[-1][1])
    for (t0, d0), (t1, d1) in zip(pts, pts[1:]):
        if t0 <= temp <= t1:
            frac = (temp - t0) / (t1 - t0) if t1 != t0 else 0
            return float(d0 + frac * (d1 - d0))
    return float(pts[-1][1])


class FanCurve(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Temperature→PWM fan curve with hysteresis."

    def __init__(self):
        self.options = dict()
        self._on = False
        self._backend = None
        self._last_duty = 0.0

    def on_loaded(self):
        self._pin = int(self.options.get("gpio_pin", 18))
        self._freq = int(self.options.get("pwm_freq", 100))
        self._curve = self.options.get("curve", [[50, 0], [55, 40], [65, 70], [75, 100]])
        self._min_duty = float(self.options.get("min_duty", 30))
        self._hysteresis = float(self.options.get("hysteresis_c", 4))
        self._invert = bool(self.options.get("invert", False))
        # on_temp = lowest curve temp with duty>0; off_temp = on_temp - hysteresis
        active = [p[0] for p in sorted(self._curve) if p[1] > 0]
        self._on_temp = active[0] if active else float("inf")
        self._off_temp = self._on_temp - self._hysteresis
        logging.info("[fan_curve] loaded (pin=%d on=%.0fC off=%.0fC)",
                     self._pin, self._on_temp, self._off_temp)

    def on_ready(self, agent):
        self._setup_gpio()

    # -- control logic (pure of hardware; testable) ------------------------------------
    def update_control(self, temp):
        target = duty_for(temp, self._curve)
        if self._on:
            if temp <= self._off_temp:
                self._on = False
                return 0.0
            return max(target, self._min_duty)
        else:
            if temp >= self._on_temp:
                self._on = True
                return max(target, self._min_duty)
            return 0.0

    # -- hardware ----------------------------------------------------------------------
    def _setup_gpio(self):
        try:
            from gpiozero import PWMOutputDevice
            self._backend = PWMOutputDevice(self._pin, frequency=self._freq)
            logging.info("[fan_curve] gpiozero backend ready on pin %d", self._pin)
            return
        except Exception as e:
            logging.debug("[fan_curve] gpiozero unavailable: %s", e)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._pin, GPIO.OUT)
            pwm = GPIO.PWM(self._pin, self._freq)
            pwm.start(0)
            self._backend = ("rpigpio", pwm)
            logging.info("[fan_curve] RPi.GPIO backend ready on pin %d", self._pin)
        except Exception as e:
            logging.warning("[fan_curve] no GPIO backend; running compute-only: %s", e)
            self._backend = None

    def _apply(self, duty):
        self._last_duty = duty
        out = (100.0 - duty) if self._invert else duty
        b = self._backend
        try:
            if b is None:
                return
            if isinstance(b, tuple) and b[0] == "rpigpio":
                b[1].ChangeDutyCycle(out)
            else:
                b.value = max(0.0, min(1.0, out / 100.0))
        except Exception as e:
            logging.debug("[fan_curve] apply failed: %s", e)

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        try:
            temp = float(pwnagotchi.temperature())
        except Exception:
            return
        self._apply(self.update_control(temp))

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("fan", LabeledValue(color=BLACK, label="fan:", value="0%",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("fan", "%d%%" % self._last_duty)

    def on_unload(self, ui):
        self._apply(0)
        try:
            if self._backend is not None and not isinstance(self._backend, tuple):
                self._backend.close()
        except Exception:
            pass
        with ui._lock:
            if ui.has_element("fan"):
                ui.remove_element("fan")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return (
            "<html><body><h1>Fan Curve</h1>"
            "<p>current duty: {:.0f}% (on={} on_temp={:.0f}C off_temp={:.0f}C)</p>"
            "<p>curve: {}</p></body></html>"
        ).format(self._last_duty, self._on, self._on_temp, self._off_temp, self._curve)
