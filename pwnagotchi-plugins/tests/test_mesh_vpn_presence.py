import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mesh_vpn_presence", ROOT / "mesh_vpn_presence.py")
mv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mv)


def test_parse_first_ipv4():
    assert mv.parse_first_ipv4("100.101.5.6\n") == "100.101.5.6"
    assert mv.parse_first_ipv4("no ip here") is None


def test_parse_wg_addr():
    out = ("5: wg0: <POINTOPOINT> mtu 1420\n"
           "    inet 10.9.0.2/24 scope global wg0\n")
    assert mv.parse_wg_addr(out) == "10.9.0.2"
    assert mv.parse_wg_addr("no inet line") is None


def _make(load_plugin, backend):
    p = load_plugin("mesh_vpn_presence.py", options={"backend": backend})
    # bypass on_loaded backend resolution (which depends on installed binaries)
    p.options = {"backend": backend, "wg_interface": "wg0", "auto_up": False}
    p._configured = backend
    p._iface = "wg0"
    p._auto_up = False
    p._backend = backend
    p._address = None
    p._connected = False
    return p


def test_status_tailscale_connected(load_plugin):
    p = _make(load_plugin, "tailscale")
    runner = lambda cmd: "100.101.5.6\n" if cmd == ["tailscale", "ip", "-4"] else ""
    st = p.status(runner=runner)
    assert st == {"connected": True, "address": "100.101.5.6", "backend": "tailscale"}


def test_status_tailscale_down(load_plugin):
    p = _make(load_plugin, "tailscale")
    def runner(cmd):
        raise RuntimeError("not up")
    st = p.status(runner=runner)
    assert st["connected"] is False and st["address"] is None


def test_status_wireguard(load_plugin):
    p = _make(load_plugin, "wireguard")

    def runner(cmd):
        if cmd == ["wg", "show", "wg0"]:
            return "interface: wg0\n  public key: xxx\n"
        if cmd == ["ip", "-4", "addr", "show", "wg0"]:
            return "    inet 10.9.0.2/24 scope global wg0\n"
        return ""
    st = p.status(runner=runner)
    assert st["connected"] is True and st["address"] == "10.9.0.2"


def test_ensure_up_builds_command(load_plugin):
    p = _make(load_plugin, "wireguard")
    calls = []
    p.ensure_up(runner=lambda cmd: calls.append(cmd) or "")
    assert calls == [["wg-quick", "up", "wg0"]]


def test_ui(load_plugin, ui):
    p = _make(load_plugin, "tailscale")
    p._connected = True
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("vpn") == "on"
    p._connected = False
    p.on_ui_update(ui)
    assert ui.get("vpn") == "off"
    p.on_unload(ui)
    assert not ui.has_element("vpn")


def test_ui_na_without_backend(load_plugin, ui):
    p = _make(load_plugin, "tailscale")
    p._backend = None
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("vpn") == "n/a"
