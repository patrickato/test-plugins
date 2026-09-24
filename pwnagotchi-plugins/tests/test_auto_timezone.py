import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("auto_timezone", ROOT / "auto_timezone.py")
az = importlib.util.module_from_spec(spec)
spec.loader.exec_module(az)


def test_lon_to_offset():
    assert az.lon_to_offset(0) == 0
    assert az.lon_to_offset(75) == 5
    assert az.lon_to_offset(-120) == -8
    assert az.lon_to_offset(200) == 12      # clamped
    assert az.lon_to_offset(-200) == -12    # clamped


def test_offset_to_etc_zone_sign_inversion():
    assert az.offset_to_etc_zone(0) == "Etc/UTC"
    assert az.offset_to_etc_zone(5) == "Etc/GMT-5"    # UTC+5
    assert az.offset_to_etc_zone(-8) == "Etc/GMT+8"   # UTC-8


def test_resolve_zone_fallback():
    # timezonefinder not installed in the test env -> coarse Etc fallback
    assert az.resolve_zone(51.5, -0.13) == "Etc/UTC"
    assert az.resolve_zone(40.0, -74.0) == "Etc/GMT+5"


def _make(load_plugin, **opts):
    p = load_plugin("auto_timezone.py", options=opts)
    p.on_loaded()
    return p


def test_apply_zone_changes_when_different(load_plugin):
    p = _make(load_plugin, apply=True)
    calls = []
    changed = p.apply_zone("Etc/GMT-5", runner=lambda cmd: calls.append(cmd), current="Etc/UTC")
    assert changed
    assert calls == [["timedatectl", "set-timezone", "Etc/GMT-5"]]


def test_apply_zone_noop_when_same(load_plugin):
    p = _make(load_plugin, apply=True)
    calls = []
    changed = p.apply_zone("Etc/UTC", runner=lambda cmd: calls.append(cmd), current="Etc/UTC")
    assert not changed and calls == []


def test_apply_false_is_dry_run(load_plugin):
    p = _make(load_plugin, apply=False)
    calls = []
    changed = p.apply_zone("Etc/GMT-5", runner=lambda cmd: calls.append(cmd), current="Etc/UTC")
    assert not changed and calls == []


def test_manual_override_and_tick(load_plugin, agent):
    # manual lat/lon skips gpsd; apply=false so no system change, just status
    p = _make(load_plugin, apply=False, latitude=40.0, longitude=-74.0)
    p._tick(force=True)
    assert p._status.startswith("Etc/GMT+5")


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p._status = "Etc/GMT-5"
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("auto_tz") == "GMT-5"     # basename after '/'
    p.on_unload(ui)
    assert not ui.has_element("auto_tz")
