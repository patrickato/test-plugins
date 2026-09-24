import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("achievements", ROOT / "achievements.py")
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)


def test_evaluate_returns_new_only():
    stats = {"handshakes": 1, "networks": 0, "peers": 0, "days": 0}
    assert ac.evaluate(stats, []) == ["first_blood"]
    assert ac.evaluate(stats, ["first_blood"]) == []   # already unlocked


def test_evaluate_multiple_thresholds():
    stats = {"handshakes": 100, "networks": 100, "peers": 1, "days": 0}
    got = ac.evaluate(stats, [])
    assert {"first_blood", "handshake_10", "handshake_100", "networker", "social"} <= set(got)
    assert "handshake_1000" not in got


def _make(load_plugin, tmp_path):
    p = load_plugin("achievements.py", options={"data_path": str(tmp_path / "ach.json")})
    p.on_loaded()
    return p


def test_record_handshake_unlocks(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    new = p.record_handshake()
    assert "first_blood" in new
    assert "first_blood" in p._unlocked


def test_night_owl_hidden(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(hour=3)             # 3 AM
    assert "night_owl" in p._unlocked


def test_no_night_owl_in_daytime(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(hour=14)
    assert "night_owl" not in p._unlocked


def test_networks_and_peers_unlock(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_networks([{"mac": "%012x" % i} for i in range(100)])
    assert "networker" in p._unlocked
    p.record_peer("peerA")
    assert "social" in p._unlocked


def test_days_unlock(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    for d in range(1, 8):
        p.record_day("2026-01-%02d" % d)
    assert "dedicated" in p._unlocked


def test_persist_roundtrip(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake()
    p.record_networks([{"mac": "aa"}])
    p2 = _make(load_plugin, tmp_path)
    assert p2._handshakes == 1
    assert "first_blood" in p2._unlocked
    assert p2._net_set == {"aa"}


def test_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p.record_handshake()
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    total = len(ac.ACHIEVEMENTS)
    assert ui.get("ach") == "1/%d" % total
    p.on_unload(ui)
    assert not ui.has_element("ach")
