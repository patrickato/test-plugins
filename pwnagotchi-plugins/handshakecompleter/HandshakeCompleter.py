import os
import json
import time
import logging
import subprocess
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class HandshakeCompleter(plugins.Plugin):
    """
    HandshakeCompleter - pwnagotchi plugin ("assembly line" targeting helper)

    You give it a list of your own SSIDs under `targets` - APs you have
    deliberately left OFF pwnagotchi's built-in main.whitelist so it keeps
    attacking them as part of your testing. This plugin then:

      1. Watches every handshake pwnagotchi captures for those targets.
      2. Classifies the capture with hcxpcapngtool: full 4-way handshake,
         PMKID only, or incomplete/partial.
      3. If it's incomplete, does nothing - pwnagotchi's own normal loop
         will naturally keep coming back to it next epoch, since it's not
         in main.whitelist.
      4. Once a target reaches a full 4-way handshake (or a valid PMKID,
         if you allow that as "done"), the plugin adds that SSID to
         pwnagotchi's REAL main.whitelist - both live in the running
         agent's config where possible, and persisted to
         /etc/pwnagotchi/config.toml so it survives a restart. That is
         pwnagotchi's own built-in "don't attack this" mechanism, so once
         a target is whitelisted this way, pwnagotchi stops deauthing /
         associating with it and naturally moves its attention to the
         next thing still in your `targets` list - the "assembly line"
         behavior you described.
      5. Tracks progress (done / still working) in a small state file and
         shows an "N/M done" counter on the pwnagotchi display.

    This plugin only ever adds entries to your whitelist - it never
    removes anything you already had there, and it never touches an SSID
    that isn't explicitly listed in your own `targets` config. Anything
    pwnagotchi captures that isn't in `targets` is left completely alone
    by this plugin.

    NOTE ON INTERNALS: pwnagotchi versions vary in exactly how the running
    agent's config object is structured internally. This plugin tries a
    couple of common attribute paths to update the live in-memory
    whitelist so the change takes effect immediately, but the reliable
    part - and the one that always works - is the config.toml edit, which
    takes effect on the next restart if the live update path doesn't
    match your version. Check the log after a completion event to see
    which path was used.

    Required tool: hcxpcapngtool (package: hcxtools)
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Assembly-line targeting helper: classifies captures for your '
        'listed target SSIDs as full 4-way / PMKID / incomplete, and '
        'once a target is fully captured, adds it to pwnagotchi\'s real '
        'whitelist so pwnagotchi stops attacking it and moves on to the '
        'next target still in progress.'
    )

    STATE_FILE_DEFAULT = '/home/pi/handshakecompleter/state.json'
    LOG_FILE_DEFAULT = '/home/pi/handshakecompleter/results.log'
    CONFIG_PATH = '/etc/pwnagotchi/config.toml'

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.state = {}   # ssid_lower -> {"status": ..., "bssid": ..., "completed_at": ...}
        self.processed_files = set()
        self.last_status = "idle"

    # ---------------------------------------------------------------
    # lifecycle
    # ---------------------------------------------------------------

    def on_loaded(self):
        cfg = self.options

        self.targets = [s.strip().lower() for s in cfg.get('targets', [])]
        self.accept_pmkid = bool(cfg.get('accept_pmkid_as_complete', False))
        self.state_file = cfg.get('state_file', self.STATE_FILE_DEFAULT)
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)
        self.notify_enabled = bool(cfg.get('notify_enabled', False))
        self.notify_method = cfg.get('notify_method', 'ntfy')
        self.ntfy_url = cfg.get('ntfy_url', '')
        self.discord_webhook = cfg.get('discord_webhook', '')

        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self._load_state()

        if not self.targets:
            logging.warning(
                "[HandshakeCompleter] No SSIDs in `targets` - plugin loaded "
                "but has nothing to track until you add your own APs to "
                "main.plugins.HandshakeCompleter.targets"
            )

        if not self._tool_exists('hcxpcapngtool'):
            logging.error(
                "[HandshakeCompleter] hcxpcapngtool not found on PATH. "
                "Install hcxtools (sudo apt install hcxtools) - this "
                "plugin cannot classify handshakes without it."
            )

        # make sure every target has a state entry
        for ssid in self.targets:
            if ssid not in self.state:
                self.state[ssid] = {"status": "in_progress", "bssid": None,
                                     "completed_at": None}
        self._save_state()

        self.ready = True
        done = sum(1 for s in self.state.values() if s["status"] == "complete")
        logging.info(
            "[HandshakeCompleter] plugin loaded, targets=%s, %d/%d already complete",
            self.targets, done, len(self.targets)
        )

    def on_ui_setup(self, ui):
        components = __import__('pwnagotchi.ui.components', fromlist=['LabeledValue'])
        fonts = __import__('pwnagotchi.ui.fonts', fromlist=['Small', 'Bold'])
        ui.add_element('handshakecompleter', components.LabeledValue(
            color=fonts.Small,
            label='HSC',
            value='0/0',
            position=(ui.width() / 2 + 60, 0),
            label_font=fonts.Bold,
            text_font=fonts.Small,
        ))

    def on_ui_update(self, ui):
        done = sum(1 for s in self.state.values() if s.get("status") == "complete")
        total = len(self.targets) if self.targets else 0
        ui.set('handshakecompleter', f"{done}/{total}")

    def on_unload(self, ui):
        with ui._lock:
            try:
                ui.remove_element('handshakecompleter')
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
        ssid_key = ssid.lower()

        if not ssid or ssid_key not in self.targets:
            return  # not one of your declared targets - leave it alone entirely

        if self.state.get(ssid_key, {}).get("status") == "complete":
            return  # already done, nothing to do

        if filename in self.processed_files:
            return
        self.processed_files.add(filename)

        t = threading.Thread(target=self._process, args=(agent, filename, ssid, bssid))
        t.daemon = True
        t.start()

    # ---------------------------------------------------------------
    # pipeline
    # ---------------------------------------------------------------

    def _process(self, agent, pcap_path, ssid, bssid):
        with self.lock:
            ssid_key = ssid.lower()
            self.last_status = f"checking {ssid}"
            self._log(f"Checking capture for target '{ssid}' ({bssid}): {pcap_path}")

            if not os.path.exists(pcap_path):
                self._log(f"ERROR: {pcap_path} does not exist, skipping")
                return

            classification = self._classify(pcap_path)
            self._log(f"'{ssid}': classified as {classification}")

            is_done = (classification == "full_handshake") or \
                      (classification == "pmkid" and self.accept_pmkid)

            if not is_done:
                self.state[ssid_key] = {
                    "status": "in_progress",
                    "bssid": bssid,
                    "last_check": datetime.now().isoformat(timespec='seconds'),
                    "last_classification": classification,
                    "completed_at": None,
                }
                self._save_state()
                self.last_status = f"{ssid}: still working"
                return  # incomplete - pwnagotchi's normal loop keeps retrying on its own

            # complete - stop targeting it
            self.state[ssid_key] = {
                "status": "complete",
                "bssid": bssid,
                "last_check": datetime.now().isoformat(timespec='seconds'),
                "last_classification": classification,
                "completed_at": datetime.now().isoformat(timespec='seconds'),
            }
            self._save_state()

            whitelisted_live = self._whitelist_live(agent, ssid)
            whitelisted_persist = self._whitelist_persist(ssid)

            self._log(
                f"'{ssid}': COMPLETE ({classification}). "
                f"Added to whitelist - live update: {whitelisted_live}, "
                f"config.toml persisted: {whitelisted_persist}"
            )

            done = sum(1 for s in self.state.values() if s["status"] == "complete")
            total = len(self.targets)
            self.last_status = f"{ssid} done ({done}/{total})"

            self._notify(
                f"HandshakeCompleter: '{ssid}' fully captured ({classification}) "
                f"and removed from targeting. Progress: {done}/{total}."
            )

            if done == total and total > 0:
                self._log("All targets complete!")
                self._notify("HandshakeCompleter: all targets complete!")

    # ---------------------------------------------------------------
    # classification
    # ---------------------------------------------------------------

    def _classify(self, pcap_path):
        """Returns 'full_handshake', 'pmkid', or 'incomplete'."""
        try:
            proc = subprocess.run(
                ['hcxpcapngtool', '-o', '/tmp/hsc_check.hc22000', pcap_path],
                capture_output=True, text=True, timeout=120
            )
            output = (proc.stdout or '') + (proc.stderr or '')
            logging.debug("[HandshakeCompleter] hcxpcapngtool output: %s", output)

            # hcxpcapngtool reports counts of EAPOL pairs / PMKIDs found.
            # These substrings are stable across recent hcxtools releases,
            # but if your version's wording differs, check the debug log
            # above and adjust this parsing.
            full_hs = self._extract_count(output, "EAPOL PAIR")
            pmkid = self._extract_count(output, "PMKID")

            if full_hs and full_hs > 0:
                return "full_handshake"
            if pmkid and pmkid > 0:
                return "pmkid"
            return "incomplete"
        except subprocess.TimeoutExpired:
            logging.error("[HandshakeCompleter] hcxpcapngtool timed out on %s", pcap_path)
            return "incomplete"
        except FileNotFoundError:
            logging.error("[HandshakeCompleter] hcxpcapngtool not installed")
            return "incomplete"

    @staticmethod
    def _extract_count(output, label):
        for line in output.splitlines():
            if label.lower() in line.lower():
                digits = ''.join(ch for ch in line if ch.isdigit())
                if digits:
                    return int(digits)
        return None

    # ---------------------------------------------------------------
    # whitelist updates
    # ---------------------------------------------------------------

    def _whitelist_live(self, agent, ssid):
        """Best-effort: try to update the running agent's in-memory
        whitelist so the change takes effect without a restart. Different
        pwnagotchi versions expose the config differently, so this tries
        a couple of known attribute paths and gives up quietly if none
        match - the config.toml persist step below always works."""
        try:
            cfg = getattr(agent, '_config', None) or getattr(agent, 'config', None)
            if cfg and 'main' in cfg and 'whitelist' in cfg['main']:
                if ssid not in cfg['main']['whitelist']:
                    cfg['main']['whitelist'].append(ssid)
                    return True
        except Exception as e:
            logging.debug("[HandshakeCompleter] live whitelist update failed: %s", e)
        return False

    def _whitelist_persist(self, ssid):
        """Adds the SSID to main.whitelist in config.toml on disk so it
        survives a restart, whether or not the live update above worked."""
        try:
            import toml
        except ImportError:
            logging.error(
                "[HandshakeCompleter] python 'toml' package not available - "
                "cannot persist whitelist change to config.toml. Add "
                "'%s' to main.whitelist manually.", ssid
            )
            return False

        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = toml.load(f)

            config.setdefault('main', {})
            config['main'].setdefault('whitelist', [])

            if ssid in config['main']['whitelist']:
                return True  # already there

            config['main']['whitelist'].append(ssid)

            tmp_path = self.CONFIG_PATH + '.hsc_tmp'
            with open(tmp_path, 'w') as f:
                toml.dump(config, f)
            os.replace(tmp_path, self.CONFIG_PATH)
            return True
        except Exception as e:
            logging.error("[HandshakeCompleter] could not persist whitelist to "
                          "config.toml: %s. Add '%s' manually.", e, ssid)
            return False

    # ---------------------------------------------------------------
    # state / logging / notify
    # ---------------------------------------------------------------

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
        except Exception as e:
            logging.warning("[HandshakeCompleter] could not load state file: %s", e)
            self.state = {}

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logging.warning("[HandshakeCompleter] could not write state file: %s", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[HandshakeCompleter] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[HandshakeCompleter] could not write log file: %s", e)

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
            logging.warning("[HandshakeCompleter] notification failed: %s", e)

    @staticmethod
    def _tool_exists(name):
        from shutil import which
        return which(name) is not None
