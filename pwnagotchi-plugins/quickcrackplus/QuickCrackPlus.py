import os
import glob
import time
import logging
import subprocess
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class QuickCrackPlus(plugins.Plugin):
    """
    QuickCrackPlus - pwnagotchi plugin

    A ground-up replacement for the community `quickdic.py` /
    `better_quickdic.py` / `pwnagotchi_fast_dictionary` family, fixing
    the specific problems found when their actual source was reviewed:

      - Those three all shell out to `aircrack-ng` synchronously inside
        `on_handshake`, blocking the pwnagotchi main loop for the whole
        crack attempt. This plugin runs each crack attempt on a
        background thread, same as RuleMutationCrack - the agent stays
        responsive no matter how long a wordlist pass takes.

      - `quickdic.py` / `better_quickdic.py` have no subprocess timeout
        at all - a big wordlist can hang indefinitely. `pwnagotchi_fast_dictionary`
        added a per-wordlist timeout but has a live bug: it calls
        `os.listdir()` with no argument, so it lists the current working
        directory instead of the configured wordlist folder. This plugin
        globs `*.txt` directly out of the configured folder and applies
        a real per-wordlist timeout via both `subprocess.run(timeout=...)`
        and hashcat's own `--runtime`.

      - None of the three do anything to validate the capture file format
        - they hand the raw filename to aircrack-ng and hope its pcap
        parser accepts whatever this fork wrote. This plugin converts
        through `hcxpcapngtool` first (which is pcapng-native, since
        this image only ever produces `.pcapng` files) - if that
        produces a non-empty `.hc22000` file, that itself is proof a
        crackable handshake/PMKID was present, no text-grepping or
        separate packet-layer check required.

      - Uses hashcat (`-m 22000`) instead of aircrack-ng for the actual
        crack, matching the format RuleMutationCrack already produces -
        one shared hc22000 pipeline instead of two different cracking
        tools maintained in parallel.

    Not SSID-scoped like ClaudeCrackAuto/HandshakeCompleter/RuleMutationCrack -
    this only ever operates on a handshake file already captured and
    sitting on disk. It doesn't touch the radio or target any network
    itself, so the same "own SSIDs only" gating that applies to active
    attack plugins doesn't apply here.

    Required tools: hcxpcapngtool (hcxtools), hashcat
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Non-blocking dictionary crack for every captured handshake: '
        'converts via hcxpcapngtool (pcapng-native), then runs hashcat '
        'against configured wordlists with a real per-wordlist timeout. '
        'Fixes the main-loop-blocking, missing-timeout, and wordlist- '
        'discovery bugs found in the community quickdic/fast_dictionary '
        'plugins.'
    )

    EXPORT_DIR_DEFAULT = '/home/pi/quickcrackplus/exports'
    LOG_FILE_DEFAULT = '/home/pi/quickcrackplus/results.log'

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

        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        for tool in ('hcxpcapngtool', 'hashcat'):
            if not self._tool_exists(tool):
                logging.error("[QuickCrackPlus] required tool '%s' not found", tool)

        if not os.path.isdir(self.wordlist_folder):
            logging.warning("[QuickCrackPlus] wordlist_folder '%s' does not exist - "
                            "nothing will be crackable until it does",
                            self.wordlist_folder)

        self.ready = True
        logging.info("[QuickCrackPlus] plugin loaded, wordlist_folder=%s",
                    self.wordlist_folder)

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
                return

            hc_path = os.path.join(self.export_dir, f"{ssid}_{int(time.time())}.hc22000")
            if not self._convert(pcap_path, hc_path):
                self._log(f"'{ssid}': no crackable handshake/PMKID found in {pcap_path}, skipping")
                return

            # correctly glob the CONFIGURED folder, not cwd
            wordlists = sorted(glob.glob(os.path.join(self.wordlist_folder, '*.txt')))
            if not wordlists:
                self._log(f"'{ssid}': converted OK but no .txt wordlists found in "
                          f"{self.wordlist_folder}")
                return

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
        logging.info("[QuickCrackPlus] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[QuickCrackPlus] could not write log file: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
