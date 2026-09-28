import logging
import threading
import time
from datetime import datetime

import pwnagotchi.plugins as plugins


class DeadZoneFeedback(plugins.Plugin):
    """
    DeadZoneFeedback - pwnagotchi plugin

    Real-time GPIO buzzer/LED feedback on signal strength toward ONE
    specific target AP (your own), so you get immediate "warmer/colder"
    feedback while physically walking around with the unit, instead of
    reviewing a log afterward.

    Feedback pattern: the weaker the signal, the slower the
    beep/blink; the stronger, the faster - a simple, immediately
    readable signal-strength indicator without needing to look at a
    screen.

    Uses the `gpiozero` library (standard on Raspberry Pi OS) to drive
    a buzzer and/or LED on the GPIO pins you specify. If you only have
    one of the two wired up, leave the other pin unset and this plugin
    will just skip it.

    Hardware: a passive buzzer and/or LED wired to a GPIO pin + ground,
    same as any basic GPIO output device. Not included/assumed -
    you'll need to wire this yourself if you don't already have it.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Real-time GPIO buzzer/LED feedback on signal strength toward '
        'a single target AP - faster beep/blink as you get closer, '
        'for immediate feedback while walking a test route.'
    )

    def __init__(self):
        self.ready = False
        self.stop_event = threading.Event()
        self.current_rssi = None
        self.buzzer = None
        self.led = None

    def on_loaded(self):
        cfg = self.options
        self.target_ssid = (cfg.get('target_ssid', '') or '').lower()
        self.buzzer_pin = cfg.get('buzzer_pin')
        self.led_pin = cfg.get('led_pin')
        self.weak_rssi_dbm = int(cfg.get('weak_rssi_dbm', -85))
        self.strong_rssi_dbm = int(cfg.get('strong_rssi_dbm', -40))
        self.min_pulse_secs = float(cfg.get('min_pulse_secs', 0.15))
        self.max_pulse_secs = float(cfg.get('max_pulse_secs', 1.5))

        if not self.target_ssid:
            logging.warning("[DeadZoneFeedback] no target_ssid set - plugin "
                            "loaded but has nothing to track")

        try:
            if self.buzzer_pin is not None:
                from gpiozero import Buzzer
                self.buzzer = Buzzer(int(self.buzzer_pin))
            if self.led_pin is not None:
                from gpiozero import LED
                self.led = LED(int(self.led_pin))
        except Exception as e:
            logging.error("[DeadZoneFeedback] could not initialize GPIO device(s): "
                          "%s - is gpiozero installed and are the pins correct?", e)

        self.ready = True
        logging.info("[DeadZoneFeedback] plugin loaded, target_ssid=%s, "
                     "buzzer_pin=%s, led_pin=%s", self.target_ssid,
                     self.buzzer_pin, self.led_pin)

        t = threading.Thread(target=self._pulse_loop, daemon=True)
        t.start()

    def on_unload(self, ui):
        self.stop_event.set()
        if self.buzzer:
            self.buzzer.off()
        if self.led:
            self.led.off()

    def on_wifi_update(self, agent, access_points):
        if not self.ready or not self.target_ssid:
            return

        for ap in access_points:
            ssid = (ap.get('hostname') or ap.get('ssid') or '').lower()
            if ssid == self.target_ssid:
                self.current_rssi = ap.get('rssi')
                return

        self.current_rssi = None  # target not currently visible

    # ---------------------------------------------------------------

    def _pulse_loop(self):
        while not self.stop_event.is_set():
            rssi = self.current_rssi

            if rssi is None:
                # target not visible - steady off, slow idle check
                if self.buzzer:
                    self.buzzer.off()
                if self.led:
                    self.led.off()
                time.sleep(1.0)
                continue

            pulse_interval = self._rssi_to_interval(rssi)

            if self.buzzer:
                self.buzzer.on()
            if self.led:
                self.led.on()
            time.sleep(0.08)  # short pulse "beep"
            if self.buzzer:
                self.buzzer.off()
            if self.led:
                self.led.off()

            time.sleep(max(pulse_interval - 0.08, 0.02))

    def _rssi_to_interval(self, rssi):
        """Maps RSSI to a pulse interval: weaker signal -> longer gap
        between beeps, stronger -> shorter gap (faster beeping)."""
        rssi = max(self.weak_rssi_dbm, min(self.strong_rssi_dbm, rssi))
        span = self.strong_rssi_dbm - self.weak_rssi_dbm
        if span <= 0:
            return self.min_pulse_secs
        fraction = (rssi - self.weak_rssi_dbm) / span  # 0 (weak) .. 1 (strong)
        return self.max_pulse_secs - fraction * (self.max_pulse_secs - self.min_pulse_secs)
