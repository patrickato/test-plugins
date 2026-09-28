import os
import re
import logging
import subprocess
from datetime import datetime

import pwnagotchi.plugins as plugins


class RFComplianceGuide(plugins.Plugin):
    """
    RFComplianceGuide - pwnagotchi plugin

    This plugin does NOT unlock extra channels or spoof a looser
    regulatory region to get more range/power - that's the opposite of
    what it's for, and there are already community plugins (fix_region)
    that do that, which is worth knowing is a legal gray area if the
    country you set isn't the one you're actually transmitting in.

    What this does instead: checks that the Pi's ACTUAL WiFi regulatory
    domain (queried live via `iw reg get`) matches the country you tell
    it you're really in (`real_country_code`), logs a clear warning if
    they don't match, and - only if you opt in - corrects the live
    regulatory domain to your real country and writes the resulting
    legal channel list into config.toml's personality.channels, so your
    unit stays inside the actual rules for where it's actually operating.

    Why this matters for a home lab: pwnagotchi images sometimes ship
    with a default/generic regulatory domain that doesn't match your
    country, which can mean operating on channels or at power levels
    your local regulator doesn't actually permit for unlicensed WiFi
    use. This plugin's job is just to catch that mismatch and help you
    fix it toward what's legal for your real location - not to help you
    find a laxer ruleset elsewhere.

    Required tool: `iw` (nearly always preinstalled on pwnagotchi images;
    part of the wireless-tools chain)
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Confirms the Pi\'s WiFi regulatory domain actually matches '
        'your real country, warns on mismatch, and (opt-in) corrects '
        'it plus writes the legal channel list for your region into '
        'config.toml. Verification/correction only - does not unlock '
        'other countries\' looser limits.'
    )

    LOG_FILE_DEFAULT = '/home/pi/rfcomplianceguide/results.log'
    CONFIG_PATH = '/etc/pwnagotchi/config.toml'

    # Public, well-known 2.4GHz non-DFS channel allowances per regulator.
    # This is standard published spectrum-allocation info, the same kind
    # any WiFi hardware datasheet or OS driver ships with - not anything
    # sensitive. 5GHz is intentionally left out here because most of it
    # is DFS-restricted and region tables are considerably more complex;
    # this plugin sticks to the simple, well-established 2.4GHz case.
    REGION_CHANNELS_24GHZ = {
        'US': list(range(1, 12)),    # FCC: 1-11
        'CA': list(range(1, 12)),    # ISED: 1-11 (same as FCC)
        'GB': list(range(1, 14)),    # Ofcom/ETSI: 1-13
        'DE': list(range(1, 14)),    # ETSI: 1-13
        'FR': list(range(1, 14)),    # ETSI: 1-13
        'EU': list(range(1, 14)),    # generic ETSI: 1-13
        'JP': list(range(1, 14)),    # ARIB: 1-13 (14 is DSSS-only, excluded)
        'AU': list(range(1, 14)),    # ACMA: 1-13
    }

    def __init__(self):
        self.ready = False
        self.last_status = "idle"

    # ---------------------------------------------------------------
    # lifecycle
    # ---------------------------------------------------------------

    def on_loaded(self):
        cfg = self.options

        self.real_country_code = (cfg.get('real_country_code', '') or '').strip().upper()
        self.auto_correct = bool(cfg.get('auto_correct', False))
        self.write_channels_to_config = bool(cfg.get('write_channels_to_config', False))
        self.log_file = cfg.get('log_file', self.LOG_FILE_DEFAULT)

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        if not self.real_country_code:
            logging.warning(
                "[RFComplianceGuide] real_country_code is not set - plugin "
                "loaded but can't check anything until you set it to the "
                "two-letter code for where this Pi actually is (e.g. \"US\")"
            )
            self.ready = True
            return

        if self.real_country_code not in self.REGION_CHANNELS_24GHZ:
            logging.warning(
                "[RFComplianceGuide] real_country_code '%s' isn't in this "
                "plugin's small reference table - it will still check for "
                "a mismatch, but can't offer a channel list correction for "
                "an unlisted region. Feel free to extend REGION_CHANNELS_24GHZ.",
                self.real_country_code
            )

        self.ready = True
        self._check_region()

    def on_ui_setup(self, ui):
        components = __import__('pwnagotchi.ui.components', fromlist=['LabeledValue'])
        fonts = __import__('pwnagotchi.ui.fonts', fromlist=['Small', 'Bold'])
        ui.add_element('rfcompliance', components.LabeledValue(
            color=fonts.Small,
            label='RF',
            value='?',
            position=(ui.width() / 2 + 130, 0),
            label_font=fonts.Bold,
            text_font=fonts.Small,
        ))

    def on_ui_update(self, ui):
        ui.set('rfcompliance', self.last_status[:6])

    def on_unload(self, ui):
        with ui._lock:
            try:
                ui.remove_element('rfcompliance')
            except Exception:
                pass

    # ---------------------------------------------------------------
    # core check - runs once at load; not a repeating/active-scanning hook
    # ---------------------------------------------------------------

    def _check_region(self):
        current = self._get_current_region()

        if current is None:
            self._log("Could not read current regulatory domain via 'iw reg get' - "
                      "check that 'iw' is installed.")
            self.last_status = "no iw"
            return

        self._log(f"Current regulatory domain: {current}, configured real "
                  f"location: {self.real_country_code}")

        if current == self.real_country_code:
            self._log("Regulatory domain matches your configured real location - OK.")
            self.last_status = "OK"
            return

        self._log(
            f"MISMATCH: Pi is set to regulatory domain '{current}' but you "
            f"told this plugin you're actually in '{self.real_country_code}'. "
            f"This can mean operating on channels or power levels not "
            f"actually permitted where this unit is running."
        )
        self.last_status = "mismatch"

        if not self.auto_correct:
            self._log("auto_correct is false - not changing anything. Set it "
                      "true to have this plugin correct the regulatory domain "
                      "to your real location automatically.")
            return

        corrected = self._set_region(self.real_country_code)
        self._log(f"auto_correct=true: attempted to set regulatory domain to "
                  f"'{self.real_country_code}', success: {corrected}")

        if corrected and self.write_channels_to_config:
            channels = self.REGION_CHANNELS_24GHZ.get(self.real_country_code)
            if channels:
                persisted = self._write_channels_to_config(channels)
                self._log(f"Wrote personality.channels = {channels} to "
                          f"config.toml for '{self.real_country_code}': {persisted}")
            else:
                self._log(f"No channel table for '{self.real_country_code}' - "
                          f"skipped writing personality.channels")

    # ---------------------------------------------------------------
    # system interaction
    # ---------------------------------------------------------------

    @staticmethod
    def _get_current_region():
        try:
            proc = subprocess.run(['iw', 'reg', 'get'], capture_output=True,
                                  text=True, timeout=10)
            match = re.search(r'^country\s+([A-Z]{2}):', proc.stdout, re.MULTILINE)
            if match:
                return match.group(1)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logging.error("[RFComplianceGuide] 'iw reg get' failed: %s", e)
        return None

    @staticmethod
    def _set_region(country_code):
        try:
            proc = subprocess.run(['sudo', 'iw', 'reg', 'set', country_code],
                                  capture_output=True, text=True, timeout=10)
            return proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logging.error("[RFComplianceGuide] 'iw reg set' failed: %s", e)
            return False

    def _write_channels_to_config(self, channels):
        try:
            import toml
        except ImportError:
            logging.error(
                "[RFComplianceGuide] python 'toml' package not available - "
                "cannot persist channel list. Set personality.channels = %s "
                "manually.", channels
            )
            return False

        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = toml.load(f)

            config.setdefault('personality', {})
            config['personality']['channels'] = channels

            tmp_path = self.CONFIG_PATH + '.rfc_tmp'
            with open(tmp_path, 'w') as f:
                toml.dump(config, f)
            os.replace(tmp_path, self.CONFIG_PATH)
            return True
        except Exception as e:
            logging.error("[RFComplianceGuide] could not persist channels to "
                          "config.toml: %s. Set personality.channels = %s "
                          "manually.", e, channels)
            return False

    def _log(self, message):
        line = f"{datetime.now().isoformat(timespec='seconds')} - {message}"
        logging.info("[RFComplianceGuide] %s", message)
        try:
            with open(self.log_file, 'a') as f:
                f.write(line + "\n")
        except Exception as e:
            logging.warning("[RFComplianceGuide] could not write log file: %s", e)
