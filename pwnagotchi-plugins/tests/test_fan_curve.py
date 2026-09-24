import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fan_curve", ROOT / "fan_curve.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)


def test_duty_for_interpolation():
    curve = [[50, 0], [55, 40], [65, 70], [75, 100]]
    assert fc.duty_for(40, curve) == 0        # below first point
    assert fc.duty_for(50, curve) == 0
    assert fc.duty_for(60, curve) == 55       # halfway 55->65 => 40->70 => 55
    assert fc.duty_for(75, curve) == 100
    assert fc.duty_for(90, curve) == 100      # above last point


def _make(load_plugin, **opts):
    options = {"curve": [[50, 0], [55, 40], [65, 70], [75, 100]],
               "min_duty": 30, "hysteresis_c": 4}
    options.update(opts)
    p = load_plugin("fan_curve.py", options=options)
    p.on_loaded()
    return p


def test_on_off_temps_derived(load_plugin):
    p = _make(load_plugin)
    assert p._on_temp == 55        # first curve temp with duty>0
    assert p._off_temp == 51       # 55 - 4


def test_control_hysteresis(load_plugin):
    p = _make(load_plugin)
    # cold: fan off
    assert p.update_control(50) == 0
    # crosses on_temp: turns on, at least min_duty
    assert p.update_control(56) >= 30
    # drops to 52 (< on_temp but > off_temp): stays on due to hysteresis
    assert p.update_control(52) >= 30
    # drops to 51 (<= off_temp): turns off
    assert p.update_control(51) == 0
    # back at 52 (< on_temp): stays off (won't re-trigger until >=55)
    assert p.update_control(52) == 0


def test_control_min_duty_floor(load_plugin):
    p = _make(load_plugin, min_duty=35)
    # at 55 curve says 40, but just-on near a low-duty region should honor min_duty floor
    duty = p.update_control(55)   # on_temp exactly -> on
    assert duty >= 35


def test_apply_without_backend_is_safe(load_plugin):
    p = _make(load_plugin)
    p._backend = None
    p._apply(70)                  # must not raise
    assert p._last_duty == 70


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p._last_duty = 70
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("fan") == "70%"
    p.on_unload(ui)
    assert not ui.has_element("fan")
