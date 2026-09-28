import json
import socket
import logging
import threading
import time
import math
from datetime import datetime

import pwnagotchi.plugins as plugins


class WaypointCoverage(plugins.Plugin):
    """
    WaypointCoverage - pwnagotchi plugin

    Program a patrol route as a list of named waypoints (lat/lon +
    arrival radius), and this plugin tracks which ones you've actually
    walked past during a session - live, as you go - so you can confirm
    a perimeter test actually covered the whole route instead of
    guessing afterward.

    Each waypoint gets marked "covered" the moment GPS shows you within
    its radius, with a timestamp. The on-screen display shows live
    progress (e.g. "3/7"), and marking a waypoint covered is logged
    immediately - this isn't a report generated after the fact, it
    updates in real time as you walk.

    Required: gpsd running and reachable (same as the other GPS
    plugins in this repo).
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Tracks which waypoints of a programmed patrol route have '
        'actually been walked past, live, as GPS confirms each one - '
        'so a perimeter test\'s coverage is confirmed, not assumed.'
    )

    LOG_FILE_DEFAULT = '/home/pi/waypointcoverage/results.log'

    def __init__(self):
        self.ready = False
        self.stop_event = threading.Event()
        self.waypoints = []  # list of dicts: name, lat, lon, radius, covered, covered_at

    def on_loaded(self):
        cfg = self.options
        raw_waypoints = cfg.get('waypoints', [])
        self.check_interval_secs = int(cfg.get('check_interval_secs', 10))
        self.gpsd_host = cfg.get('gpsd_host', 'localhost')
        self.gpsd_port = int(cfg.get('gpsd_port', 2947))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        for wp in raw_waypoints:
            self.waypoints.append({
                "name": wp.get("name", "unnamed"),
                "lat": wp["lat"],
                "lon": wp["lon"],
                "radius": wp.get("radius_meters", 15),
                "covered": False,
                "covered_at": None,
            })

        if not self.waypoints:
            logging.warning("[WaypointCoverage] no waypoints configured - "
                            "plugin loaded but has nothing to track")

        self.ready = True
        logging.info("[WaypointCoverage] plugin loaded, %d waypoint(s) programmed",
                     len(self.waypoints))

        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()

    def on_unload(self, ui):
        self.stop_event.set()

    def on_ui_setup(self, ui):
        components = __import__('pwnagotchi.ui.components', fromlist=['LabeledValue'])
        fonts = __import__('pwnagotchi.ui.fonts', fromlist=['Small', 'Bold'])
        ui.add_element('waypoints', components.LabeledValue(
            color=fonts.Small,
            label='WP',
            value='0/0',
            position=(ui.width() / 2 + 190, 0),
            label_font=fonts.Bold,
            text_font=fonts.Small,
        ))

    def on_ui_update(self, ui):
        covered = sum(1 for w in self.waypoints if w["covered"])
        ui.set('waypoints', f"{covered}/{len(self.waypoints)}")

    def on_unload_ui(self, ui):
        pass

    # ---------------------------------------------------------------

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            if self.waypoints:
                position = self._get_gps_position()
                if position:
                    lat, lon = position
                    self._check_waypoints(lat, lon)
            time.sleep(self.check_interval_secs)

    def _get_gps_position(self):
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
                    if msg.get('class') == 'TPV' and 'lat' in msg and 'lon' in msg:
                        return (msg['lat'], msg['lon'])
        except Exception as e:
            logging.debug("[WaypointCoverage] could not read gpsd position: %s", e)
        return None

    def _check_waypoints(self, lat, lon):
        for wp in self.waypoints:
            if wp["covered"]:
                continue
            distance = self._haversine_meters(lat, lon, wp["lat"], wp["lon"])
            if distance <= wp["radius"]:
                wp["covered"] = True
                wp["covered_at"] = datetime.now().isoformat(timespec='seconds')
                covered_count = sum(1 for w in self.waypoints if w["covered"])
                self._log(f"waypoint '{wp['name']}' reached "
                          f"({covered_count}/{len(self.waypoints)} covered)")
                if covered_count == len(self.waypoints):
                    self._log("ALL waypoints covered - route complete!")

    @staticmethod
    def _haversine_meters(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[WaypointCoverage] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[WaypointCoverage] could not write log file: %s", e)
