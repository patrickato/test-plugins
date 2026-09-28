import os
import shutil
import logging
import subprocess
from datetime import datetime

import pwnagotchi.plugins as plugins


class HandshakeMerge(plugins.Plugin):
    """
    HandshakeMerge - pwnagotchi plugin

    Every time a handshake event fires for an AP, this plugin archives a
    timestamped snapshot of that capture, then merges every snapshot
    ever collected for that AP (across this session and any prior ones)
    into a single combined pcap using `mergecap` (part of the standard
    Wireshark/tshark tools). The idea: if session 1 caught EAPOL message
    1+2 but not 3+4, and session 3 (days later) caught 2+3+4 but missed
    1, the merged file may contain enough pieces across both to form a
    complete exchange that neither capture had alone - instead of
    needing one single session to catch the whole thing outright.

    This doesn't attempt to classify or crack anything itself - it just
    keeps every AP's fullest-possible combined capture ready for
    whatever does that next (HandshakeCompleter, ClaudeCrackAuto, or
    hcxpcapngtool by hand).

    NOTE: this assumes pwnagotchi writes/overwrites one pcap file per
    AP (the `filename` on_handshake gives you) rather than
    automatically keeping every session's file separately. If your
    build already preserves per-session files distinctly, you may not
    need the archiving step - check your handshake directory structure
    before assuming you need this.

    Required tool: `mergecap` (package: wireshark-common or tshark)
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Archives a timestamped snapshot of every handshake capture and '
        'merges all snapshots for the same AP (across sessions) into '
        'one combined pcap with mergecap, so partial captures collected '
        'at different times can add up to a complete exchange.'
    )

    ARCHIVE_DIR_DEFAULT = '/home/pi/handshakemerge/archive'
    MERGED_DIR_DEFAULT = '/home/pi/handshakemerge/merged'
    LOG_FILE_DEFAULT = '/home/pi/handshakemerge/results.log'

    def __init__(self):
        self.ready = False

    def on_loaded(self):
        cfg = self.options
        self.archive_dir = cfg.get('archive_dir', self.ARCHIVE_DIR_DEFAULT)
        self.merged_dir = cfg.get('merged_dir', self.MERGED_DIR_DEFAULT)
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        os.makedirs(self.archive_dir, exist_ok=True)
        os.makedirs(self.merged_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self._tool_exists('mergecap'):
            logging.error(
                "[HandshakeMerge] mergecap not found on PATH. Install "
                "wireshark-common (sudo apt install wireshark-common, "
                "answer 'No' to the dumpcap-as-non-root prompt if asked) "
                "- this plugin cannot merge captures without it."
            )

        self.ready = True
        logging.info("[HandshakeMerge] plugin loaded, archive_dir=%s, merged_dir=%s",
                     self.archive_dir, self.merged_dir)

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready:
            return

        bssid = (access_point or {}).get('mac', '').lower().replace(':', '')
        ssid = (access_point or {}).get('hostname', '') or '(hidden)'

        if not bssid or not os.path.exists(filename):
            return

        # archive this snapshot with a timestamp so it's never overwritten
        ap_archive_dir = os.path.join(self.archive_dir, bssid)
        os.makedirs(ap_archive_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_path = os.path.join(ap_archive_dir, f"{timestamp}.pcap")

        try:
            shutil.copy2(filename, snapshot_path)
        except Exception as e:
            self._log(f"ERROR: could not archive snapshot for '{ssid}': {e}")
            return

        self._log(f"'{ssid}' ({bssid}): archived snapshot {snapshot_path}")

        # merge every snapshot ever collected for this AP
        self._merge_all(bssid, ssid, ap_archive_dir)

    def _merge_all(self, bssid, ssid, ap_archive_dir):
        if not self._tool_exists('mergecap'):
            return

        snapshots = sorted(
            os.path.join(ap_archive_dir, f) for f in os.listdir(ap_archive_dir)
            if f.endswith('.pcap')
        )
        if len(snapshots) < 2:
            self._log(f"'{ssid}': only {len(snapshots)} snapshot(s) so far, "
                      f"nothing to merge yet")
            return

        merged_path = os.path.join(self.merged_dir, f"{bssid}_merged.pcap")
        try:
            proc = subprocess.run(
                ['mergecap', '-w', merged_path] + snapshots,
                capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0 and os.path.exists(merged_path):
                self._log(f"'{ssid}': merged {len(snapshots)} snapshots into "
                          f"{merged_path}")
            else:
                self._log(f"'{ssid}': mergecap failed: {proc.stderr}")
        except subprocess.TimeoutExpired:
            self._log(f"'{ssid}': mergecap timed out")
        except FileNotFoundError:
            logging.error("[HandshakeMerge] mergecap not installed")

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[HandshakeMerge] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[HandshakeMerge] could not write log file: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
