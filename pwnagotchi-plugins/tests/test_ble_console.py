import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ble_console", ROOT / "ble_console.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def test_format_uptime():
    assert bc.format_uptime(0) == "0h00m00s"
    assert bc.format_uptime(3661) == "1h01m01s"


def _make(load_plugin, **opts):
    p = load_plugin("ble_console.py", options=opts)
    p.on_loaded()
    return p


def test_help_lists_allowed(load_plugin):
    p = _make(load_plugin, allowed=["help", "status"])
    out = p.process("help")
    assert "help" in out and "status" in out


def test_status_uses_fakes(load_plugin):
    p = _make(load_plugin)
    # fake pwnagotchi: temp 48, cpu 0.17, mem 0.42
    assert p.process("status") == "temp=48C cpu=17% mem=42%"


def test_handshakes_command(load_plugin, agent):
    p = _make(load_plugin)
    p.on_handshake(agent, "f", {}, {})
    assert p.process("handshakes") == "handshakes=1"


def test_disallowed_command_rejected(load_plugin):
    p = _make(load_plugin, allowed=["status"])
    assert p.process("reboot").startswith("err:")
    assert p.process("uptime").startswith("err:")   # not in allow-list


def test_unknown_but_allowed_command(load_plugin):
    # allow-listed name with no handler -> graceful error, not a crash
    p = _make(load_plugin, allowed=["frobnicate"])
    assert p.process("frobnicate").startswith("err:")


def test_empty_line(load_plugin):
    p = _make(load_plugin)
    assert p.process("") == ""
    assert p.process("   ") == ""


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("ble") == "off"      # no BLE backend in test env
    p._ble_ok = True
    p.on_ui_update(ui)
    assert ui.get("ble") == "on"
    p.on_unload(ui)
    assert not ui.has_element("ble")
