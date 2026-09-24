"""ble_console — a no-network status/command console over BLE.

When there's no IP link at all, this exposes a small Nordic-UART-style BLE service so a phone
can query status and run a few **allow-listed, read-only** commands. The command processor is
the tested heart; the BLE peripheral transport (BlueZ via bluezero) is guarded and optional.

Only commands on the allow-list run; everything else is rejected. Nothing here changes system
state by default.

Options (main.plugins.ble_console.*):
    enabled     = true
    device_name = "pwnagotchi"
    allowed     = ["help","status","uptime","ip","handshakes"]
    position    = "0,0"

Requires: BlueZ + pip `bluezero` (or another BLE peripheral stack) and a BLE adapter for the
transport. Without them the command core still works but there's no radio link.
"""
import logging
import socket

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_DEFAULT_ALLOWED = ["help", "status", "uptime", "ip", "handshakes"]


def format_uptime(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return "%dh%02dm%02ds" % (h, m, s)


class BLEConsole(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "No-network BLE status/command console (allow-listed, read-only)."

    def __init__(self):
        self.options = dict()
        self._handshakes = 0
        self._ble_ok = False
        self._peripheral = None

    def on_loaded(self):
        self._device_name = self.options.get("device_name", "pwnagotchi")
        self._allowed = set(self.options.get("allowed", _DEFAULT_ALLOWED))
        logging.info("[ble_console] loaded (allowed=%s)", sorted(self._allowed))

    # -- command core (testable) -------------------------------------------------------
    def process(self, line):
        line = (line or "").strip()
        if not line:
            return ""
        cmd = line.split()[0].lower()
        if cmd not in self._allowed:
            return "err: '%s' not allowed" % cmd
        handler = getattr(self, "_cmd_" + cmd, None)
        if handler is None:
            return "err: unknown command"
        try:
            return handler()
        except Exception as e:
            return "err: %s" % e

    def _cmd_help(self):
        return "commands: " + ", ".join(sorted(self._allowed))

    def _cmd_status(self):
        try:
            return "temp=%.0fC cpu=%.0f%% mem=%.0f%%" % (
                float(pwnagotchi.temperature()),
                float(pwnagotchi.cpu_load()) * 100,
                float(pwnagotchi.mem_usage()) * 100)
        except Exception:
            return "status unavailable"

    def _cmd_uptime(self):
        return format_uptime(pwnagotchi.uptime())

    def _cmd_ip(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "unknown"

    def _cmd_handshakes(self):
        return "handshakes=%d" % self._handshakes

    # -- BLE transport (guarded, not unit-tested) --------------------------------------
    def _start_ble(self):
        try:
            from bluezero import peripheral, adapter  # noqa: F401
        except Exception as e:
            logging.warning("[ble_console] bluezero not available; console core only: %s", e)
            self._ble_ok = False
            return
        try:
            # Minimal Nordic UART Service; RX write -> process(), TX notify with reply.
            nus = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
            rx = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
            tx = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
            dongle = adapter.Adapter()
            self._peripheral = peripheral.Peripheral(dongle.address, local_name=self._device_name)
            self._peripheral.add_service(srv_id=1, uuid=nus, primary=True)
            self._peripheral.add_characteristic(
                srv_id=1, chr_id=1, uuid=tx, value=[], notifying=False,
                flags=["notify"])
            self._peripheral.add_characteristic(
                srv_id=1, chr_id=2, uuid=rx, value=[], notifying=False,
                flags=["write", "write-without-response"],
                write_callback=self._on_ble_write)
            self._ble_ok = True
            import threading
            threading.Thread(target=self._peripheral.publish, daemon=True, name="ble").start()
            logging.info("[ble_console] BLE peripheral advertising as %s", self._device_name)
        except Exception as e:
            logging.warning("[ble_console] BLE setup failed; console core only: %s", e)
            self._ble_ok = False

    def _on_ble_write(self, value, options=None):
        try:
            line = bytes(value).decode("utf-8", "ignore")
            reply = self.process(line)
            logging.debug("[ble_console] '%s' -> '%s'", line.strip(), reply)
            # TX notify wiring is transport-specific; kept minimal here.
        except Exception as e:
            logging.debug("[ble_console] write handling failed: %s", e)

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self._start_ble()

    def on_handshake(self, agent, filename, access_point, client_station):
        self._handshakes += 1

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("ble", LabeledValue(color=BLACK, label="ble:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("ble", "on" if self._ble_ok else "off")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("ble"):
                ui.remove_element("ble")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return ("<html><body><h1>BLE Console</h1>"
                "<p>BLE link: {}</p><p>allowed commands: {}</p></body></html>").format(
                    "up" if self._ble_ok else "down", ", ".join(sorted(self._allowed)))
