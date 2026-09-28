import os
import json
import logging
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class WPA3Watch(plugins.Plugin):
    """
    WPA3Watch - pwnagotchi plugin

    Passively classifies every AP pwnagotchi's radio sees (from the
    beacon/probe-response info bettercap already parses - no extra
    scanning or attack traffic of any kind) into one of:

        wpa3_only   - SAE (WPA3) authentication only, no PSK fallback
        wpa2_wpa3   - "transition mode": supports both WPA2-PSK and
                      WPA3-SAE at once
        wpa2_psk    - classic WPA2-Personal
        enterprise  - WPA/WPA2/WPA3-Enterprise (802.1X/MGT) - not a
                      4-way-handshake target in the PSK-cracking sense
        open        - no encryption
        wep         - WEP (legacy, different attack surface entirely)
        unknown     - couldn't determine from the fields bettercap gave us

    This classification is 100% passive read-of-already-broadcast info -
    it doesn't change what pwnagotchi captures or attacks. Every AP seen
    gets logged with its classification, which is useful recon
    documentation on its own (how much of the WiFi around you has moved
    to WPA3, etc).

    The one active behavior: for SSIDs you list in `my_networks`, if one
    of them classifies as wpa3_only, this plugin will (optionally) add
    it to pwnagotchi's real main.whitelist - both live in the running
    agent where possible and persisted to config.toml - because a pure
    WPA3-SAE network isn't vulnerable to the classic "capture a 4-way
    handshake and crack it offline" approach this project's other
    plugins use (SAE's Dragonfly key exchange doesn't hand you a
    crackable exchange the same way WPA2-PSK does). There's no point
    having pwnagotchi keep deauthing/re-associating with your own AP
    for a capture method that can't work against it - so once flagged,
    it gets whitelisted and pwnagotchi moves its attention elsewhere.

    This whitelist-on-completion behavior ONLY ever applies to SSIDs you
    explicitly list in `my_networks`. Every other AP is logged for your
    own visibility and otherwise left completely untouched - this
    plugin never changes pwnagotchi's behavior toward a network that
    isn't yours.

    NOTE: field names bettercap reports for encryption/cipher/
    authentication have shifted slightly across versions in the past.
    If everything classifies as "unknown", check the debug log (raw AP
    dict is logged at DEBUG level) and adjust `_classify()` to match
    what your version actually reports.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Passively classifies every AP pwnagotchi sees by WPA2/WPA3/'
        'enterprise/open/WEP, logs it for recon documentation, and '
        'optionally whitelists your own WPA3-SAE-only networks since '
        'handshake-capture attacks cannot work against them.'
    )

    LOG_FILE_DEFAULT = '/home/pi/wpa3watch/results.log'
    STATE_FILE_DEFAULT = '/home/pi/wpa3watch/seen_aps.json'
    CONFIG_PATH = '/etc/pwnagotchi/config.toml'

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.seen = {}   # bssid -> {"ssid":..., "classification":..., "first_seen":...}
        self.last_status = "idle"

    # ---------------------------------------------------------------
    # lifecycle
    # ---------------------------------------------------------------

    def on_loaded(self):
        cfg = self.options

        self.my_networks = [s.strip().lower() for s in cfg.get('my_networks', [])]
        self.auto_whitelist_wpa3 = bool(cfg.get('auto_whitelist_wpa3', False))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)
        self.state_file = cfg.get('state_file', self.STATE_FILE_DEFAULT)

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        self._load_state()
        self.ready = True
        logging.info(
            "[WPA3Watch] plugin loaded, tracking %d AP(s) already seen, "
            "my_networks=%s, auto_whitelist_wpa3=%s",
            len(self.seen), self.my_networks, self.auto_whitelist_wpa3
        )

    def on_ui_setup(self, ui):
        components = __import__('pwnagotchi.ui.components', fromlist=['LabeledValue'])
        fonts = __import__('pwnagotchi.ui.fonts', fromlist=['Small', 'Bold'])
        ui.add_element('wpa3watch', components.LabeledValue(
            color=fonts.Small,
            label='W3',
            value='0',
            position=(ui.width() / 2 + 100, 0),
            label_font=fonts.Bold,
            text_font=fonts.Small,
        ))

    def on_ui_update(self, ui):
        wpa3_count = sum(1 for v in self.seen.values()
                        if v.get("classification") in ("wpa3_only", "wpa2_wpa3"))
        ui.set('wpa3watch', str(wpa3_count))

    def on_unload(self, ui):
        with ui._lock:
            try:
                ui.remove_element('wpa3watch')
            except Exception:
                pass

    # ---------------------------------------------------------------
    # main hook - passive, runs on every periodic wifi scan update
    # ---------------------------------------------------------------

    def on_wifi_update(self, agent, access_points):
        if not self.ready:
            return

        for ap in access_points:
            bssid = (ap.get('mac') or '').lower()
            ssid = ap.get('hostname') or ap.get('ssid') or '(hidden)'
            if not bssid:
                continue

            classification = self._classify(ap)

            existing = self.seen.get(bssid)
            if existing and existing.get("classification") == classification:
                continue  # already logged this AP with this classification

            with self.lock:
                self.seen[bssid] = {
                    "ssid": ssid,
                    "classification": classification,
                    "channel": ap.get('channel'),
                    "rssi": ap.get('rssi'),
                    "first_seen": existing["first_seen"] if existing else
                                  datetime.now().isoformat(timespec='seconds'),
                    "last_seen": datetime.now().isoformat(timespec='seconds'),
                }
                self._save_state()

            self._log(f"{ssid} ({bssid}) ch{ap.get('channel')} "
                      f"rssi={ap.get('rssi')} -> {classification}")
            logging.debug("[WPA3Watch] raw AP dict for %s: %s", ssid, ap)

            if classification == "wpa3_only" and ssid.lower() in self.my_networks:
                self._handle_own_wpa3(agent, ssid)

    # ---------------------------------------------------------------
    # classification
    # ---------------------------------------------------------------

    @staticmethod
    def _classify(ap):
        """Best-effort classification from bettercap's parsed AP fields.
        Adjust the field names here if your bettercap version reports
        them differently (check the DEBUG log for the raw dict)."""
        encryption = (ap.get('encryption') or '').upper()
        authentication = (ap.get('authentication') or '').upper()
        cipher = (ap.get('cipher') or '').upper()

        combined = f"{encryption} {authentication} {cipher}"

        if not encryption or encryption in ('', 'NONE', 'OPEN'):
            return "open"
        if 'WEP' in combined:
            return "wep"
        if 'MGT' in combined or 'ENTERPRISE' in combined or '802.1X' in combined:
            return "enterprise"

        has_sae = 'SAE' in combined or 'WPA3' in combined
        has_psk = 'PSK' in combined

        if has_sae and has_psk:
            return "wpa2_wpa3"
        if has_sae and not has_psk:
            return "wpa3_only"
        if has_psk or 'WPA' in combined:
            return "wpa2_psk"

        return "unknown"

    # ---------------------------------------------------------------
    # whitelist handling for user's own WPA3-only networks
    # ---------------------------------------------------------------

    def _handle_own_wpa3(self, agent, ssid):
        if not self.auto_whitelist_wpa3:
            self._log(f"'{ssid}': WPA3-SAE-only, matches my_networks, but "
                      f"auto_whitelist_wpa3=false - not touching whitelist")
            return

        live = self._whitelist_live(agent, ssid)
        persisted = self._whitelist_persist(ssid)
        self._log(
            f"'{ssid}': WPA3-SAE-only own network - handshake capture can't "
            f"work against it, added to whitelist. live update: {live}, "
            f"config.toml persisted: {persisted}"
        )

    def _whitelist_live(self, agent, ssid):
        try:
            cfg = getattr(agent, '_config', None) or getattr(agent, 'config', None)
            if cfg and 'main' in cfg and 'whitelist' in cfg['main']:
                if ssid not in cfg['main']['whitelist']:
                    cfg['main']['whitelist'].append(ssid)
                    return True
        except Exception as e:
            logging.debug("[WPA3Watch] live whitelist update failed: %s", e)
        return False

    def _whitelist_persist(self, ssid):
        try:
            import toml
        except ImportError:
            logging.error(
                "[WPA3Watch] python 'toml' package not available - cannot "
                "persist whitelist change. Add '%s' to main.whitelist "
                "manually.", ssid
            )
            return False

        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = toml.load(f)

            config.setdefault('main', {})
            config['main'].setdefault('whitelist', [])

            if ssid in config['main']['whitelist']:
                return True

            config['main']['whitelist'].append(ssid)

            tmp_path = self.CONFIG_PATH + '.wpa3_tmp'
            with open(tmp_path, 'w') as f:
                toml.dump(config, f)
            os.replace(tmp_path, self.CONFIG_PATH)
            return True
        except Exception as e:
            logging.error("[WPA3Watch] could not persist whitelist to "
                          "config.toml: %s. Add '%s' manually.", e, ssid)
            return False

    # ---------------------------------------------------------------
    # state / logging
    # ---------------------------------------------------------------

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.seen = json.load(f)
        except Exception as e:
            logging.warning("[WPA3Watch] could not load state file: %s", e)
            self.seen = {}

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.seen, f, indent=2)
        except Exception as e:
            logging.warning("[WPA3Watch] could not write state file: %s", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[WPA3Watch] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[WPA3Watch] could not write log file: %s", e)
