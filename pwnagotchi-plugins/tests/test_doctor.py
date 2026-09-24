import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("doctor", ROOT / "doctor.py")
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)


def test_clean_evidence_no_findings():
    ev = {"log": "all good\nstill good\n", "disk_free_mb": 5000, "temp_c": 45,
          "min_free_mb": 200, "max_temp_c": 80}
    assert doc.diagnose(ev) == []


def test_low_disk_and_high_temp():
    ev = {"log": "", "disk_free_mb": 50, "temp_c": 85, "min_free_mb": 200, "max_temp_c": 80}
    ids = {f["id"] for f in doc.diagnose(ev)}
    assert ids == {"low_disk", "high_temp"}


def test_wifi_driver_rule_needs_threshold():
    log = "\n".join("wifi error blah" for _ in range(5))
    findings = doc.diagnose({"log": log})
    assert any(f["id"] == "wifi_driver" for f in findings)
    # only 4 occurrences -> below min_count(5) -> no finding
    log4 = "\n".join("wifi error blah" for _ in range(4))
    assert not any(f["id"] == "wifi_driver" for f in doc.diagnose({"log": log4}))


def test_various_log_rules():
    log = ("bettercap connection refused\n"
           "pwngrid error: nope\n"
           "bt-tether error pairing\n"
           "error while loading fancygotchi\n")
    ids = {f["id"] for f in doc.diagnose({"log": log})}
    assert {"bettercap_down", "pwngrid", "bt_tether", "plugin_load"} <= ids


def test_findings_sorted_by_severity():
    ev = {"log": "pwngrid error\n", "disk_free_mb": 10, "min_free_mb": 200}
    findings = doc.diagnose(ev)
    # low_disk (high) should sort before pwngrid (warn)
    assert findings[0]["severity"] == "high"


def _make(load_plugin, tmp_path, log_text="", **opts):
    logf = tmp_path / "pwn.log"
    logf.write_text(log_text)
    options = {"log_path": str(logf), "min_free_mb": 0, "max_temp_c": 200}  # neutralize live checks
    options.update(opts)
    p = load_plugin("doctor.py", options=options)
    p.on_loaded()
    return p


def test_run_reads_log_and_ui(load_plugin, tmp_path, ui, agent):
    p = _make(load_plugin, tmp_path, log_text="pwngrid error here\n")
    p.on_ready(agent)
    assert any(f["id"] == "pwngrid" for f in p._findings)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("doctor") == "1!"
    p.on_unload(ui)
    assert not ui.has_element("doctor")


def test_run_clean_shows_ok(load_plugin, tmp_path, ui, agent):
    p = _make(load_plugin, tmp_path, log_text="nothing wrong\n")
    p.on_ready(agent)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("doctor") == "OK"
