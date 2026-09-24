import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rtl433_ambient", ROOT / "rtl433_ambient.py")
rtl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rtl)


def test_device_key():
    assert rtl.device_key({"model": "Acurite-Tower", "id": 1234}) == "Acurite-Tower/1234"
    assert rtl.device_key({"model": "Nexus-TH", "channel": 2}) == "Nexus-TH/2"
    assert rtl.device_key({"model": "Foo"}) == "Foo"
    assert rtl.device_key({"id": 5}) is None       # no model
    assert rtl.device_key("nope") is None


def test_extract_readings():
    ev = {"model": "X", "id": 1, "temperature_C": 21.5, "humidity": 55, "junk": "ignore"}
    r = rtl.extract_readings(ev)
    assert r == {"temperature_C": 21.5, "humidity": 55}


def _make(load_plugin, **opts):
    p = load_plugin("rtl433_ambient.py", options=opts)
    p.on_loaded()
    return p


def test_update_aggregates(load_plugin):
    p = _make(load_plugin)
    p.update({"model": "Acurite", "id": 1, "temperature_C": 20}, now=100)
    p.update({"model": "Acurite", "id": 1, "temperature_C": 21}, now=200)
    p.update({"model": "Nexus", "id": 2, "humidity": 60}, now=150)
    assert p.summary() == {"devices": 2, "events": 3}
    d = p._devices["Acurite/1"]
    assert d["count"] == 2 and d["last"]["temperature_C"] == 21 and d["last_seen"] == 200


def test_update_respects_max_devices(load_plugin):
    p = _make(load_plugin, max_devices=1)
    p.update({"model": "A", "id": 1})
    p.update({"model": "B", "id": 2})     # over cap -> ignored
    assert len(p._devices) == 1


def test_update_ignores_keyless(load_plugin):
    p = _make(load_plugin)
    assert p.update({"temperature_C": 20}) is None
    assert p.summary()["events"] == 0


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p._available = True
    p.update({"model": "A", "id": 1})
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("rtl433") == "1d"
    p.on_unload(ui)
    assert not ui.has_element("rtl433")


def test_ui_off_when_unavailable(load_plugin, ui):
    p = _make(load_plugin)
    p._available = False
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("rtl433") == "off"
