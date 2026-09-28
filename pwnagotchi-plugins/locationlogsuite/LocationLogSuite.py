import os
import csv
import json
import socket
import logging
import threading
import time
from datetime import datetime

import pwnagotchi.plugins as plugins


class LocationLogSuite(plugins.Plugin):
    """
    LocationLogSuite - pwnagotchi plugin

    Combines four related GPS-logging ideas into one plugin, since they
    all share the same underlying GPS read and reinforce each other
    (fix-quality context makes the heatmap and AP-location data
    trustworthy; the GPX track ties a session together spatially):

      1. Handshake Heatmap Log - GPS position + signal strength for
         every capture, building a cumulative heatmap of where on the
         property captures actually succeed.
      2. GPX Session Track Recorder - the physical path walked each
         session, as a standard GPX file importable into any mapping
         tool.
      3. AP First-Seen Location Log - the exact GPS point and
         timestamp where each new AP was first detected.
      4. GPS Fix-Quality Log - HDOP/satellite count/fix quality,
         embedded alongside every heatmap and AP-location entry (so
         you always know how trustworthy a given tagged position is),
         plus its own standalone periodic log if you want pure
         fix-quality history on its own cadence.

    A background thread maintains a persistent gpsd connection, keeping
    the latest position, speed, and fix quality (HDOP, satellite count,
    2D/3D mode from gpsd's TPV and SKY reports) available to the rest
    of the plugin without each event needing its own gpsd round-trip.

    Required: gpsd running and reachable (same as the other GPS
    plugins in this repo).
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Combined GPS logging: handshake heatmap, GPX session track, '
        'AP first-seen locations, and fix-quality context - all from '
        'one shared gpsd connection.'
    )

    BASE_DIR_DEFAULT = '/home/pi/locationlogsuite'

    def __init__(self):
        self.ready = False
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        self.last_lat = None
        self.last_lon = None
        self.last_speed = None
        self.last_hdop = None
        self.last_sats = None
        self.last_mode = None  # 1=no fix, 2=2D, 3=3D
        self.last_updated = None

        self.track_points = []
        self.known_bssids = set()

    def on_loaded(self):
        cfg = self.options
        base = cfg.get('base_dir', self.BASE_DIR_DEFAULT)
        self.heatmap_file = os.path.join(base, 'handshake_heatmap.csv')
        self.ap_first_seen_file = os.path.join(base, 'ap_first_seen.csv')
        self.fix_quality_file = os.path.join(base, 'fix_quality.csv')
        self.gpx_file = os.path.join(base, 'session_track.gpx')
        self.known_bssids_state_file = os.path.join(base, 'known_bssids.json')

        self.gpsd_host = cfg.get('gpsd_host', 'localhost')
        self.gpsd_port = int(cfg.get('gpsd_port', 2947))
        self.track_interval_secs = int(cfg.get('track_interval_secs', 20))
        self.gpx_flush_interval_secs = int(cfg.get('gpx_flush_interval_secs', 300))
        self.fix_quality_log_interval_secs = int(cfg.get('fix_quality_log_interval_secs', 60))

        os.makedirs(base, exist_ok=True)

        self._init_csv(self.heatmap_file,
                       ['timestamp', 'ssid', 'bssid', 'lat', 'lon', 'rssi',
                        'hdop', 'satellites', 'fix_mode'])
        self._init_csv(self.ap_first_seen_file,
                       ['timestamp', 'ssid', 'bssid', 'lat', 'lon',
                        'hdop', 'satellites', 'fix_mode'])
        self._init_csv(self.fix_quality_file,
                       ['timestamp', 'lat', 'lon', 'hdop', 'satellites', 'fix_mode'])

        self._load_known_bssids()

        self.ready = True
        logging.info("[LocationLogSuite] plugin loaded, base_dir=%s, "
                     "%d BSSID(s) already known", base, len(self.known_bssids))

        threading.Thread(target=self._gpsd_reader_loop, daemon=True).start()
        threading.Thread(target=self._periodic_loop, daemon=True).start()

    def on_unload(self, ui):
        self.stop_event.set()
        self._write_gpx()

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready:
            return
        ssid = (access_point or {}).get('hostname', '') or '(hidden)'
        bssid = (access_point or {}).get('mac', '') or ''
        rssi = (access_point or {}).get('rssi')

        with self.lock:
            if self.last_lat is None:
                logging.debug("[LocationLogSuite] no GPS fix yet, skipping "
                              "heatmap entry for '%s'", ssid)
                return
            self._append_csv(self.heatmap_file, [
                datetime.now().isoformat(timespec='seconds'), ssid, bssid,
                self.last_lat, self.last_lon, rssi, self.last_hdop,
                self.last_sats, self.last_mode
            ])

    def on_wifi_update(self, agent, access_points):
        if not self.ready:
            return
        with self.lock:
            if self.last_lat is None:
                return
            for ap in access_points:
                bssid = (ap.get('mac') or '').lower()
                if not bssid or bssid in self.known_bssids:
                    continue
                ssid = ap.get('hostname') or ap.get('ssid') or '(hidden)'
                self.known_bssids.add(bssid)
                self._append_csv(self.ap_first_seen_file, [
                    datetime.now().isoformat(timespec='seconds'), ssid, bssid,
                    self.last_lat, self.last_lon, self.last_hdop,
                    self.last_sats, self.last_mode
                ])
            self._save_known_bssids()

    # ---------------------------------------------------------------
    # gpsd reader - persistent connection, updates shared state
    # ---------------------------------------------------------------

    def _gpsd_reader_loop(self):
        while not self.stop_event.is_set():
            try:
                with socket.create_connection((self.gpsd_host, self.gpsd_port), timeout=10) as sock:
                    sock.sendall(b'?WATCH={"enable":true,"json":true}\n')
                    buf = sock.makefile()
                    while not self.stop_event.is_set():
                        line = buf.readline()
                        if not line:
                            break
                        try:
                            msg = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        with self.lock:
                            if msg.get('class') == 'TPV':
                                if 'lat' in msg and 'lon' in msg:
                                    self.last_lat = msg['lat']
                                    self.last_lon = msg['lon']
                                    self.last_updated = datetime.now()
                                if 'speed' in msg:
                                    self.last_speed = msg['speed']
                                if 'mode' in msg:
                                    self.last_mode = msg['mode']
                            elif msg.get('class') == 'SKY':
                                if 'hdop' in msg:
                                    self.last_hdop = msg['hdop']
                                if 'satellites' in msg:
                                    visible = [s for s in msg['satellites'] if s.get('used')]
                                    self.last_sats = len(visible)
            except Exception as e:
                logging.debug("[LocationLogSuite] gpsd connection issue: %s - retrying", e)
                time.sleep(5)

    def _periodic_loop(self):
        last_track = 0
        last_gpx_flush = 0
        last_fix_log = 0
        while not self.stop_event.is_set():
            now = time.time()

            with self.lock:
                has_fix = self.last_lat is not None

            if has_fix and now - last_track >= self.track_interval_secs:
                with self.lock:
                    self.track_points.append((datetime.now(), self.last_lat, self.last_lon))
                last_track = now

            if now - last_gpx_flush >= self.gpx_flush_interval_secs:
                self._write_gpx()
                last_gpx_flush = now

            if has_fix and now - last_fix_log >= self.fix_quality_log_interval_secs:
                with self.lock:
                    self._append_csv(self.fix_quality_file, [
                        datetime.now().isoformat(timespec='seconds'),
                        self.last_lat, self.last_lon, self.last_hdop,
                        self.last_sats, self.last_mode
                    ])
                last_fix_log = now

            time.sleep(2)

    # ---------------------------------------------------------------
    # GPX writing
    # ---------------------------------------------------------------

    def _write_gpx(self):
        with self.lock:
            points = list(self.track_points)

        if not points:
            return

        try:
            with open(self.gpx_file, 'w') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<gpx version="1.1" creator="LocationLogSuite">\n')
                f.write('  <trk><name>pwnagotchi session</name><trkseg>\n')
                for ts, lat, lon in points:
                    f.write(f'    <trkpt lat="{lat}" lon="{lon}">'
                           f'<time>{ts.isoformat()}</time></trkpt>\n')
                f.write('  </trkseg></trk>\n')
                f.write('</gpx>\n')
        except Exception as e:
            logging.warning("[LocationLogSuite] could not write GPX file: %s", e)

    # ---------------------------------------------------------------
    # small helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _init_csv(path, header):
        if not os.path.exists(path):
            try:
                with open(path, 'w', newline='') as f:
                    csv.writer(f).writerow(header)
            except Exception as e:
                logging.warning("[LocationLogSuite] could not create %s: %s", path, e)

    @staticmethod
    def _append_csv(path, row):
        try:
            with open(path, 'a', newline='') as f:
                csv.writer(f).writerow(row)
        except Exception as e:
            logging.warning("[LocationLogSuite] could not append to %s: %s", path, e)

    def _load_known_bssids(self):
        try:
            if os.path.exists(self.known_bssids_state_file):
                with open(self.known_bssids_state_file, 'r') as f:
                    self.known_bssids = set(json.load(f))
        except Exception as e:
            logging.warning("[LocationLogSuite] could not load known BSSIDs: %s", e)

    def _save_known_bssids(self):
        try:
            with open(self.known_bssids_state_file, 'w') as f:
                json.dump(list(self.known_bssids), f)
        except Exception as e:
            logging.warning("[LocationLogSuite] could not save known BSSIDs: %s", e)
