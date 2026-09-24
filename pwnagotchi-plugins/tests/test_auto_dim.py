import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("auto_dim", ROOT / "auto_dim.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)


def test_brightness_for_lux():
    assert ad.brightness_for_lux(0, 5, 300, 10, 100) == 10      # dark -> min
    assert ad.brightness_for_lux(500, 5, 300, 10, 100) == 100   # bright -> max
    mid = ad.brightness_for_lux(152.5, 5, 300, 10, 100)         # ~halfway
    assert 50 < mid < 60


def test_brightness_for_time():
    assert ad.brightness_for_time(12, 8, 22, 100, 20) == 100    # daytime
    assert ad.brightness_for_time(23, 8, 22, 100, 20) == 20     # night
    assert ad.brightness_for_time(6, 8, 22, 100, 20) == 20      # early morning = night


def _make(load_plugin, **opts):
    p = load_plugin("auto_dim.py", options=opts)
    p.on_loaded()
    return p


def test_current_brightness_time_mode(load_plugin):
    p = _make(load_plugin, source="time", day_start=8, night_start=22,
              day_brightness=100, night_brightness=20)
    assert p.current_brightness(hour=12) == 100
    assert p.current_brightness(hour=23) == 20


def test_current_brightness_lux_mode(load_plugin):
    p = _make(load_plugin, source="lux", lux_low=5, lux_high=300,
              min_brightness=10, max_brightness=100)
    assert p.current_brightness(lux=0) == 10
    assert p.current_brightness(lux=1000) == 100


def test_apply_without_backend_is_safe(load_plugin):
    p = _make(load_plugin, method="sysfs", backlight_path="/nonexistent/backlight")
    p._apply(50)                # must not raise
    assert p._last_applied == 50


def test_ui(load_plugin, ui):
    p = _make(load_plugin, source="time", day_start=8, night_start=22,
              day_brightness=100, night_brightness=20)
    p._apply(42)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("dim") == "42%"
    p.on_unload(ui)
    assert not ui.has_element("dim")
