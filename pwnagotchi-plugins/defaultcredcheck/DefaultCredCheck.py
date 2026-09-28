import os
import json
import logging
from datetime import datetime

import pwnagotchi.plugins as plugins


class DefaultCredCheck(plugins.Plugin):
    """
    DefaultCredCheck - pwnagotchi plugin

    Passively identifies a router's likely vendor from its BSSID's OUI
    (the first 3 bytes, which are vendor-assigned) and flags whether
    that vendor is known for shipping default/predictable credentials
    or a default SSID naming convention - a fast, completely passive
    risk check using only publicly broadcast beacon info, no login
    attempts of any kind.

    This does NOT attempt to log into anything, does NOT guess or try
    passwords, and does NOT connect to any admin interface. It only
    reads the OUI already broadcast in every beacon frame and checks it
    against a small built-in reference table, then logs what it found.
    For SSIDs on your own `my_networks` list, it flags the result more
    prominently since that's actionable for you specifically.

    For actual default-credential values to test against your OWN
    router (never anyone else's), see SecLists' Default-Credentials
    directory: https://github.com/danielmiessler/SecLists/tree/master/Passwords/Default-Credentials
    This plugin only tells you WHICH vendor/pattern might apply - it
    doesn't ship or guess actual passwords.

    Note: modern ISP-issued routers (recent Xfinity/Spectrum/etc. gear)
    usually generate a unique per-device key rather than a shared
    default, so this is most useful for older or non-ISP consumer
    routers.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Identifies router vendor from BSSID OUI and flags known '
        'default-credential/SSID-naming risk patterns for that vendor, '
        'purely passive - no login attempts, no password guessing.'
    )

    LOG_FILE_DEFAULT = '/home/pi/defaultcredcheck/results.log'
    STATE_FILE_DEFAULT = '/home/pi/defaultcredcheck/seen.json'

    # A small, curated set of common consumer-router OUI prefixes and
    # what's publicly known about that vendor's default credential /
    # SSID conventions. Not exhaustive - extend as needed. Sourced from
    # publicly known vendor conventions, not any private database.
    OUI_VENDOR_NOTES = {
        '00:14:6c': ('Netgear', 'Older Netgear default password is often admin/password; '
                                  'newer models use a unique key printed on a label.'),
        '00:1f:33': ('Netgear', 'See Netgear note above.'),
        '00:18:4d': ('D-Link', 'Older D-Link default is often admin with blank password.'),
        '00:1c:f0': ('D-Link', 'See D-Link note above.'),
        '00:1d:7e': ('Cisco/Linksys', 'Older Linksys default is admin/admin.'),
        '00:23:69': ('Cisco/Linksys', 'See Linksys note above.'),
        '00:0f:66': ('TP-Link', 'Default SSID often "TP-LINK_XXXXXX"; older units admin/admin.'),
        '50:c7:bf': ('TP-Link', 'See TP-Link note above.'),
        '2c:56:dc': ('ASUS', 'Default SSID often "ASUS_XXXX"; check label for router key.'),
        '1c:b7:2c': ('Ubiquiti', 'Default SSID often "UBNT"; default admin/ubnt on old firmware.'),
    }

    def __init__(self):
        self.ready = False
        self.seen = {}

    def on_loaded(self):
        cfg = self.options
        self.my_networks = [s.strip().lower() for s in cfg.get('my_networks', [])]
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)
        self.state_file = cfg.get('state_file', self.STATE_FILE_DEFAULT)

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self._load_state()

        self.ready = True
        logging.info("[DefaultCredCheck] plugin loaded, tracking %d AP(s) already "
                     "checked, my_networks=%s", len(self.seen), self.my_networks)

    def on_wifi_update(self, agent, access_points):
        if not self.ready:
            return

        for ap in access_points:
            bssid = (ap.get('mac') or '').lower()
            ssid = ap.get('hostname') or ap.get('ssid') or '(hidden)'
            if not bssid or bssid in self.seen:
                continue

            oui = bssid[0:8]  # "xx:xx:xx"
            vendor_info = self.OUI_VENDOR_NOTES.get(oui)

            self.seen[bssid] = {
                "ssid": ssid,
                "oui": oui,
                "vendor": vendor_info[0] if vendor_info else "unknown",
                "checked_at": datetime.now().isoformat(timespec='seconds'),
            }
            self._save_state()

            if not vendor_info:
                continue  # no note for this OUI, nothing to flag

            vendor, note = vendor_info
            is_own = ssid.lower() in self.my_networks
            prefix = "OWN NETWORK - " if is_own else ""

            self._log(f"{prefix}'{ssid}' ({bssid}): vendor={vendor} - {note}")

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.seen = json.load(f)
        except Exception as e:
            logging.warning("[DefaultCredCheck] could not load state file: %s", e)
            self.seen = {}

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.seen, f, indent=2)
        except Exception as e:
            logging.warning("[DefaultCredCheck] could not write state file: %s", e)

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[DefaultCredCheck] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[DefaultCredCheck] could not write log file: %s", e)
