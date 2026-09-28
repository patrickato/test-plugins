import math
import json
import socket
import logging
import threading
import time
from datetime import datetime

import pwnagotchi.plugins as plugins


class DeauthGeofence(plugins.Plugin):
    """
    DeauthGeofence - pwnagotchi plugin

    A more surgical companion to GPSModeSwitch. Where GPSModeSwitch
    stops EVERYTHING (recon, PMKID, deauth) outside a boundary, this
    plugin keeps passive recon and PMKID collection running everywhere,
    and only arms deauth specifically while inside your configured
    property boundary - disarming just that one capability the instant
    you (or the unit, if mobile) leaves it.

    Use this instead of GPSModeSwitch when you want continuous
    passive/PMKID monitoring even when technically outside the
    boundary, but want an absolute guarantee that no deauth traffic
    ever goes out except within your defined zone.

    REQUIRES personality.deauth = false (same as PMKIDFirst/
    TargetedKick) so this plugin is the sole source of deauth activity
    and can gate it by location.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Arms deauth capability only while GPS shows the unit inside a '
        'configured boundary; disarms it (while leaving recon/PMKID '
        'running normally) outside. Requires personality.deauth = '
        'false so this plugin controls deauth exclusively.'
    )

    LOG_FILE_DEFAULT = '/home/pi/deauthgeofence/results.log'

    def __init__(self):
        self.ready = False
        self.armed = False
        self.stop_event = threading.Event()
        self.last_deauth = {}  # bssid -> datetime, basic safety cooldown

    def on_loaded(self):
        cfg = self.options
        self.center_lat = cfg.get('center_lat')
        self.center_lon = cfg.get('center_lon')
        self.radius_meters = float(cfg.get('radius_meters', 200))
        self.boundary_polygon = cfg.get('boundary_polygon', [])
        self.check_interval_secs = int(cfg.get('check_interval_secs', 30))
        self.per_ap_cooldown_secs = int(cfg.get('per_ap_cooldown_secs', 60))
        self.gpsd_host = cfg.get('gpsd_host', 'localhost')
        self.gpsd_port = int(cfg.get('gpsd_port', 2947))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self.ready = True
        logging.info("[DeauthGeofence] plugin loaded, check_interval_secs=%d. "
                     "Reminder: set personality.deauth = false for this "
                     "plugin to control deauth arming.", self.check_interval_secs)

        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()

    def on_unload(self, ui):
        self.stop_event.set()

    def on_wifi_update(self, agent, access_points):
        if not self.ready or not self.armed:
            return  # disarmed - do nothing, let recon/PMKID continue via core

        now = datetime.now()
        for ap in access_points:
            bssid = (ap.get('mac') or '').lower()
            clients = ap.get('clients') or []
            if not clients or not bssid:
                continue

            last = self.last_deauth.get(bssid)
            if last and (now - last).total_seconds() < self.per_ap_cooldown_secs:
                continue  # basic safety cooldown - for finer per-AP control,
                          # combine with AdaptiveDeauth or TargetedKick instead
                          # of relying on this plugin's location gate alone

            try:
                agent.deauth(ap, clients[0])
                self.last_deauth[bssid] = now
            except Exception as e:
                logging.debug("[DeauthGeofence] deauth call failed: %s", e)

    # ---------------------------------------------------------------

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            position = self._get_gps_position()
            if position:
                lat, lon = position
                inside = self._is_inside_boundary(lat, lon)
                if inside and not self.armed:
                    self.armed = True
                    self._log("entered boundary - deauth ARMED")
                elif not inside and self.armed:
                    self.armed = False
                    self._log("left boundary - deauth DISARMED (recon/PMKID continue)")
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
            logging.debug("[DeauthGeofence] could not read gpsd position: %s", e)
        return None

    def _is_inside_boundary(self, lat, lon):
        if self.boundary_polygon:
            return self._point_in_polygon(lat, lon, self.boundary_polygon)
        if self.center_lat is not None and self.center_lon is not None:
            return self._haversine_meters(lat, lon, self.center_lat, self.center_lon) <= self.radius_meters
        return False  # no boundary configured - stay disarmed to be safe

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

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[DeauthGeofence] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[DeauthGeofence] could not write log file: %s", e)
