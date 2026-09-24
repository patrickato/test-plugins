import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("why_no_handshakes", ROOT / "why_no_handshakes.py")
wn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wn)

IW_MON = "phy#0\n\tInterface wlan0mon\n\t\ttype monitor\n"
IW_NOMON = "phy#0\n\tInterface wlan0\n\t\ttype managed\n"


def test_iw_has_monitor():
    assert wn.iw_has_monitor(IW_MON) is True
    assert wn.iw_has_monitor("phy#0\n\tInterface wlan1\n\t\ttype monitor\n") is True
    assert wn.iw_has_monitor(IW_NOMON) is False


def test_analyze_working():
    f = wn.analyze({"pcap_count": 5, "monitor_present": True, "ap_count": 3, "client_count": 2})
    assert f[0]["severity"] == "info" and "working" in f[0]["symptom"]


def test_analyze_no_monitor():
    f = wn.analyze({"pcap_count": 0, "monitor_present": False, "ap_count": 3, "client_count": 1})
    assert any("monitor" in x["symptom"] for x in f)
    assert f[0]["severity"] == "high"


def test_analyze_no_aps():
    f = wn.analyze({"pcap_count": 0, "monitor_present": True, "ap_count": 0, "client_count": 0})
    assert any("no access points" in x["symptom"] for x in f)


def test_analyze_aps_no_clients():
    f = wn.analyze({"pcap_count": 0, "monitor_present": True, "ap_count": 5, "client_count": 0})
    assert any("no clients" in x["symptom"] for x in f)


def test_analyze_conditions_fine():
    f = wn.analyze({"pcap_count": 0, "monitor_present": True, "ap_count": 5, "client_count": 3})
    assert any("look fine" in x["symptom"] for x in f)


def _make(load_plugin, tmp_path, **opts):
    options = {"handshakes": str(tmp_path)}
    options.update(opts)
    p = load_plugin("why_no_handshakes.py", options=options)
    p.on_loaded()
    return p


def test_wifi_update_counts(load_plugin, tmp_path, agent):
    p = _make(load_plugin, tmp_path)
    p.on_wifi_update(agent, [
        {"mac": "a", "clients": [{"mac": "c1"}, {"mac": "c2"}]},
        {"mac": "b", "clients": []},
        {"mac": "c"},
    ])
    assert p._ap_count == 3
    assert p._client_count == 2


def test_refresh_and_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p._ap_count = 0
    p.refresh(runner=lambda cmd: IW_NOMON)      # no monitor, no APs, no pcaps
    assert p._findings[0]["severity"] == "high"
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("hswhy").endswith("?")        # issues flagged
    # now a capture exists -> ok
    (tmp_path / "AP_00c0ca111111.pcap").write_bytes(b"x")
    p.refresh(runner=lambda cmd: IW_MON)
    p.on_ui_update(ui)
    assert ui.get("hswhy") == "ok"
    p.on_unload(ui)
    assert not ui.has_element("hswhy")
