import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("conflict_referee", ROOT / "conflict_referee.py")
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


def test_parse_position():
    assert cr.parse_position("10,20") == (10, 20)
    assert cr.parse_position("bad") is None
    assert cr.parse_position("1,2,3") is None


def test_extract_resources_only_enabled():
    cfg = {
        "a": {"enabled": True, "position": "10,20", "gpio_pin": 18},
        "b": {"enabled": False, "position": "10,20"},   # disabled -> ignored
        "c": {"enabled": True, "fan_pin": "18"},
    }
    res = cr.extract_resources(cfg)
    assert res["positions"] == {"a": (10, 20)}
    assert res["pins"]["a"] == {18} and res["pins"]["c"] == {18}


def test_find_position_conflict():
    cfg = {"a": {"enabled": True, "position": "5,5"},
           "b": {"enabled": True, "position": "5,5"},
           "c": {"enabled": True, "position": "9,9"}}
    conflicts = cr.find_conflicts(cr.extract_resources(cfg))
    pos = [c for c in conflicts if c["type"] == "ui_position"]
    assert len(pos) == 1
    assert pos[0]["resource"] == "5,5"
    assert pos[0]["plugins"] == ["a", "b"]


def test_find_pin_conflict():
    cfg = {"fan": {"enabled": True, "gpio_pin": 18},
           "led": {"enabled": True, "pin": 18},
           "other": {"enabled": True, "gpio_pin": 21}}
    conflicts = cr.find_conflicts(cr.extract_resources(cfg))
    pins = [c for c in conflicts if c["type"] == "gpio_pin"]
    assert len(pins) == 1
    assert pins[0]["resource"] == "18"
    assert pins[0]["plugins"] == ["fan", "led"]


def test_no_conflicts():
    cfg = {"a": {"enabled": True, "position": "1,1"},
           "b": {"enabled": True, "position": "2,2"}}
    assert cr.find_conflicts(cr.extract_resources(cfg)) == []


def _make(load_plugin):
    p = load_plugin("conflict_referee.py", options={})
    p.on_loaded()
    return p


def test_refresh_and_ui(load_plugin, ui):
    p = _make(load_plugin)
    cfg = {"a": {"enabled": True, "position": "5,5"}, "b": {"enabled": True, "position": "5,5"}}
    p.refresh(plugins_cfg=cfg)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("referee") == "1"
    # clean config -> ok
    p.refresh(plugins_cfg={"a": {"enabled": True, "position": "1,1"}})
    p.on_ui_update(ui)
    assert ui.get("referee") == "ok"
    p.on_unload(ui)
    assert not ui.has_element("referee")
