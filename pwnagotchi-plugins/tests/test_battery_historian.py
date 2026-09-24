import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("battery_historian", ROOT / "battery_historian.py")
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)


def test_read_battery_from_sysfs(tmp_path):
    (tmp_path / "capacity").write_text("77\n")
    (tmp_path / "status").write_text("Discharging\n")
    assert bh.read_battery(str(tmp_path)) == (77, False)
    (tmp_path / "status").write_text("Charging\n")
    assert bh.read_battery(str(tmp_path)) == (77, True)


def test_read_battery_missing(tmp_path):
    assert bh.read_battery(str(tmp_path)) is None


def test_rate_per_hour():
    s = {"start_pct": 100, "end_pct": 80, "duration_s": 3600}   # 20% in 1h
    assert abs(bh.rate_per_hour(s) - 20.0) < 0.01
    assert bh.rate_per_hour({"start_pct": 50, "end_pct": 50, "duration_s": 3600}) is None


def test_learned_full_runtime():
    hist = [
        {"start_pct": 100, "end_pct": 80, "duration_s": 3600},   # 20%/h -> 5h full
        {"start_pct": 90, "end_pct": 70, "duration_s": 3600},    # 20%/h
    ]
    assert abs(bh.learned_full_runtime_h(hist) - 5.0) < 0.01


def test_aging_factor_detects_faster_drain():
    # early sessions ~10%/h, recent ~20%/h -> aging ~2.0
    hist = [{"start_pct": 100, "end_pct": 90, "duration_s": 3600} for _ in range(3)] + \
           [{"start_pct": 100, "end_pct": 80, "duration_s": 3600} for _ in range(3)]
    factor = bh.aging_factor(hist)
    assert factor is not None and factor > 1.5


def _make(load_plugin, tmp_path, **opts):
    options = {"source": "file", "power_supply": "none",
               "data_path": str(tmp_path / "bat.json"), "min_drop_pct": 10}
    options.update(opts)
    p = load_plugin("battery_historian.py", options=options)
    p.on_loaded()
    return p


def test_update_records_session_on_charge(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.update(100, charging=False, now=0)
    p.update(80, charging=False, now=3600)      # discharged 20% over 1h
    assert p._session is not None
    p.update(85, charging=True, now=4000)        # charging -> close session
    assert p._session is None
    assert len(p._history) == 1
    assert p._history[0]["start_pct"] == 100 and p._history[0]["end_pct"] == 80


def test_current_stats_live_rate(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.update(100, charging=False, now=0)
    stats = p.update(90, charging=False, now=3600)   # 10%/h
    assert abs(stats["rate_per_hr"] - 10.0) < 0.1
    assert abs(stats["eta_to_empty_h"] - 9.0) < 0.1  # 90% left at 10%/h


def test_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p.update(66, charging=False, now=0)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("battery") == "66%"
    p.update(70, charging=True, now=10)
    p.on_ui_update(ui)
    assert ui.get("battery") == "70%+"
    p.on_unload(ui)
    assert not ui.has_element("battery")


def test_history_persists(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.update(100, charging=False, now=0)
    p.update(80, charging=False, now=3600)
    p.update(90, charging=True, now=4000)         # closes + saves
    p2 = _make(load_plugin, tmp_path)
    assert len(p2._history) == 1
