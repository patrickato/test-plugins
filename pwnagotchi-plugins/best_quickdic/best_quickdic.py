import os
import glob
import time
import logging
import subprocess
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class BestQuickdic(plugins.Plugin):
    """
    best_quickdic - pwnagotchi plugin

    A dictionary-crack plugin for every captured handshake, written to
    replace the community quickdic.py / better_quickdic.py /
    pwnagotchi_fast_dictionary trio after a source-level review of all
    three turned up specific, concrete problems:

      - quickdic.py and better_quickdic.py both shell out to aircrack-ng
        SYNCHRONOUSLY inside on_handshake, with no timeout. That blocks
        the pwnagotchi main loop for the full duration of the crack
        attempt - a large wordlist can hang the agent indefinitely.
        best_quickdic runs every crack attempt on a background thread,
        so the agent stays responsive no matter how long a pass takes.

      - pwnagotchi_fast_dictionary added a per-wordlist timeout, but its
        wordlist-discovery code calls os.listdir() with NO argument -
        it lists the current working directory instead of the
        configured wordlist folder, so as shipped it usually can't find
        the user's actual wordlists. best_quickdic globs the configured
        folder directly (glob.glob(os.path.join(wordlist_folder, '*.txt'))),
        so this can't silently point at the wrong directory.

      - None of the three validate the capture file itself before
        running a subprocess - they hand the raw filename straight to
        aircrack-ng and rely on whatever pcap parsing its installed
        build happens to support, or (fast_dictionary) do a separate
        scapy pass just to check for an EAPOL layer. best_quickdic
        converts through hcxpcapngtool first - the tool built for this
        fork's .pcapng capture format - and treats a non-empty
        .hc22000 output as proof a crackable handshake/PMKID was
        present. No text-grepping, no separate verification pass.

      - Cracks with hashcat (-m 22000) instead of aircrack-ng, with a
        real timeout enforced two ways: hashcat's own --runtime flag,
        plus a subprocess.run(timeout=...) backstop in case hashcat
        itself hangs.

    Not SSID-scoped. It never touches the radio or targets a network -
    it only ever operates on a handshake file that's already been
    captured and is sitting on disk. That's pure local post-processing,
    not active behavior against any network, so it doesn't carry the
    same "own SSIDs only" gating that active attack/assoc/deauth
    plugins need.

    Required tools: hcxpcapngtool (hcxtools), hashcat
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Non-blocking dictionary crack for every captured handshake: '
        'converts via hcxpcapngtool (pcapng-native), then runs hashcat '
        'against configured wordlists with a real per-wordlist timeout. '
        'Replaces quickdic.py / better_quickdic.py / '
        'pwnagotchi_fast_dictionary - fixes the main-loop-blocking, '
        'missing-timeout, and wordlist-discovery bugs found in review '
        'of all three.'
    )

    EXPORT_DIR_DEFAULT = '/home/pi/best_quickdic/exports'
    LOG_FILE_DEFAULT = '/home/pi/best_quickdic/results.log'

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.processed = set()

    def on_loaded(self):
        cfg = self.options
        self.wordlist_folder = cfg.get('wordlist_folder', '/home/pi/wordlists')
        self.export_dir = cfg.get('export_dir', self.EXPORT_DIR_DEFAULT)
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)
        self.per_wordlist_timeout = int(cfg.get('per_wordlist_timeout_secs', 300))
        self.convert_timeout = int(cfg.get('convert_timeout_secs', 60))
        self.max_wordlists = int(cfg.get('max_wordlists_per_handshake', 0))  # 0 = no limit

        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        missing_tools = [t for t in ('hcxpcapngtool', 'hashcat') if not self._tool_exists(t)]
        if missing_tools:
            logging.error("[best_quickdic] required tool(s) not found: %s - "
                          "plugin will load but every crack attempt will fail",
                          ', '.join(missing_tools))

        if not os.path.isdir(self.wordlist_folder):
            logging.warning("[best_quickdic] wordlist_folder '%s' does not exist - "
                            "nothing will be crackable until it does",
                            self.wordlist_folder)

        self.ready = True
        logging.info("[best_quickdic] plugin loaded, wordlist_folder=%s, "
                    "per_wordlist_timeout_secs=%d",
                    self.wordlist_folder, self.per_wordlist_timeout)

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready:
            return

        if filename in self.processed:
            return
        self.processed.add(filename)

        ssid = (access_point or {}).get('hostname', '') or 'unknown'

        t = threading.Thread(target=self._process, args=(filename, ssid))
        t.daemon = True
        t.start()

    def _process(self, pcap_path, ssid):
        with self.lock:
            if not os.path.exists(pcap_path):
                self._log(f"'{ssid}': {pcap_path} no longer exists, skipping")
                return

            hc_path = os.path.join(self.export_dir, f"{ssid}_{int(time.time())}.hc22000")
            if not self._convert(pcap_path, hc_path):
                self._log(f"'{ssid}': no crackable handshake/PMKID found in "
                          f"{pcap_path}, skipping")
                return

            wordlists = sorted(glob.glob(os.path.join(self.wordlist_folder, '*.txt')))
            if not wordlists:
                self._log(f"'{ssid}': converted OK but no .txt wordlists found in "
                          f"{self.wordlist_folder}")
                return

            if self.max_wordlists > 0:
                wordlists = wordlists[:self.max_wordlists]

            for wl in wordlists:
                self._log(f"'{ssid}': trying {os.path.basename(wl)} "
                          f"(timeout={self.per_wordlist_timeout}s)")
                result = self._run_hashcat(hc_path, wl, self.per_wordlist_timeout)
                if result:
                    self._log(f"'{ssid}': CRACKED with {os.path.basename(wl)} -> {result}")
                    return

            self._log(f"'{ssid}': not found in any of {len(wordlists)} wordlist(s)")

    def _convert(self, pcap_path, hc_path):
        try:
            subprocess.run(['hcxpcapngtool', '-o', hc_path, pcap_path],
                          capture_output=True, text=True, timeout=self.convert_timeout)
            return os.path.exists(hc_path) and os.path.getsize(hc_path) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _run_hashcat(self, hc_path, wordlist, timeout):
        out_path = hc_path + '.cracked'
        cmd = ['hashcat', '-m', '22000', hc_path, wordlist,
               '--quiet', '--potfile-disable', '--runtime', str(timeout),
               '-o', out_path, '--outfile-format', '2']
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, 'r') as f:
                    return f.readline().strip() or None
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[best_quickdic] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[best_quickdic] could not write log file: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
