"""multi_adapter — see and sanity-check Wi-Fi adapter roles.

Dual-adapter setups are common but role assignment is fragile and invisible. This enumerates
the wireless interfaces, classifies each as monitor / uplink / idle (from mode + whether it
has an IP, with optional explicit overrides), and warns about conflicts — e.g. two monitor
interfaces, or no uplink with an IP. It's observational by default: it reports roles rather
than reconfiguring interfaces out from under Pwnagotchi.

Options (main.plugins.multi_adapter.*):
    enabled       = true
    monitor_iface =            # force a specific interface as the monitor role
    uplink_iface  =            # force a specific interface as the uplink role
    position      = "0,0"

Requires: `iw` and `ip` (iproute2), normally already present on the image. 2+ Wi-Fi adapters
to be useful.
"""
import logging
import subprocess

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def parse_iw_dev(text):
    """Parse `iw dev` output into [{iface, type}]."""
    interfaces = []
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("Interface "):
            current = {"iface": line.split(None, 1)[1], "type": "unknown"}
            interfaces.append(current)
        elif line.startswith("type ") and current is not None:
            current["type"] = line.split(None, 1)[1]
    return interfaces


def parse_ip_ifaces(text):
    """Interfaces that have an IPv4 address, from `ip -4 -o addr show`."""
    ifaces = set()
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            ifaces.add(parts[1])
    return ifaces


def classify_roles(interfaces, ip_ifaces, monitor_iface=None, uplink_iface=None):
    roles = {}
    for i in interfaces:
        iface, t = i["iface"], i.get("type")
        if uplink_iface and iface == uplink_iface:
            roles[iface] = "uplink"
        elif monitor_iface and iface == monitor_iface:
            roles[iface] = "monitor"
        elif t == "monitor":
            roles[iface] = "monitor"
        elif t == "managed" and iface in ip_ifaces:
            roles[iface] = "uplink"
        else:
            roles[iface] = "idle"
    conflicts = []
    if sum(1 for r in roles.values() if r == "monitor") > 1:
        conflicts.append("multiple monitor interfaces")
    if roles and not any(r == "uplink" for r in roles.values()):
        conflicts.append("no uplink interface with an IP")
    return roles, conflicts


class MultiAdapter(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Classify Wi-Fi adapter roles (monitor/uplink) and warn on conflicts."

    def __init__(self):
        self.options = dict()
        self._roles = {}
        self._conflicts = []

    def on_loaded(self):
        self._monitor_iface = self.options.get("monitor_iface") or None
        self._uplink_iface = self.options.get("uplink_iface") or None
        logging.info("[multi_adapter] loaded")

    # -- gathering (guarded) -----------------------------------------------------------
    @staticmethod
    def _run(cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)

    def refresh(self, runner=None):
        runner = runner or self._run
        try:
            interfaces = parse_iw_dev(runner(["iw", "dev"]))
        except Exception as e:
            logging.debug("[multi_adapter] iw dev failed: %s", e)
            return
        try:
            ip_ifaces = parse_ip_ifaces(runner(["ip", "-4", "-o", "addr", "show"]))
        except Exception:
            ip_ifaces = set()
        self._roles, self._conflicts = classify_roles(
            interfaces, ip_ifaces, self._monitor_iface, self._uplink_iface)
        if self._conflicts:
            logging.warning("[multi_adapter] conflicts: %s", "; ".join(self._conflicts))
        return self._roles, self._conflicts

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.refresh()

    def on_epoch(self, agent, epoch, epoch_data):
        if epoch % 20 == 0:
            self.refresh()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("adapters", LabeledValue(color=BLACK, label="if:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("adapters", "%d%s" % (len(self._roles), "!" if self._conflicts else ""))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("adapters"):
                ui.remove_element("adapters")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        rows = "".join("<tr><td>{}</td><td>{}</td></tr>".format(i, r)
                       for i, r in self._roles.items()) or "<tr><td colspan=2>none</td></tr>"
        warn = ("<p style='color:red'>%s</p>" % "; ".join(self._conflicts)) if self._conflicts else ""
        return ("<html><body><h1>Wi-Fi Adapters</h1>{}"
                "<table border=1><tr><th>iface</th><th>role</th></tr>{}"
                "</table></body></html>").format(warn, rows)
