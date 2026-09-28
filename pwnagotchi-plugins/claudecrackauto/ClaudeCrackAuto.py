import os
import json
import time
import logging
import subprocess
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class ClaudeCrackAuto(plugins.Plugin):
    """
    ClaudeCrackAuto - pwnagotchi plugin

    Pipeline, run ONLY against SSIDs you explicitly own and list in the
    whitelist (config: main.plugins.ClaudeCrackAuto.whitelist):

      1. on_handshake fires when pwnagotchi writes a new .pcap
      2. SSID is checked against the whitelist - anything not listed is
         left completely alone (no conversion, no cracking, no touching
         the file at all beyond the normal pwnagotchi behavior)
      3. hcxpcapngtool validates the capture actually contains a crackable
         handshake or PMKID, and converts it to the modern .hc22000 format
      4. Depending on config, either:
           run_local = true  -> hashcat runs directly on the Pi against a
                                 wordlist you provide
           run_local = false -> the .hc22000 file is just exported to a
                                 folder for you to grab and crack elsewhere
                                 (e.g. a PC with a GPU)
      5. Result (cracked password, "not found", or "export only") is
         logged and optionally pushed to ntfy / a Discord webhook.

    This plugin does not touch, convert, or crack anything for an SSID
    that is not on your whitelist. It is meant for testing your own
    home network's password strength - not for use against networks you
    do not own or have explicit permission to test.

    Required tools on the Pi (install via apt/pip as needed):
      - hcxpcapngtool  (package: hcxtools)
      - hashcat        (only required if run_local = true)

    Example config.toml block - see config-example.toml in this repo.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Whitelist-gated pipeline: validates and converts captured '
        'handshakes for whitelisted home SSIDs, then optionally runs '
        'hashcat locally or exports for offline cracking on another '
        'machine. Only ever acts on SSIDs you explicitly list as your '
        'own.'
    )

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.last_result = "idle"
        self.processed = set()

    # ---------------------------------------------------------------
    # lifecycle
    # ---------------------------------------------------------------

    def on_loaded(self):
        cfg = self.options

        self.whitelist = [s.strip().lower() for s in cfg.get('whitelist', [])]
        self.run_local = bool(cfg.get('run_local', False))
        self.wordlist = cfg.get('wordlist', '/root/wordlists/rockyou.txt')
        self.handshake_dir = cfg.get('handshake_dir', '/home/pi/handshakes')
        self.export_dir = cfg.get('export_dir', '/home/pi/claudecrackauto/exports')
        self.log_file = cfg.get('log_file', '/home/pi/claudecrackauto/results.log')
        self.hashcat_timeout = int(cfg.get('hashcat_timeout_secs', 900))
        self.notify_enabled = bool(cfg.get('notify_enabled', False))
        self.notify_method = cfg.get('notify_method', 'ntfy')  # 'ntfy' or 'discord'
        self.ntfy_url = cfg.get('ntfy_url', '')
        self.discord_webhook = cfg.get('discord_webhook', '')

        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self.whitelist:
            logging.warning(
                "[ClaudeCrackAuto] No SSIDs in whitelist - plugin loaded "
                "but will not act on any handshake until you add your "
                "own SSIDs to main.plugins.ClaudeCrackAuto.whitelist"
            )

        if self.run_local and not self._tool_exists('hashcat'):
            logging.warning(
                "[ClaudeCrackAuto] run_local is true but hashcat was not "
                "found on PATH - cracking step will be skipped and the "
                "handshake will just be exported instead."
            )

        if not self._tool_exists('hcxpcapngtool'):
            logging.error(
                "[ClaudeCrackAuto] hcxpcapngtool not found on PATH. "
                "Install hcxtools (sudo apt install hcxtools) - this "
                "plugin cannot validate or convert handshakes without it."
            )

        self.ready = True
        logging.info("[ClaudeCrackAuto] plugin loaded, whitelist=%s, run_local=%s",
                     self.whitelist, self.run_local)

    def on_ui_setup(self, ui):
        ui.add_element('claudecrackauto', __import__('pwnagotchi.ui.components', fromlist=['LabeledValue']).LabeledValue(
            color=__import__('pwnagotchi.ui.fonts', fromlist=['Small']).Small,
            label='CCA',
            value='idle',
            position=(ui.width() / 2 + 10, 0),
            label_font=__import__('pwnagotchi.ui.fonts', fromlist=['Bold']).Bold,
            text_font=__import__('pwnagotchi.ui.fonts', fromlist=['Small']).Small,
        ))

    def on_ui_update(self, ui):
        ui.set('claudecrackauto', self.last_result[:10])

    def on_unload(self, ui):
        with ui._lock:
            try:
                ui.remove_element('claudecrackauto')
            except Exception:
                pass

    # ---------------------------------------------------------------
    # main hook
    # ---------------------------------------------------------------

    def on_handshake(self, agent, filename, access_point, client_station):
        if not self.ready:
            return

        ssid = (access_point or {}).get('hostname', '') or ''
        bssid = (access_point or {}).get('mac', '') or ''

        if not ssid or ssid.lower() not in self.whitelist:
            logging.info(
                "[ClaudeCrackAuto] skipping non-whitelisted SSID '%s' (%s) - "
                "left untouched", ssid, bssid
            )
            return

        if filename in self.processed:
            return
        self.processed.add(filename)

        # run pipeline in background so we never block pwnagotchi's main loop
        t = threading.Thread(target=self._process, args=(filename, ssid, bssid))
        t.daemon = True
        t.start()

    # ---------------------------------------------------------------
    # pipeline
    # ---------------------------------------------------------------

    def _process(self, pcap_path, ssid, bssid):
        with self.lock:
            self._set_status("validating")
            self._log(f"New handshake for whitelisted SSID '{ssid}' ({bssid}): {pcap_path}")

            if not os.path.exists(pcap_path):
                self._log(f"ERROR: {pcap_path} does not exist, skipping")
                self._set_status("no file")
                return

            hc22000_path = os.path.join(
                self.export_dir,
                f"{self._safe_name(ssid)}_{int(time.time())}.hc22000"
            )

            ok = self._convert(pcap_path, hc22000_path)
            if not ok:
                self._set_status("no handshake")
                self._log(f"'{ssid}': no crackable handshake/PMKID found in {pcap_path}")
                self._notify(f"ClaudeCrackAuto: '{ssid}' capture had no crackable "
                             f"handshake/PMKID.")
                return

            self._log(f"'{ssid}': converted to {hc22000_path}")

            if not self.run_local:
                self._set_status("exported")
                self._log(f"'{ssid}': run_local=false, exported for offline cracking: "
                          f"{hc22000_path}")
                self._notify(f"ClaudeCrackAuto: '{ssid}' handshake validated and "
                             f"exported for offline cracking: {hc22000_path}")
                return

            if not self._tool_exists('hashcat'):
                self._set_status("no hashcat")
                self._log(f"'{ssid}': run_local=true but hashcat missing, left as export only")
                self._notify(f"ClaudeCrackAuto: '{ssid}' exported, but hashcat is not "
                             f"installed so local cracking was skipped.")
                return

            if not os.path.exists(self.wordlist):
                self._set_status("no wordlist")
                self._log(f"'{ssid}': wordlist not found at {self.wordlist}, "
                          f"left as export only")
                self._notify(f"ClaudeCrackAuto: '{ssid}' exported, but the configured "
                             f"wordlist ({self.wordlist}) was not found.")
                return

            self._set_status("cracking")
            self._log(f"'{ssid}': starting local hashcat run (timeout={self.hashcat_timeout}s)")
            result = self._run_hashcat(hc22000_path)

            if result:
                self._set_status("cracked!")
                self._log(f"'{ssid}': CRACKED -> {result}")
                self._notify(f"ClaudeCrackAuto: '{ssid}' password found: {result}")
            else:
                self._set_status("not found")
                self._log(f"'{ssid}': not found in wordlist ({self.wordlist})")
                self._notify(f"ClaudeCrackAuto: '{ssid}' handshake did not match "
                             f"the configured wordlist.")

    # ---------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------

    def _convert(self, pcap_path, hc22000_path):
        """Run hcxpcapngtool to validate + convert. Returns True if a
        crackable hash was produced."""
        try:
            proc = subprocess.run(
                ['hcxpcapngtool', '-o', hc22000_path, pcap_path],
                capture_output=True, text=True, timeout=120
            )
            logging.debug("[ClaudeCrackAuto] hcxpcapngtool stdout: %s", proc.stdout)
            if proc.returncode != 0:
                logging.warning("[ClaudeCrackAuto] hcxpcapngtool exit %s: %s",
                                proc.returncode, proc.stderr)
            return os.path.exists(hc22000_path) and os.path.getsize(hc22000_path) > 0
        except subprocess.TimeoutExpired:
            logging.error("[ClaudeCrackAuto] hcxpcapngtool timed out on %s", pcap_path)
            return False
        except FileNotFoundError:
            logging.error("[ClaudeCrackAuto] hcxpcapngtool not installed")
            return False

    def _run_hashcat(self, hc22000_path):
        """Run hashcat -m 22000 against the configured wordlist.
        Returns the cracked password string, or None if not found."""
        try:
            subprocess.run(
                ['hashcat', '-m', '22000', hc22000_path, self.wordlist,
                 '--quiet', '--potfile-disable',
                 '-o', hc22000_path + '.cracked', '--outfile-format', '2'],
                capture_output=True, text=True, timeout=self.hashcat_timeout
            )
            cracked_file = hc22000_path + '.cracked'
            if os.path.exists(cracked_file) and os.path.getsize(cracked_file) > 0:
                with open(cracked_file, 'r') as f:
                    line = f.readline().strip()
                    return line if line else None
            return None
        except subprocess.TimeoutExpired:
            logging.warning("[ClaudeCrackAuto] hashcat timed out after %ss",
                            self.hashcat_timeout)
            return None
        except FileNotFoundError:
            logging.error("[ClaudeCrackAuto] hashcat not installed")
            return None

    def _notify(self, message):
        if not self.notify_enabled:
            return
        try:
            import requests
            if self.notify_method == 'ntfy' and self.ntfy_url:
                requests.post(self.ntfy_url, data=message.encode('utf-8'), timeout=10)
            elif self.notify_method == 'discord' and self.discord_webhook:
                requests.post(self.discord_webhook, json={'content': message}, timeout=10)
        except Exception as e:
            logging.warning("[ClaudeCrackAuto] notification failed: %s", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[ClaudeCrackAuto] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[ClaudeCrackAuto] could not write log file: %s", e)

    def _set_status(self, status):
        self.last_result = status

    @staticmethod
    def _safe_name(name):
        return "".join(c if c.isalnum() else "_" for c in name)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
