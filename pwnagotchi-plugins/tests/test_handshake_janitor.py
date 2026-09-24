import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("handshake_janitor", ROOT / "handshake_janitor.py")
hj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hj)


def test_bssid_from_filename():
    assert hj.bssid_from_filename("MyAP_00c0ca123456.pcap") == "00c0ca123456"
    assert hj.bssid_from_filename("My_AP_aa:bb:cc:dd:ee:ff.pcap") == "aabbccddeeff"
    assert hj.bssid_from_filename("MyAP_00c0ca123456_2.pcap") == "00c0ca123456"  # trailing counter
    assert hj.bssid_from_filename("notahandshake.txt") is None


def test_group_by_bssid():
    files = ["a_00c0ca111111.pcap", "b_00c0ca111111.pcap", "c_00c0ca222222.pcap"]
    groups = hj.group_by_bssid(files)
    assert set(groups) == {"00c0ca111111", "00c0ca222222"}
    assert len(groups["00c0ca111111"]) == 2


def test_plan_keeps_highest_score_then_size():
    scored = [
        {"path": "a", "score": 2, "size": 100, "mtime": 1},
        {"path": "b", "score": 4, "size": 10, "mtime": 1},   # best: most EAPOL frames
        {"path": "c", "score": 2, "size": 300, "mtime": 1},
    ]
    keep, drops = hj.plan(scored)
    assert keep["path"] == "b"
    assert {d["path"] for d in drops} == {"a", "c"}


def test_count_eapol_heuristic(tmp_path):
    f = tmp_path / "x.pcap"
    f.write_bytes(b"....\x88\x8e....\x88\x8e....\x88\x8e")
    assert hj.count_eapol(str(f)) == 3


def _make(load_plugin, tmp_path, **opts):
    options = {"handshakes": str(tmp_path), "action": "archive"}
    options.update(opts)
    p = load_plugin("handshake_janitor.py", options=options)
    p.on_loaded()
    return p


def _cap(tmp_path, name, eapol):
    (tmp_path / name).write_bytes(b"\x88\x8e" * eapol + b"padding")
    return tmp_path / name


def test_run_archives_duplicates(load_plugin, tmp_path):
    # two files for same BSSID: one with 4 EAPOL, one with 1 -> keep the 4
    _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    _cap(tmp_path, "APdup_00c0ca111111.pcap", 1)
    _cap(tmp_path, "Other_00c0ca222222.pcap", 2)   # singleton, untouched

    p = _make(load_plugin, tmp_path)
    results = p.run()

    assert len(results) == 1
    assert results[0]["kept"] == "AP_00c0ca111111.pcap"
    assert (tmp_path / "AP_00c0ca111111.pcap").exists()           # best kept
    assert not (tmp_path / "APdup_00c0ca111111.pcap").exists()    # dup moved
    assert (tmp_path / "duplicates" / "APdup_00c0ca111111.pcap").exists()
    assert (tmp_path / "Other_00c0ca222222.pcap").exists()        # singleton untouched
    assert p._reclaimed_files == 1


def test_dry_run_moves_nothing(load_plugin, tmp_path):
    _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    _cap(tmp_path, "APdup_00c0ca111111.pcap", 1)
    p = _make(load_plugin, tmp_path, dry_run=True)
    results = p.run()
    assert results[0]["action"] == "dry_run"
    assert (tmp_path / "APdup_00c0ca111111.pcap").exists()        # nothing moved
    assert not (tmp_path / "duplicates").exists()


def test_run_delete_action(load_plugin, tmp_path):
    _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    _cap(tmp_path, "APdup_00c0ca111111.pcap", 1)
    p = _make(load_plugin, tmp_path, action="delete")
    p.run()
    assert not (tmp_path / "APdup_00c0ca111111.pcap").exists()
    assert not (tmp_path / "duplicates").exists()                 # deleted, not archived


def test_ui(load_plugin, tmp_path, ui):
    _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    _cap(tmp_path, "APdup_00c0ca111111.pcap", 1)
    p = _make(load_plugin, tmp_path)
    p.run()
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("janitor") == "1"
    p.on_unload(ui)
    assert not ui.has_element("janitor")


def test_empty_dir_is_safe(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.run() == []
