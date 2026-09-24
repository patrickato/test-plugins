import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("doctor", ROOT / "doctor.py")
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)


# ---- pure parsers ----------------------------------------------------------------------
def test_parse_throttled():
    t = doc.parse_throttled("throttled=0x50005")   # 0x1 uv_now,0x4 thr_now,0x10000 uv_occ,0x40000 thr_occ
    assert t["undervoltage_now"] and t["throttled_now"]
    assert t["undervoltage_occurred"] and t["throttled_occurred"]
    assert doc.parse_throttled("throttled=0x0") == {
        "undervoltage_now": False, "throttled_now": False,
        "undervoltage_occurred": False, "throttled_occurred": False}
    assert doc.parse_throttled("garbage") == {}


def test_parse_dmesg():
    text = ("[1] Under-voltage detected! (0x50005)\n"
            "[2] usb 1-1: reset high-speed USB device\n"
            "[3] Out of memory: Killed process 1234\n"
            "[4] mmcblk0: error -84 transferring data\n"
            "[5] brcmfmac: firmware failed to load\n")
    d = doc.parse_dmesg(text)
    assert d["undervoltage"] == 1 and d["usb_reset"] == 1 and d["oom"] == 1
    assert d["sd_error"] == 1 and d["wifi_fw"] == 1


def test_parse_mounts_ro():
    assert doc.parse_mounts_ro("/dev/mmcblk0p2 / ext4 ro,noatime 0 0\n") is True
    assert doc.parse_mounts_ro("/dev/mmcblk0p2 / ext4 rw,noatime 0 0\n") is False


def test_config_valid():
    assert doc.config_valid('a = 1\n[x]\ny = "z"\n')["valid"] is True
    bad = doc.config_valid('a = = 1\n')
    assert bad["valid"] is False and bad["error"]


def test_parse_log_signals():
    log = ("Traceback (most recent call last):\nTraceback again\nTraceback three\n"
           "error while loading fancygotchi\n"
           "bettercap connection refused\n")
    s = doc.parse_log_signals(log)
    assert s["tracebacks"] == 3
    assert s["plugins_failed"] == ["fancygotchi"]
    assert s["bettercap_refused"] == 1


# ---- diagnosis over signals ------------------------------------------------------------
def _cfg(min_free=200, max_temp=80):
    return {"min_free_mb": min_free, "max_temp_c": max_temp}


def test_diagnose_clean():
    signals = {"_cfg": _cfg(), "disk": {"free_mb": 5000, "root_ro": False},
               "services": {"bettercap": {"active": True}}, "bettercap_reachable": True,
               "monitor_present": True, "rfkill_blocked": False,
               "time": {"year_ok": True}, "temp_c": 45, "throttled": {}, "dmesg": {}, "log": {},
               "config": {"valid": True}}
    assert doc.diagnose(signals) == []


def test_diagnose_detects_multiple():
    signals = {"_cfg": _cfg(), "disk": {"free_mb": 10, "root_ro": True},
               "services": {"bettercap": {"active": False}}, "bettercap_reachable": False,
               "monitor_present": False, "rfkill_blocked": True, "time": {"year_ok": False},
               "temp_c": 90, "throttled": {"undervoltage_now": True}, "dmesg": {"sd_error": 2},
               "log": {"tracebacks": 4, "plugins_failed": ["boom"]}, "config": {"valid": False}}
    ids = {f["id"] for f in doc.diagnose(signals)}
    for expect in ("sd_readonly", "disk_full", "bettercap_down", "rfkill_blocked", "no_monitor",
                   "clock_wrong", "config_invalid", "plugin_crash_loop", "undervoltage",
                   "overheat", "sd_errors"):
        assert expect in ids, expect
    # sorted high-first
    assert doc.diagnose(signals)[0]["severity"] == "high"


# ---- circuit breaker & policy ----------------------------------------------------------
def test_circuit_breaker():
    b = doc.CircuitBreaker(max_attempts=2, window=100)
    assert b.allow("x", now=0) and (b.record("x", 0) or True)
    assert b.allow("x", now=1) and (b.record("x", 1) or True)
    assert b.allow("x", now=2) is False           # 2 attempts in window -> stop
    assert b.allow("x", now=500) is True           # window elapsed


def test_policy_allows():
    assert doc.policy_allows("safe", "safe") is True
    assert doc.policy_allows("risky", "safe") is False
    assert doc.policy_allows("risky", "all") is True
    assert doc.policy_allows("safe", "off") is False


# ---- apply_fixes: auto-fix, verify, tiers ----------------------------------------------
def _detect_down(s):
    return s.get("services", {}).get("bettercap", {}).get("active") is False


def test_apply_fix_auto_and_verify_success():
    findings = [{"id": "bettercap_down", "severity": "high", "fix": {
        "action": "restart_service", "args": {"service": "bettercap"}, "tier": "safe"},
        "_detect": _detect_down, "outcome": "detected", "howto": []}]
    calls = []
    runner = lambda cmd: calls.append(cmd)
    breaker = doc.CircuitBreaker()
    # after the fix, recollect shows the service back up -> verified fixed
    recollect = lambda: {"services": {"bettercap": {"active": True}}}
    out = doc.apply_fixes(findings, {"services": {"bettercap": {"active": False}}},
                          "safe", runner, breaker, {}, recollect=recollect, now=0)
    assert out[0]["outcome"] == "fixed"
    assert calls == [["systemctl", "restart", "bettercap"]]


def test_apply_fix_verify_still_broken():
    findings = [{"id": "bettercap_down", "fix": {"action": "restart_service",
                 "args": {"service": "bettercap"}, "tier": "safe"},
                 "_detect": _detect_down, "outcome": "detected", "howto": []}]
    recollect = lambda: {"services": {"bettercap": {"active": False}}}   # still down
    out = doc.apply_fixes(findings, {"services": {"bettercap": {"active": False}}},
                          "safe", lambda c: None, doc.CircuitBreaker(), {}, recollect=recollect)
    assert out[0]["outcome"] == "fix_failed"


def test_apply_fix_risky_needs_user_in_safe_mode():
    findings = [{"id": "sd_readonly", "fix": {"action": "remount_rw", "tier": "risky"},
                 "_detect": lambda s: True, "outcome": "detected", "howto": ["step"]}]
    out = doc.apply_fixes(findings, {}, "safe", lambda c: None, doc.CircuitBreaker(), {})
    assert out[0]["outcome"] == "needs_user"       # risky not auto in safe mode


def test_apply_fix_off_mode_never_acts():
    findings = [{"id": "bettercap_down", "fix": {"action": "restart_service",
                 "args": {"service": "bettercap"}, "tier": "safe"},
                 "_detect": _detect_down, "outcome": "detected", "howto": []}]
    calls = []
    out = doc.apply_fixes(findings, {}, "off", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {})
    assert out[0]["outcome"] == "needs_user" and calls == []


def test_no_fix_is_needs_user():
    findings = [{"id": "undervoltage", "fix": None, "_detect": lambda s: True,
                 "outcome": "detected", "howto": ["use a better PSU"]}]
    out = doc.apply_fixes(findings, {}, "all", lambda c: None, doc.CircuitBreaker(), {})
    assert out[0]["outcome"] == "needs_user"


# ---- file-touching action --------------------------------------------------------------
def test_prune_logs_action(tmp_path):
    log = tmp_path / "pwn.log"
    log.write_text("\n".join("line %d" % i for i in range(5000)) + "\n")
    ctx = {"log_path": str(log), "log_max_bytes": 1000, "log_keep_lines": 100}
    assert doc.act_prune_logs({}, lambda c: None, {}, ctx) is True
    remaining = log.read_text().splitlines()
    assert len(remaining) == 100 and remaining[-1] == "line 4999"
    # under threshold -> no-op
    small = tmp_path / "small.log"
    small.write_text("tiny\n")
    assert doc.act_prune_logs({}, lambda c: None, {},
                              {"log_path": str(small), "log_max_bytes": 10**9}) is False


# ---- full scan integration with injected runner ----------------------------------------
def _make(load_plugin, tmp_path, **opts):
    options = {"config_path": str(tmp_path / "config.toml"),
               "log_path": str(tmp_path / "pwn.log"),
               "incident_path": str(tmp_path / "incidents.json"),
               "scan_every": 0}
    options.update(opts)
    (tmp_path / "config.toml").write_text('main.plugins.x.enabled = true\n')
    (tmp_path / "pwn.log").write_text("all good\n")
    p = load_plugin("doctor.py", options=options)
    p.on_loaded()
    return p


def test_scan_autofixes_and_reports(load_plugin, tmp_path):
    # Use a service-only condition (pwngrid) whose verification the runner fully controls;
    # bettercap's condition also depends on its live API, which isn't reachable in a test env.
    p = _make(load_plugin, tmp_path, autofix="safe")
    calls = []
    state = {"pwngrid_restarted": False}

    def runner(cmd):
        if cmd[:2] == ["systemctl", "is-active"]:
            if cmd[2] == "pwngrid-peer":
                return "active\n" if state["pwngrid_restarted"] else "failed\n"
            return "active\n"
        if cmd[:2] == ["systemctl", "restart"]:
            calls.append(cmd)
            if cmd[2] == "pwngrid-peer":
                state["pwngrid_restarted"] = True
            return ""
        if cmd[0] == "vcgencmd":
            return "throttled=0x0"
        if cmd[0] == "iw":
            return "Interface wlan0mon\n\t\ttype monitor\n"
        if cmd[0] == "rfkill":
            return "Soft blocked: no\n"
        if cmd[0] == "dmesg":
            return ""
        return ""

    report = p.scan(runner=runner, now=0)
    # pwngrid was down -> restarted -> re-collect shows active -> verified fixed
    assert ["systemctl", "restart", "pwngrid-peer"] in calls
    assert any(f["id"] == "pwngrid_down" and f["outcome"] == "fixed" for f in report["observed"])
    # an incident was recorded
    assert (tmp_path / "incidents.json").exists()


def test_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p._last_report = {"fixed": [], "needs_user": [{"id": "x"}], "observed": [{"id": "x"}]}
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("doctor") == "1!"
    p._last_report = {"fixed": [{"id": "y"}], "needs_user": [], "observed": [{"id": "y"}]}
    p.on_ui_update(ui)
    assert ui.get("doctor") == "healed"
    p._last_report = {"fixed": [], "needs_user": [], "observed": []}
    p.on_ui_update(ui)
    assert ui.get("doctor") == "OK"
    p.on_unload(ui)
    assert not ui.has_element("doctor")
