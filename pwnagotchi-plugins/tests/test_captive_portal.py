import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("captive_portal", ROOT / "captive_portal.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def test_classify_online():
    assert cp.classify_response(204, "", 204) == "online"
    assert cp.classify_response(204, "   ", 204) == "online"


def test_classify_captive():
    assert cp.classify_response(200, "<html>login</html>", 204) == "captive"
    assert cp.classify_response(302, "", 204) == "captive"
    assert cp.classify_response(204, "unexpected body", 204) == "captive"


def test_classify_offline():
    assert cp.classify_response(None, "", 204) == "offline"


def _make(load_plugin, **opts):
    p = load_plugin("captive_portal.py", options=opts)
    p.on_loaded()
    return p


def test_is_online(load_plugin):
    p = _make(load_plugin)
    p._status = "online"
    assert p.is_online() is True
    p._status = "captive"
    assert p.is_online() is False


def test_ui_maps_status(load_plugin, ui):
    p = _make(load_plugin)
    p.on_ui_setup(ui)
    for status, expected in (("online", "on"), ("captive", "cap"), ("offline", "off")):
        p._status = status
        p.on_ui_update(ui)
        assert ui.get("captive") == expected
    p.on_unload(ui)
    assert not ui.has_element("captive")


def test_maybe_probe_throttle(load_plugin):
    p = _make(load_plugin, interval_secs=60)
    calls = []
    p.probe = lambda: calls.append(1)      # stub out the network call
    p._last_check = 0
    p._maybe_probe(now=30)                   # too soon
    assert calls == []
    p._maybe_probe(now=61)                   # past interval
    assert calls == [1]
