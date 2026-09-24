import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("milestone_fireworks", ROOT / "milestone_fireworks.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

MS = [10, 25, 50, 100, 250, 500, 1000]


def test_crossed_basic():
    assert mf.crossed_milestones(0, 10, MS) == [10]
    assert mf.crossed_milestones(9, 11, MS) == [10]
    assert mf.crossed_milestones(5, 60, MS) == [10, 25, 50]
    assert mf.crossed_milestones(10, 10, MS) == []
    assert mf.crossed_milestones(11, 24, MS) == []


def test_crossed_every_1000_after_last():
    assert mf.crossed_milestones(999, 1001, MS) == [1000]
    assert mf.crossed_milestones(1999, 2001, MS) == [2000]
    assert mf.crossed_milestones(1000, 3000, MS) == [2000, 3000]


def _make(load_plugin, tmp_path, **opts):
    options = {"data_path": str(tmp_path / "mf.json"), "celebrate_secs": 8}
    options.update(opts)
    p = load_plugin("milestone_fireworks.py", options=options)
    p.on_loaded()
    return p


def test_add_triggers_celebration(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    # 9 handshakes -> no milestone yet
    for _ in range(9):
        assert p.add(1, now=0) is None
    # 10th -> milestone 10
    assert p.add(1, now=100) == 10
    assert p.celebrating(now=105) is True
    assert p.celebrating(now=200) is False   # celebration window elapsed


def test_add_bulk_returns_last(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.add(60, now=0) == 50            # crosses 10,25,50 -> celebrates 50


def test_persist_count(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.add(5)
    p2 = _make(load_plugin, tmp_path)
    assert p2._count == 5


def test_ui_shows_and_clears(load_plugin, tmp_path, ui):
    import time
    p = _make(load_plugin, tmp_path, face="(^o^)/", message="YAY")
    p.on_ui_setup(ui)
    assert p.add(10) == 10                    # milestone 10
    p._celebrating_until = time.time() + 100  # keep the window open for the assertion
    p.on_ui_update(ui)
    val = ui.get("fireworks")
    assert "YAY" in val and "10" in val
    # force celebration to expire
    p._celebrating_until = 0
    p.on_ui_update(ui)
    assert ui.get("fireworks") == ""
    p.on_unload(ui)
    assert not ui.has_element("fireworks")
