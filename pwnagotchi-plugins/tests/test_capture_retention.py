import importlib.util
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("capture_retention", ROOT / "capture_retention.py")
crn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crn)


def test_evaluate_priorities():
    meta = [
        {"path": "solved", "solved": True, "grade": "A", "age_days": 1},
        {"path": "junk", "solved": False, "grade": "F", "age_days": 1},
        {"path": "old_c", "solved": False, "grade": "C", "age_days": 100},      # partial, old
        {"path": "old_b", "solved": False, "grade": "B", "age_days": 100},      # crackable, old
        {"path": "fresh_c", "solved": False, "grade": "C", "age_days": 1},      # partial, fresh
    ]
    pol = {"max_age_days": 30, "protect_unsolved": True, "space_pressure": False}
    reasons = {c["path"]: c["reason"] for c in crn.evaluate(meta, pol)}
    assert reasons["solved"] == "solved"
    assert reasons["junk"] == "junk"
    assert reasons["old_c"] == "old"           # partial + old expires
    assert "old_b" not in reasons              # crackable protected even when old
    assert "fresh_c" not in reasons            # not old enough yet


def test_space_pressure_overrides_protection():
    meta = [{"path": "old_b", "solved": False, "grade": "B", "age_days": 100}]
    pol = {"max_age_days": 30, "protect_unsolved": True, "space_pressure": True}
    assert crn.evaluate(meta, pol)[0]["reason"] == "old"   # protection lifted under pressure


def test_grade_of_prefers_sidecar(tmp_path):
    f = tmp_path / "AP_00c0ca111111.pcap"
    f.write_bytes(b"\x88\x8e")                  # 1 EAPOL -> would be C
    (tmp_path / "AP_00c0ca111111.pcap.grade").write_text("A eapol=4\n")
    assert crn.grade_of(str(f)) == "A"          # sidecar wins


def _make(load_plugin, tmp_path, **opts):
    options = {"handshakes": str(tmp_path),
               "data_path": str(tmp_path / "q.json"),
               "min_free_mb": 0}                # ignore space in tests unless overridden
    options.update(opts)
    p = load_plugin("capture_retention.py", options=options)
    p.on_loaded()
    return p


def _old_cap(tmp_path, name, eapol, age_days):
    f = tmp_path / name
    f.write_bytes(b"\x88\x8e" * eapol + b"pad")
    old = time.time() - age_days * 86400
    os.utime(f, (old, old))
    return f


def test_grace_window_queues_then_deletes(load_plugin, tmp_path):
    _old_cap(tmp_path, "junk_00c0ca111111.pcap", 0, 1)   # junk -> candidate
    p = _make(load_plugin, tmp_path, grace_days=3)
    now = time.time()

    r1 = p.run(now=now)
    assert "junk_00c0ca111111.pcap" in r1["queued"]
    assert r1["deleted"] == []
    assert (tmp_path / "junk_00c0ca111111.pcap").exists()   # grace not elapsed

    r2 = p.run(now=now + 4 * 86400)                          # past grace
    assert "junk_00c0ca111111.pcap" in r2["deleted"]
    assert not (tmp_path / "junk_00c0ca111111.pcap").exists()


def test_dry_run_never_deletes(load_plugin, tmp_path):
    _old_cap(tmp_path, "junk_00c0ca111111.pcap", 0, 1)
    p = _make(load_plugin, tmp_path, grace_days=0, dry_run=True)
    now = time.time()
    r = p.run(now=now)                                       # grace 0 -> eligible now
    assert r["deleted"] == []
    assert (tmp_path / "junk_00c0ca111111.pcap").exists()


def test_delete_removes_sidecars(load_plugin, tmp_path):
    f = _old_cap(tmp_path, "solved_00c0ca111111.pcap", 4, 1)
    (tmp_path / "solved_00c0ca111111.pcap.cracked").write_text("x")   # solved -> candidate
    (tmp_path / "solved_00c0ca111111.pcap.grade").write_text("A\n")
    p = _make(load_plugin, tmp_path, grace_days=0)
    p.run(now=time.time())
    assert not f.exists()
    assert not (tmp_path / "solved_00c0ca111111.pcap.cracked").exists()
    assert not (tmp_path / "solved_00c0ca111111.pcap.grade").exists()


def test_ui_and_empty_dir(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    assert p.run(now=time.time()) == {"queued": [], "deleted": []}
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("retention") == "0q"
    p.on_unload(ui)
    assert not ui.has_element("retention")
