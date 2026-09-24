import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("capture_grader", ROOT / "capture_grader.py")
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)


def test_classify_thresholds():
    assert cg.classify(4)["grade"] == "A" and cg.classify(4)["crackable"]
    assert cg.classify(3)["grade"] == "A"
    assert cg.classify(2)["grade"] == "B" and cg.classify(2)["crackable"]
    assert cg.classify(1)["grade"] == "C" and not cg.classify(1)["crackable"]
    assert cg.classify(0)["grade"] == "F" and not cg.classify(0)["crackable"]


def _cap(tmp_path, name, eapol):
    (tmp_path / name).write_bytes(b"\x88\x8e" * eapol + b"pad")
    return tmp_path / name


def test_count_and_grade_file(tmp_path):
    f = _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    assert cg.count_eapol(str(f)) == 4
    g = cg.grade_file(str(f))
    assert g["grade"] == "A" and g["file"] == "AP_00c0ca111111.pcap"


def _make(load_plugin, tmp_path, **opts):
    options = {"handshakes": str(tmp_path)}
    options.update(opts)
    p = load_plugin("capture_grader.py", options=options)
    p.on_loaded()
    return p


def test_on_handshake_grades_and_writes_sidecar(load_plugin, tmp_path, agent):
    f = _cap(tmp_path, "AP_00c0ca111111.pcap", 2)
    p = _make(load_plugin, tmp_path)
    p.on_handshake(agent, str(f), {}, {})
    assert p._counts["B"] == 1
    assert (tmp_path / "AP_00c0ca111111.pcap.grade").exists()
    assert "B" in (tmp_path / "AP_00c0ca111111.pcap.grade").read_text()


def test_no_sidecar_when_disabled(load_plugin, tmp_path, agent):
    f = _cap(tmp_path, "AP_00c0ca111111.pcap", 2)
    p = _make(load_plugin, tmp_path, write_sidecar=False)
    p.on_handshake(agent, str(f), {}, {})
    assert not (tmp_path / "AP_00c0ca111111.pcap.grade").exists()


def test_sweep_counts(load_plugin, tmp_path):
    _cap(tmp_path, "a_00c0ca111111.pcap", 4)   # A
    _cap(tmp_path, "b_00c0ca222222.pcap", 2)   # B
    _cap(tmp_path, "c_00c0ca333333.pcap", 0)   # F
    p = _make(load_plugin, tmp_path)
    graded = p.sweep()
    assert len(graded) == 3
    assert sum(1 for g in graded if g["crackable"]) == 2


def test_ui(load_plugin, tmp_path, agent, ui):
    f = _cap(tmp_path, "AP_00c0ca111111.pcap", 4)
    p = _make(load_plugin, tmp_path)
    p.on_handshake(agent, str(f), {}, {})
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("grade").startswith("A")
    p.on_unload(ui)
    assert not ui.has_element("grade")
