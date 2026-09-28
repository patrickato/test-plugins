import os
import time
import logging
import subprocess
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class RuleMutationCrack(plugins.Plugin):
    """
    RuleMutationCrack - pwnagotchi plugin

    For your own whitelisted SSIDs (config: `targets`), after
    converting a handshake to .hc22000, this plugin first tries a
    plain wordlist pass (fast), and if that doesn't find anything,
    retries with a hashcat rule file applied on top of the same
    wordlist - covering common human mutations (appended digits,
    capitalization, l33t-speak substitutions) that a flat dictionary
    pass alone would miss. More realistic coverage of how people
    actually vary a base password, without needing a much larger
    wordlist.

    Only ever acts on SSIDs explicitly listed in `targets` - same
    scoping principle as ClaudeCrackAuto and HandshakeCompleter.
    Everything this plugin captures for a non-listed SSID is left
    completely alone.

    Required tools: hcxpcapngtool (hcxtools), hashcat
    A rule file: hashcat ships several under /usr/share/hashcat/rules/
    on most installs - best64.rule is a reasonable default (fast,
    decent coverage); dive.rule is much larger and far slower but more
    thorough, if you have time to let it run.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'For whitelisted own networks: tries a plain wordlist crack '
        'first, then falls back to a hashcat rule-based mutation '
        'attack (appended digits, casing, leetspeak) on the same '
        'wordlist if the plain pass fails - more realistic coverage '
        'than a flat dictionary alone.'
    )

    EXPORT_DIR_DEFAULT = '/home/pi/rulemutationcrack/exports'
    LOG_FILE_DEFAULT = '/home/pi/rulemutationcrack/results.log'

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.processed = set()

    def on_loaded(self):
        cfg = self.options
        self.targets = [s.strip().lower() for s in cfg.get('targets', [])]
        self.wordlist = cfg.get('wordlist', '/home/pi/wordlists/rockyou.txt')
        self.rules_file = cfg.get('rules_file', '/usr/share/hashcat/rules/best64.rule')
        self.export_dir = cfg.get('export_dir', self.EXPORT_DIR_DEFAULT)
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)
        self.plain_timeout = int(cfg.get('plain_pass_timeout_secs', 300))
        self.rule_timeout = int(cfg.get('rule_pass_timeout_secs', 1800))

        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self.targets:
            logging.warning("[RuleMutationCrack] no SSIDs in `targets` - loaded "
                            "but nothing will be acted on")

        for tool in ('hcxpcapngtool', 'hashcat'):
            if not self._tool_exists(tool):
                logging.error("[RuleMutationCrack] required tool '%s' not found", tool)

        if not os.path.exists(self.rules_file):
            logging.warning("[RuleMutationCrack] rules_file '%s' not found - "
                            "rule-based pass will be skipped until it exists",
                            self.rules_file)

        self.ready = True
        logging.info("[RuleMutationCrack] plugin loaded, targets=%s", self.targets)

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready:
            return

        ssid = (access_point or {}).get('hostname', '') or ''
        bssid = (access_point or {}).get('mac', '') or ''

        if not ssid or ssid.lower() not in self.targets:
            return

        if filename in self.processed:
            return
        self.processed.add(filename)

        t = threading.Thread(target=self._process, args=(filename, ssid, bssid))
        t.daemon = True
        t.start()

    def _process(self, pcap_path, ssid, bssid):
        with self.lock:
            if not os.path.exists(pcap_path):
                return

            hc_path = os.path.join(self.export_dir, f"{ssid}_{int(time.time())}.hc22000")
            if not self._convert(pcap_path, hc_path):
                self._log(f"'{ssid}': no crackable handshake/PMKID found, skipping")
                return

            self._log(f"'{ssid}': starting plain wordlist pass (timeout={self.plain_timeout}s)")
            result = self._run_hashcat(hc_path, rule_file=None, timeout=self.plain_timeout)

            if result:
                self._log(f"'{ssid}': CRACKED on plain pass -> {result}")
                return

            self._log(f"'{ssid}': plain pass found nothing")

            if not os.path.exists(self.rules_file):
                self._log(f"'{ssid}': rules_file missing, skipping rule-based pass")
                return

            self._log(f"'{ssid}': starting rule-based pass with {self.rules_file} "
                      f"(timeout={self.rule_timeout}s)")
            result = self._run_hashcat(hc_path, rule_file=self.rules_file, timeout=self.rule_timeout)

            if result:
                self._log(f"'{ssid}': CRACKED on rule-based pass -> {result}")
            else:
                self._log(f"'{ssid}': not found even with rule-based mutations "
                          f"against {self.wordlist}")

    def _convert(self, pcap_path, hc_path):
        try:
            subprocess.run(['hcxpcapngtool', '-o', hc_path, pcap_path],
                          capture_output=True, text=True, timeout=120)
            return os.path.exists(hc_path) and os.path.getsize(hc_path) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _run_hashcat(self, hc_path, rule_file, timeout):
        out_path = hc_path + '.cracked'
        cmd = ['hashcat', '-m', '22000', hc_path, self.wordlist,
               '--quiet', '--potfile-disable', '-o', out_path, '--outfile-format', '2']
        if rule_file:
            cmd += ['-r', rule_file]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, 'r') as f:
                    return f.readline().strip() or None
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[RuleMutationCrack] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[RuleMutationCrack] could not write log file: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
