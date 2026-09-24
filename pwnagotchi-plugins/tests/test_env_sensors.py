import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("env_sensors", ROOT / "env_sensors.py")
es = importlib.util.module_from_spec(spec)
spec.loader.exec_module(es)


def test_parse_address():
    assert es.parse_address("0x76", 0x76) == 0x76
    assert es.parse_address("68", 0) == 68
    assert es.parse_address(0x44, 0) == 0x44
    assert es.parse_address(None, 0x76) == 0x76
    assert es.parse_address("garbage", 0x77) == 0x77


def test_registry_has_types():
    assert set(es.DRIVERS) >= {"mock", "bme280", "sht3x", "tsl2591"}


def _make(load_plugin, sensors):
    p = load_plugin("env_sensors.py", options={"sensors": sensors})
    p.on_loaded()
    return p


def test_build_skips_unknown_type(load_plugin):
    p = _make(load_plugin, [{"type": "does_not_exist"}])
    assert p._sensors == []


def test_mock_sensor_polls(load_plugin):
    p = _make(load_plugin, [
        {"type": "mock", "name": "weather", "values": {"temperature_C": 21.3, "humidity": 55}},
        {"type": "mock", "name": "light", "values": {"lux": 300.0}},
    ])
    latest = p.poll()
    assert latest["weather"]["temperature_C"] == 21.3
    assert latest["light"]["lux"] == 300.0


def test_ui_prefers_temperature(load_plugin, ui):
    p = _make(load_plugin, [{"type": "mock", "name": "w", "values": {"temperature_C": 21.3}}])
    p.poll()
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("env") == "21C"
    p.on_unload(ui)
    assert not ui.has_element("env")


def test_ui_falls_back_to_lux(load_plugin, ui):
    p = _make(load_plugin, [{"type": "mock", "name": "l", "values": {"lux": 123.0}}])
    p.poll()
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("env") == "123lx"


def test_no_sensors_is_safe(load_plugin, ui):
    p = _make(load_plugin, [])
    assert p.poll() == {}
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("env") == "-"


def test_real_drivers_unavailable_in_test_env(load_plugin):
    # bme280/sht3x/tsl2591 libs aren't installed here -> skipped, not crash
    p = _make(load_plugin, [{"type": "bme280"}, {"type": "sht3x"}, {"type": "tsl2591"}])
    assert p._sensors == []
