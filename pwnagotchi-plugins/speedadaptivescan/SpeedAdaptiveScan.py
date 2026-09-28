import json
import socket
import logging
import threading
import time
from datetime import datetime

import pwnagotchi.plugins as plugins


class SpeedAdaptiveScan(plugins.Plugin):
    """
    SpeedAdaptiveScan - pwnagotchi plugin

    Adjusts bettercap's WiFi channel-hopping dwell time based on
    GPS-derived speed: dwell longer per channel while stationary (more
    thorough scanning of a fixed spot), hop faster while moving (so a
    walking/driving perimeter loop doesn't sit too long on one channel
    and miss APs elsewhere along the route).

    Uses bettercap's live `set wifi.hopping.period <ms>` command
    through the agent, rather than a personality setting - unlike
    personality.* config (read once at startup), bettercap module
    options set this way DO take effect immediately on a running
    session, which is what makes continuous speed-based adjustment
    possible at all.

    Required: gpsd running and reachable (same as GPSModeSwitch/
    DeauthGeofence).
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Adjusts WiFi channel-hop dwell time live based on GPS speed - '
        'longer dwell while stationary, faster hopping while moving, '
        'via bettercap\'s "set wifi.hopping.period" command.'
    )

    LOG_FILE_DEFAULT = '/home/pi/speedadaptivescan/results.log'

    def __init__(self):
        self.ready = False
        self.stop_event = threading.Event()
        self.agent_ref = None
        self.current_mode = None  # "stationary" or "moving"

    def on_loaded(self):
        cfg = self.options
        self.stationary_dwell_ms = int(cfg.get('stationary_dwell_ms', 500))
        self.moving_dwell_ms = int(cfg.get('moving_dwell_ms', 150))
        self.speed_threshold_mps = float(cfg.get('speed_threshold_mps', 1.0))
        self.check_interval_secs = int(cfg.get('check_interval_secs', 15))
        self.gpsd_host = cfg.get('gpsd_host', 'localhost')
        self.gpsd_port = int(cfg.get('gpsd_port', 2947))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self.ready = True
        logging.info("[SpeedAdaptiveScan] plugin loaded, stationary=%dms, "
                     "moving=%dms, threshold=%.1fm/s", self.stationary_dwell_ms,
                     self.moving_dwell_ms, self.speed_threshold_mps)

        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()

    def on_unload(self, ui):
        self.stop_event.set()

    def on_wifi_update(self, agent, access_points):
        self.agent_ref = agent

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            speed = self._get_gps_speed()
            if speed is not None:
                mode = "moving" if speed >= self.speed_threshold_mps else "stationary"
                if mode != self.current_mode:
                    self.current_mode = mode
                    self._apply_dwell(mode, speed)
            time.sleep(self.check_interval_secs)

    def _get_gps_speed(self):
        """Reads speed (m/s) from gpsd's TPV report. Returns None if
        unavailable."""
        try:
            with socket.create_connection((self.gpsd_host, self.gpsd_port), timeout=5) as sock:
                sock.sendall(b'?WATCH={"enable":true,"json":true}\n')
                buf = sock.makefile()
                for _ in range(20):
                    line = buf.readline()
                    if not line:
                        break
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if msg.get('class') == 'TPV' and 'speed' in msg:
                        return msg['speed']
        except Exception as e:
            logging.debug("[SpeedAdaptiveScan] could not read gpsd speed: %s", e)
        return None

    def _apply_dwell(self, mode, speed):
        dwell_ms = self.moving_dwell_ms if mode == "moving" else self.stationary_dwell_ms

        if not self.agent_ref:
            logging.warning("[SpeedAdaptiveScan] no agent reference yet, "
                            "cannot apply dwell change")
            return

        try:
            self.agent_ref.run(f'set wifi.hopping.period {dwell_ms}')
            self._log(f"speed={speed:.2f}m/s -> mode={mode}, "
                      f"hop dwell set to {dwell_ms}ms")
        except Exception as e:
            logging.error("[SpeedAdaptiveScan] 'set wifi.hopping.period' failed: "
                          "%s - check the exact bettercap option name for your "
                          "version (try 'wifi.hop.period' as an alternative)", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[SpeedAdaptiveScan] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[SpeedAdaptiveScan] could not write log file: %s", e)
