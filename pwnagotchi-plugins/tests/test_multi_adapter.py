import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("multi_adapter", ROOT / "multi_adapter.py")
ma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ma)

IW_DEV = """phy#1
	Interface wlan1
		ifindex 4
		type monitor
phy#0
	Interface wlan0
		ifindex 3
		type managed
"""

IP_ADDR = ("2: eth0    inet 192.168.1.5/24 brd 192.168.1.255 scope global eth0\n"
           "3: wlan0    inet 10.0.0.9/24 brd 10.0.0.255 scope global wlan0\n")


def test_parse_iw_dev():
    ifs = ma.parse_iw_dev(IW_DEV)
    by = {i["iface"]: i["type"] for i in ifs}
    assert by == {"wlan1": "monitor", "wlan0": "managed"}


def test_parse_ip_ifaces():
    assert ma.parse_ip_ifaces(IP_ADDR) == {"eth0", "wlan0"}


def test_classify_roles_auto():
    interfaces = [{"iface": "wlan1", "type": "monitor"}, {"iface": "wlan0", "type": "managed"}]
    roles, conflicts = ma.classify_roles(interfaces, {"wlan0"})
    assert roles == {"wlan1": "monitor", "wlan0": "uplink"}
    assert conflicts == []


def test_classify_conflict_two_monitors():
    interfaces = [{"iface": "wlan1", "type": "monitor"}, {"iface": "wlan2", "type": "monitor"}]
    roles, conflicts = ma.classify_roles(interfaces, set())
    assert roles == {"wlan1": "monitor", "wlan2": "monitor"}
    assert "multiple monitor interfaces" in conflicts
    assert "no uplink interface with an IP" in conflicts


def test_classify_overrides():
    interfaces = [{"iface": "wlan0", "type": "managed"}, {"iface": "wlan1", "type": "managed"}]
    roles, _ = ma.classify_roles(interfaces, set(),
                                 monitor_iface="wlan1", uplink_iface="wlan0")
    assert roles == {"wlan0": "uplink", "wlan1": "monitor"}


def _make(load_plugin, **opts):
    p = load_plugin("multi_adapter.py", options=opts)
    p.on_loaded()
    return p


def test_refresh_with_injected_runner(load_plugin):
    p = _make(load_plugin)
    def runner(cmd):
        return IW_DEV if cmd[:2] == ["iw", "dev"] else IP_ADDR
    roles, conflicts = p.refresh(runner=runner)
    assert roles == {"wlan1": "monitor", "wlan0": "uplink"}
    assert conflicts == []


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p._roles = {"wlan0": "uplink", "wlan1": "monitor"}
    p._conflicts = []
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("adapters") == "2"
    p._conflicts = ["multiple monitor interfaces"]
    p.on_ui_update(ui)
    assert ui.get("adapters") == "2!"
    p.on_unload(ui)
    assert not ui.has_element("adapters")
