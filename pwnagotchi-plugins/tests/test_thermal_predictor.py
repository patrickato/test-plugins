import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("thermal_predictor", ROOT / "thermal_predictor.py")
tp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tp)


def test_linreg_slope():
    pts = [(0, 50), (60, 52), (120, 54)]     # +2C per 60s -> 0.0333 C/s
    assert abs(tp.linreg_slope(pts) - (2.0 / 60.0)) < 1e-6
    assert tp.linreg_slope([(0, 50)]) == 0.0
    assert tp.linreg_slope([(0, 50), (0, 60)]) == 0.0   # zero variance in t


def test_predict_time_to():
    assert tp.predict_time_to(54, 2.0 / 60.0, 80) == (80 - 54) / (2.0 / 60.0)
    assert tp.predict_time_to(85, 0.1, 80) == 0.0        # already over
    assert tp.predict_time_to(50, 0, 80) is None         # not rising


def _make(load_plugin, **opts):
    options = {"threshold_c": 80, "lead_seconds": 120, "window_secs": 1000}
    options.update(opts)
    p = load_plugin("thermal_predictor.py", options=options)
    p.on_loaded()
    return p


def test_status_rising_then_warn(load_plugin):
    p = _make(load_plugin)
    p.add_sample(50, 0)
    p.add_sample(52, 60)
    st = p.add_sample(54, 120)               # +2C/min, far from 80 -> rising
    assert st["state"] == "rising"
    assert abs(st["slope_per_min"] - 2.0) < 0.1

    p2 = _make(load_plugin, lead_seconds=120)
    p2.add_sample(76, 0)
    st2 = p2.add_sample(79, 60)              # near threshold, steep -> warn
    assert st2["state"] == "warn"


def test_status_ok_when_flat(load_plugin):
    p = _make(load_plugin)
    p.add_sample(55, 0)
    st = p.add_sample(55, 60)                 # flat -> ok
    assert st["state"] == "ok"


def test_window_trims_old_samples(load_plugin):
    p = _make(load_plugin, window_secs=100)
    p.add_sample(50, 0)
    p.add_sample(60, 200)                      # 0 is now outside the 100s window
    assert len(p._samples) == 1


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p.add_sample(50, 0)
    p.add_sample(52, 60)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("thermal") in ("+2/m", "WARN", "+2/m")   # rising trend shown
    p.on_unload(ui)
    assert not ui.has_element("thermal")
