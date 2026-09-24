import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("crack_reconciler", ROOT / "crack_reconciler.py")
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


def test_parse_wpasec_format():
    text = "aabbccddeeff:112233445566:MyESSID:hunter2\n" \
           "001122334455:665544332211:Other:s3cret\n"
    cracked = cr.parse_results(text)
    assert cracked["aabbccddeeff"] == "hunter2"
    assert cracked["001122334455"] == "s3cret"


def test_parse_hashcat_22000_format():
    line = "WPA*02*deadbeef*aabbccddeeff*112233445566*4d79*0*0:letmein"
    cracked = cr.parse_results(line)
    assert cracked["aabbccddeeff"] == "letmein"


def test_parse_ignores_junk():
    assert cr.parse_results("nonsense line without fields") == {}
    assert cr.parse_results("") == {}


def _make(load_plugin, tmp_path, **opts):
    options = {"handshakes": str(tmp_path)}
    options.update(opts)
    p = load_plugin("crack_reconciler.py", options=options)
    p.on_loaded()
    return p


def test_reconcile_marks_solved(load_plugin, tmp_path):
    # captures
    (tmp_path / "AP_aabbccddeeff.pcap").write_bytes(b"x")
    (tmp_path / "Other_001122334455.pcap").write_bytes(b"x")
    # a potfile that solves only the first
    pot = tmp_path / "hashcat.potfile"
    pot.write_text("WPA*02*mic*aabbccddeeff*112233445566*4d79*0*0:letmein\n")

    p = _make(load_plugin, tmp_path, potfiles=[str(pot)])
    report = p.reconcile()

    by_file = {e["file"]: e for e in report}
    assert by_file["AP_aabbccddeeff.pcap"]["solved"] is True
    assert by_file["AP_aabbccddeeff.pcap"]["password"] == "letmein"
    assert by_file["Other_001122334455.pcap"]["solved"] is False
    assert (tmp_path / "AP_aabbccddeeff.pcap.cracked").exists()
    assert not (tmp_path / "Other_001122334455.pcap.cracked").exists()
    assert p.is_solved("aa:bb:cc:dd:ee:ff")   # normalization-tolerant


def test_ui(load_plugin, tmp_path, ui):
    (tmp_path / "AP_aabbccddeeff.pcap").write_bytes(b"x")
    pot = tmp_path / "p.pot"
    pot.write_text("aabbccddeeff:112233445566:E:pw\n")
    p = _make(load_plugin, tmp_path, potfiles=[str(pot)])
    p.reconcile()
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("cracked") == "1/1"
    p.on_unload(ui)
    assert not ui.has_element("cracked")


def test_missing_potfiles_safe(load_plugin, tmp_path):
    (tmp_path / "AP_aabbccddeeff.pcap").write_bytes(b"x")
    p = _make(load_plugin, tmp_path, potfiles=[str(tmp_path / "nope.pot")])
    report = p.reconcile()
    assert report[0]["solved"] is False
