"""mesh_vpn_presence — reach the unit anywhere over your own tailnet / WireGuard.

Remote access today means setting up a VPN by hand outside Pwnagotchi. This brings the VPN
interface up (Tailscale or WireGuard) and reports the assigned address and connection state,
so the companion app can reach the Pi from anywhere with no port-forwarding. It does not set
up keys/auth — that's a one-time manual step; this keeps the link up and visible.

Guarded: if the chosen backend's binary isn't installed, the plugin idles.

Options (main.plugins.mesh_vpn_presence.*):
    enabled      = true
    backend      = "auto"      # "auto", "tailscale", or "wireguard"
    wg_interface = "wg0"       # WireGuard interface name
    auto_up      = true        # bring the interface up on start
    position     = "0,0"

Requires: the `tailscale` CLI **or** `wireguard-tools` (`wg`/`wg-quick`) installed & configured.
"""
import logging
import re
import shutil
import subprocess

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_IPV4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def parse_first_ipv4(text):
    m = _IPV4.search(text or "")
    return m.group(1) if m else None


def parse_wg_addr(text):
    """Pull an IPv4 from `ip -4 addr show` output (the 'inet' line)."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("inet "):
            return parse_first_ipv4(line)
    return None


def _default_runner(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)


class MeshVPNPresence(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Keep a Tailscale/WireGuard link up and report the unit's address."

    def __init__(self):
        self.options = dict()
        self._backend = None
        self._address = None
        self._connected = False

    def on_loaded(self):
        self._configured = self.options.get("backend", "auto")
        self._iface = self.options.get("wg_interface", "wg0")
        self._auto_up = bool(self.options.get("auto_up", True))
        self._backend = self._resolve_backend(self._configured)
        logging.info("[mesh_vpn_presence] loaded (backend=%s)", self._backend)

    @staticmethod
    def _resolve_backend(configured):
        if configured == "tailscale":
            return "tailscale" if shutil.which("tailscale") else None
        if configured == "wireguard":
            return "wireguard" if shutil.which("wg") else None
        # auto
        if shutil.which("tailscale"):
            return "tailscale"
        if shutil.which("wg"):
            return "wireguard"
        return None

    # -- core (runner injected for tests) ----------------------------------------------
    def ensure_up(self, runner=None):
        runner = runner or _default_runner
        try:
            if self._backend == "tailscale":
                runner(["tailscale", "up"])
            elif self._backend == "wireguard":
                runner(["wg-quick", "up", self._iface])
        except Exception as e:
            logging.debug("[mesh_vpn_presence] bring-up failed: %s", e)

    def status(self, runner=None):
        runner = runner or _default_runner
        addr, connected = None, False
        try:
            if self._backend == "tailscale":
                addr = parse_first_ipv4(runner(["tailscale", "ip", "-4"]))
                connected = bool(addr)
            elif self._backend == "wireguard":
                out = runner(["wg", "show", self._iface])
                connected = bool(out.strip())
                if connected:
                    addr = parse_wg_addr(runner(["ip", "-4", "addr", "show", self._iface]))
        except Exception as e:
            logging.debug("[mesh_vpn_presence] status failed: %s", e)
        self._address, self._connected = addr, connected
        return {"connected": connected, "address": addr, "backend": self._backend}

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        if not self._backend:
            logging.warning("[mesh_vpn_presence] no tailscale/wireguard backend found; idling")
            return
        if self._auto_up:
            self.ensure_up()
        self.status()

    def on_epoch(self, agent, epoch, epoch_data):
        if self._backend and epoch % 20 == 0:
            self.status()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("vpn", LabeledValue(color=BLACK, label="vpn:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            if not self._backend:
                ui.set("vpn", "n/a")
            else:
                ui.set("vpn", "on" if self._connected else "off")

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("vpn"):
                ui.remove_element("vpn")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        return (
            "<html><body><h1>Mesh / VPN Presence</h1>"
            "<ul><li>backend: {}</li><li>connected: {}</li><li>address: {}</li></ul>"
            "</body></html>"
        ).format(self._backend, self._connected, self._address or "-")
