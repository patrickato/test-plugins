import os
import time
import logging
import threading

import pwnagotchi.plugins as plugins


class FailedCaptureCleanup(plugins.Plugin):
    """
    FailedCaptureCleanup - pwnagotchi plugin

    Detects when an attack attempt produced an empty or junk .pcap
    (a silent failure - deauth/association fired but nothing usable
    landed on disk) and cleans it up immediately, instead of letting
    dead files pile up per AP in the handshakes directory.

    "Junk" is judged two ways:
      1. Zero-byte (or near-zero, below `min_valid_bytes`) files - an
         instant, cheap check that catches the most common case with
         no external tools.
      2. Optionally, files that ARE non-trivial in size but contain no
         parseable handshake/PMKID material at all, checked via
         hcxpcapngtool (same tool used elsewhere in this repo for
         capture validation) if `deep_check` is enabled. This catches
         pcaps that recorded some traffic but never a useful frame.

    Consistent with this repo's existing caution around destructive
    operations (HandshakeMerge never overwrites or deletes anything),
    this plugin defaults to QUARANTINING junk files into a subfolder
    rather than permanently deleting them. Hard-delete is available
    as an explicit opt-in for anyone who's confirmed the quarantine
    behavior does what they want first.

    Runs on a periodic background sweep of the handshakes directory
    rather than only reacting to on_handshake, since a truly silent
    failure (nothing captured at all) never fires that hook - the
    junk file just sits there from whatever wrote it.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Finds empty/junk .pcap files left behind by failed capture '
        'attempts and quarantines (or optionally deletes) them, so '
        'dead files don\'t pile up per AP.'
    )

    HANDSHAKES_DIR_DEFAULT = '/home/pi/handshakes'

    def __init__(self):
        self.ready = False
        self.stop_event = threading.Event()
        self.stats = {'checked': 0, 'quarantined': 0, 'deleted': 0}

    def on_loaded(self):
        cfg = self.options

        self.handshakes_dir = cfg.get('handshakes_dir', self.HANDSHAKES_DIR_DEFAULT)
        self.quarantine_dir = cfg.get(
            'quarantine_dir',
            os.path.join(self.handshakes_dir, 'failedcapturecleanup_quarantine')
        )
        self.min_valid_bytes = int(cfg.get('min_valid_bytes', 200))
        self.deep_check = bool(cfg.get('deep_check', False))
        self.hard_delete = bool(cfg.get('hard_delete', False))
        self.sweep_interval_secs = int(cfg.get('sweep_interval_secs', 120))
        self.min_file_age_secs = int(cfg.get('min_file_age_secs', 30))

        if self.hard_delete:
            logging.warning(
                "[FailedCaptureCleanup] hard_delete is ENABLED - junk "
                "files will be permanently removed, not quarantined. "
                "Make sure you've reviewed quarantine_dir output first."
            )

        if not self.hard_delete:
            os.makedirs(self.quarantine_dir, exist_ok=True)

        self.ready = True
        logging.info(
            "[FailedCaptureCleanup] plugin loaded, watching %s "
            "(min_valid_bytes=%d, deep_check=%s, hard_delete=%s)",
            self.handshakes_dir, self.min_valid_bytes, self.deep_check,
            self.hard_delete
        )

        threading.Thread(target=self._sweep_loop, daemon=True).start()

    def on_unload(self, ui):
        self.stop_event.set()

    # ---------------------------------------------------------------
    # sweep loop
    # ---------------------------------------------------------------

    def _sweep_loop(self):
        while not self.stop_event.is_set():
            try:
                self._sweep_once()
            except Exception as e:
                logging.warning("[FailedCaptureCleanup] sweep error: %s", e)
            self.stop_event.wait(self.sweep_interval_secs)

    def _sweep_once(self):
        if not os.path.isdir(self.handshakes_dir):
            return

        now = time.time()

        for entry in os.listdir(self.handshakes_dir):
            if not entry.lower().endswith('.pcap'):
                continue

            path = os.path.join(self.handshakes_dir, entry)
            if not os.path.isfile(path):
                continue

            try:
                st = os.stat(path)
            except OSError:
                continue

            # Skip anything still young - it may be mid-write.
            if now - st.st_mtime < self.min_file_age_secs:
                continue

            self.stats['checked'] += 1

            if st.st_size < self.min_valid_bytes:
                self._handle_junk(path, entry, reason=f"{st.st_size} bytes")
                continue

            if self.deep_check and not self._has_useful_material(path):
                self._handle_junk(path, entry, reason="no parseable handshake/PMKID material")

    def _has_useful_material(self, path):
        """
        Best-effort deep check via hcxpcapngtool. Returns True if we
        can't run the check at all (fails open - a broken tool
        shouldn't cause good captures to get quarantined).
        """
        import subprocess
        import tempfile

        hcxtool = self.options.get('hcxpcapngtool_path', 'hcxpcapngtool')

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out_hc22000 = os.path.join(tmpdir, 'out.hc22000')
                result = subprocess.run(
                    [hcxtool, f'-o={out_hc22000}', path],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    logging.debug(
                        "[FailedCaptureCleanup] hcxpcapngtool returned %d on %s, "
                        "leaving file alone", result.returncode, path
                    )
                    return True
                return os.path.exists(out_hc22000) and os.path.getsize(out_hc22000) > 0
        except FileNotFoundError:
            logging.debug(
                "[FailedCaptureCleanup] hcxpcapngtool not found - "
                "deep_check skipped for %s", path
            )
            return True
        except Exception as e:
            logging.debug(
                "[FailedCaptureCleanup] deep check failed for %s: %s - "
                "leaving file alone", path, e
            )
            return True

    def _handle_junk(self, path, entry, reason):
        if self.hard_delete:
            try:
                os.remove(path)
                self.stats['deleted'] += 1
                logging.info(
                    "[FailedCaptureCleanup] deleted junk capture %s (%s)",
                    entry, reason
                )
            except Exception as e:
                logging.warning(
                    "[FailedCaptureCleanup] could not delete %s: %s", path, e
                )
        else:
            dest = os.path.join(self.quarantine_dir, entry)
            try:
                if os.path.exists(dest):
                    stamp = int(time.time())
                    dest = os.path.join(self.quarantine_dir, f"{stamp}_{entry}")
                os.rename(path, dest)
                self.stats['quarantined'] += 1
                logging.info(
                    "[FailedCaptureCleanup] quarantined junk capture %s (%s) -> %s",
                    entry, reason, dest
                )
            except Exception as e:
                logging.warning(
                    "[FailedCaptureCleanup] could not quarantine %s: %s", path, e
                )

    # ---------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------

    def on_ui_setup(self, ui):
        from pwnagotchi.ui.components import LabeledValue
        from pwnagotchi.ui.view import BLACK
        ui.add_element('fcc_stat', LabeledValue(
            color=BLACK, label='JUNK', value='0',
            position=(ui.width() / 2 + 55, 0),
            label_font=ui.fonts()['Bold'], text_font=ui.fonts()['Small']
        ))

    def on_ui_update(self, ui):
        if not self.ready:
            return
        total = self.stats['quarantined'] + self.stats['deleted']
        ui.set('fcc_stat', str(total))

    def on_unload_ui(self, ui):
        try:
            ui.remove_element('fcc_stat')
        except Exception:
            pass
