import math
import json
import socket
import logging
import threading
import time
from datetime import datetime

import pwnagotchi.plugins as plugins


class GPSModeSwitch(plugins.Plugin):
    """
    GPSModeSwitch - pwnagotchi plugin

    Automatically drops pwnagotchi to fully dormant the moment GPS
    shows the unit has left your configured property boundary, and
    resumes normal behavior once it's back inside.

    Boundary can be either a simple center point + radius (easiest to
    set up) or a polygon of lat/lon points (more precise for an
    irregularly-shaped property) - if `boundary_polygon` is set, it's
    used; otherwise `center_lat`/`center_lon`/`radius_meters` is used.

    Reads position directly from gpsd (the standard GPS daemon most
    GPS HATs run through) rather than through pwnagotchi's own GPS
    plugin internals, so this doesn't depend on that plugin's specific
    data format.

    How dormancy is actually enforced: this plugin calls
    `agent.run('wifi.recon off')` (a direct bettercap command, the same
    mechanism pwnagotchi's own core automata uses to drive bettercap)
    to stop channel hopping and all recon/attack activity outright, and
    `agent.run('wifi.recon on')` to resume. This is a more reliable
    lever than trying to toggle personality settings, which are only
    read once at startup and can't be changed live (see
    PassiveOnlyMode's README for why that approach doesn't work).

    NOTE: `agent.run()` availability/signature can vary by pwnagotchi
    version. Check the log after your first boundary crossing to
    confirm it worked - if it errors, you may need to adjust
    `_set_dormant()` for your specific build.

    Required: gpsd running and reachable (default localhost:2947,
    already the case on nearly all pwnagotchi GPS HAT setups).
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Drops pwnagotchi to fully dormant (wifi.recon off) the moment '
        'GPS shows it has left a configured property boundary (radius '
        'or polygon), and resumes when back inside.'
    )

    LOG_FILE_DEFAULT = '/home/pi/gpsmodeswitch/results.log'

    def __init__(self):
        self.ready = False
        self.dormant = False
        self.stop_event = threading.Event()
        self.agent_ref = None

    def on_loaded(self):
        cfg = self.options
        self.center_lat = cfg.get('center_lat')
        self.center_lon = cfg.get('center_lon')
        self.radius_meters = float(cfg.get('radius_meters', 200))
        self.boundary_polygon = cfg.get('boundary_polygon', [])  # list of [lat, lon]
        self.check_interval_secs = int(cfg.get('check_interval_secs', 30))
        self.gpsd_host = cfg.get('gpsd_host', 'localhost')
        self.gpsd_port = int(cfg.get('gpsd_port', 2947))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self.boundary_polygon and (self.center_lat is None or self.center_lon is None):
            logging.warning(
                "[GPSModeSwitch] no boundary_polygon and no center_lat/"
                "center_lon set - plugin loaded but has nothing to check "
                "against"
            )

        self.ready = True
        logging.info("[GPSModeSwitch] plugin loaded, check_interval_secs=%d",
                     self.check_interval_secs)

        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()

    def on_unload(self, ui):
        self.stop_event.set()

    def on_wifi_update(self, agent, access_points):
        # capture a reference to the live agent object for the monitor
        # thread to use, since on_loaded doesn't receive it directly
        self.agent_ref = agent

    # ---------------------------------------------------------------

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            position = self._get_gps_position()
            if position:
                lat, lon = position
                inside = self._is_inside_boundary(lat, lon)
                self._apply_state(inside)
            time.sleep(self.check_interval_secs)

    def _get_gps_position(self):
        """Reads one position report from gpsd via its JSON socket
        protocol. Returns (lat, lon) or None if unavailable."""
        try:
            with socket.create_connection((self.gpsd_host, self.gpsd_port), timeout=5) as sock:
                sock.sendall(b'?WATCH={"enable":true,"json":true}\n')
                buf = sock.makefile()
                for _ in range(20):  # read a handful of lines looking for a TPV report
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
            logging.debug("[GPSModeSwitch] could not read gpsd position: %s", e)
        return None

    def _is_inside_boundary(self, lat, lon):
        if self.boundary_polygon:
            return self._point_in_polygon(lat, lon, self.boundary_polygon)
        if self.center_lat is not None and self.center_lon is not None:
            distance = self._haversine_meters(lat, lon, self.center_lat, self.center_lon)
            return distance <= self.radius_meters
        return True  # no boundary configured - never trigger

    @staticmethod
    def _haversine_meters(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    @staticmethod
    def _point_in_polygon(lat, lon, polygon):
        # standard ray-casting point-in-polygon test
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            lat_i, lon_i = polygon[i]
            lat_j, lon_j = polygon[j]
            if ((lon_i > lon) != (lon_j > lon)) and \
               (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i + 1e-15) + lat_i):
                inside = not inside
            j = i
        return inside

    def _apply_state(self, inside):
        if inside and self.dormant:
            self.dormant = False
            self._set_dormant(False)
        elif not inside and not self.dormant:
            self.dormant = True
            self._set_dormant(True)

    def _set_dormant(self, dormant):
        if not self.agent_ref:
            logging.warning("[GPSModeSwitch] no agent reference yet, cannot "
                            "change state - will retry next check")
            return

        cmd = 'wifi.recon off' if dormant else 'wifi.recon on'
        try:
            self.agent_ref.run(cmd)
            self._log(f"boundary {'exited' if dormant else 're-entered'} - "
                      f"ran '{cmd}'")
        except Exception as e:
            logging.error("[GPSModeSwitch] agent.run('%s') failed: %s - your "
                          "pwnagotchi version's Agent may not expose run() "
                          "the same way, check and adjust _set_dormant()",
                          cmd, e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[GPSModeSwitch] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[GPSModeSwitch] could not write log file: %s", e)
