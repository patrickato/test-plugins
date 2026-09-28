import os
import logging
import subprocess
from datetime import datetime

import pwnagotchi.plugins as plugins


class HashFormatDetector(plugins.Plugin):
    """
    HashFormatDetector - pwnagotchi plugin

    Inspects each capture and determines the correct cracking pathway
    instead of assuming every capture is a modern hashcat -m 22000 job:

        WEP          -> flags for aircrack-ng (statistical IV attack,
                         not a hashcat job at all - different tool
                         entirely)
        WPA/WPA2/PMKID -> converts via hcxpcapngtool to .hc22000 and
                         confirms hashcat mode 22000 (the current
                         unified mode covering both handshake and
                         PMKID - the old separate modes 2500/16800 are
                         deprecated on recent hashcat versions)
        no crypto detected -> flags as open network, no cracking
                         pathway applies at all

    This plugin only classifies and routes - it doesn't run hashcat or
    aircrack-ng itself (that's ClaudeCrackAuto's job for the WPA/PMKID
    path). It writes a small `.route` sidecar file next to each
    processed capture stating what was detected, so downstream tooling
    (or you, by hand) knows what to do with it without re-inspecting.

    Required tool: hcxpcapngtool (package: hcxtools)
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Classifies each capture and routes it to the correct cracking '
        'pathway (aircrack-ng for WEP, hashcat -m 22000 for WPA/WPA2/'
        'PMKID, or "open, nothing to crack") instead of assuming every '
        'capture is the same format.'
    )

    OUTPUT_DIR_DEFAULT = '/home/pi/hashformatdetector/routed'
    LOG_FILE_DEFAULT = '/home/pi/hashformatdetector/results.log'

    def __init__(self):
        self.ready = False

    def on_loaded(self):
        cfg = self.options
        self.output_dir = cfg.get('output_dir', self.OUTPUT_DIR_DEFAULT)
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self._tool_exists('hcxpcapngtool'):
            logging.error(
                "[HashFormatDetector] hcxpcapngtool not found on PATH. "
                "Install hcxtools (sudo apt install hcxtools)."
            )

        self.ready = True
        logging.info("[HashFormatDetector] plugin loaded, output_dir=%s", self.output_dir)

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready or not os.path.exists(filename):
            return

        ssid = (access_point or {}).get('hostname', '') or '(hidden)'
        bssid = (access_point or {}).get('mac', '') or ''
        encryption = (access_point.get('encryption') or '').upper() if access_point else ''

        route, detail = self._classify_and_route(filename, encryption, ssid, bssid)
        self._write_sidecar(filename, route, detail)
        self._log(f"'{ssid}' ({bssid}): route={route} - {detail}")

    def _classify_and_route(self, filename, encryption, ssid, bssid):
        if 'WEP' in encryption:
            return "aircrack-ng", (
                "WEP-encrypted - not a hashcat job. Use aircrack-ng's IV-based "
                "statistical attack instead, e.g.: aircrack-ng -b " + bssid + " " + filename
            )

        if not encryption or encryption in ('', 'NONE', 'OPEN'):
            return "none", "No encryption detected - open network, nothing to crack."

        # WPA/WPA2/WPA3-transition/PMKID - try converting via hcxpcapngtool
        if not self._tool_exists('hcxpcapngtool'):
            return "unknown", "hcxpcapngtool not installed, cannot confirm hashcat mode"

        hc_path = os.path.join(self.output_dir, f"{bssid.replace(':', '')}.hc22000")
        try:
            proc = subprocess.run(
                ['hcxpcapngtool', '-o', hc_path, filename],
                capture_output=True, text=True, timeout=120
            )
            if os.path.exists(hc_path) and os.path.getsize(hc_path) > 0:
                return "hashcat-22000", (
                    f"WPA/WPA2/PMKID material found - use hashcat -m 22000 "
                    f"against {hc_path}"
                )
            else:
                return "no-crackable-material", (
                    "Encrypted (non-WEP) but hcxpcapngtool found no crackable "
                    "handshake/PMKID material in this capture yet"
                )
        except subprocess.TimeoutExpired:
            return "unknown", "hcxpcapngtool timed out"
        except FileNotFoundError:
            return "unknown", "hcxpcapngtool not installed"

    def _write_sidecar(self, filename, route, detail):
        sidecar_path = filename + '.route'
        try:
            with open(sidecar_path, 'w') as f:
                f.write(f"route: {route}\n")
                f.write(f"detail: {detail}\n")
                f.write(f"checked_at: {datetime.now().isoformat(timespec='seconds')}\n")
        except Exception as e:
            logging.warning("[HashFormatDetector] could not write sidecar file: %s", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[HashFormatDetector] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[HashFormatDetector] could not write log file: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
