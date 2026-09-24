import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("doctor", ROOT / "doctor.py")
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)


# ---- pure parsers ----------------------------------------------------------------------
def test_parse_throttled():
    t = doc.parse_throttled("throttled=0x50005")
    assert t["undervoltage_now"] and t["throttled_now"]
    assert t["undervoltage_occurred"] and t["throttled_occurred"]
    assert doc.parse_throttled("garbage") == {}


def test_parse_dmesg():
    text = ("Under-voltage detected!\nusb 1-1: reset high-speed USB device\n"
            "Out of memory: Killed process\nmmcblk0: error -84\nbrcmfmac: firmware failed\n")
    d = doc.parse_dmesg(text)
    assert d["undervoltage"] == 1 and d["usb_reset"] == 1 and d["oom"] == 1
    assert d["sd_error"] == 1 and d["wifi_fw"] == 1


def test_parse_mounts_ro():
    assert doc.parse_mounts_ro("/dev/mmcblk0p2 / ext4 ro,noatime 0 0\n") is True
    assert doc.parse_mounts_ro("/dev/mmcblk0p2 / ext4 rw 0 0\n") is False


def test_parse_meminfo():
    text = "SwapTotal:  102396 kB\nSwapFree:   40000 kB\n"
    assert abs(doc.parse_meminfo(text)["swap_used_pct"] - 60.9) < 0.5
    assert doc.parse_meminfo("SwapTotal: 0 kB\n")["swap_used_pct"] == 0.0


def test_parse_default_route():
    text = ("Iface\tDestination\tGateway\n"
            "eth0\t00000000\t0102A8C0\n"
            "eth0\t0002A8C0\t00000000\n")
    assert doc.parse_default_route(text) is True
    assert doc.parse_default_route("Iface\tDestination\neth0\t0002A8C0\n") is False


def test_config_valid():
    assert doc.config_valid('a = 1\n')["valid"] is True
    assert doc.config_valid('a = = 1\n')["valid"] is False


def test_parse_log_signals():
    log = "Traceback\nTraceback\nTraceback\nerror while loading boom\nwpa-sec error 500\n"
    s = doc.parse_log_signals(log)
    assert s["tracebacks"] == 3 and s["plugins_failed"] == ["boom"] and s["wpa_sec_errors"] == 1


# ---- diagnosis + confidence ------------------------------------------------------------
def _clean():
    return {"_cfg": {"min_free_mb": 200, "max_temp_c": 80, "boot_grace_s": 25},
            "uptime_sec": 9999, "disk": {"free_mb": 5000, "root_ro": False},
            "services": {"bettercap": {"active": True}, "pwngrid-peer": {"active": True}},
            "bettercap_reachable": True, "monitor_present": True, "rfkill_blocked": False,
            "time": {"year_ok": True, "ntp": True}, "temp_c": 45, "mem_pct": 40,
            "swap_used_pct": 0, "net": {"default_route": True, "dns_ok": True},
            "throttled": {}, "dmesg": {}, "log": {}, "config": {"valid": True},
            "handshakes": {"writable": True}, "log_size": 1000}


def test_diagnose_clean():
    assert doc.diagnose(_clean()) == []


def test_findings_carry_confidence():
    s = _clean(); s["rfkill_blocked"] = True
    f = [x for x in doc.diagnose(s) if x["id"] == "rfkill_blocked"][0]
    assert f["confidence"] == "high"


def test_new_conditions_detect():
    s = _clean()
    s["mem_pct"] = 95                       # low_memory
    s["swap_used_pct"] = 70                 # swap_thrash
    s["net"] = {"default_route": False}     # no_route
    s["handshakes"] = {"writable": False}   # handshakes_unwritable
    s["time"] = {"year_ok": True, "ntp": False}   # ntp_unsynced
    s["throttled"] = {"throttled_now": True, "undervoltage_now": False}  # throttled_now
    ids = {f["id"] for f in doc.diagnose(s)}
    for e in ("low_memory", "swap_thrash", "no_route", "handshakes_unwritable",
              "ntp_unsynced", "throttled_now"):
        assert e in ids, e


def test_unknown_means_unknown():
    # sensors absent (None) must NOT be treated as failures
    s = _clean()
    s["monitor_present"] = None
    s["rfkill_blocked"] = None
    s["disk"] = {"free_mb": None, "root_ro": None}
    s["handshakes"] = {"writable": None}
    s["net"] = {"default_route": None}
    ids = {f["id"] for f in doc.diagnose(s)}
    assert not ({"no_monitor", "rfkill_blocked", "disk_full", "sd_readonly",
                 "handshakes_unwritable", "no_route"} & ids)


def test_boot_grace_gates_service_down():
    s = _clean(); s["services"]["bettercap"] = {"active": False}
    s["bettercap_reachable"] = True
    # during boot: uptime below grace -> not flagged
    s["uptime_sec"] = 5
    assert not any(f["id"] == "bettercap_down" for f in doc.diagnose(s))
    # after boot: flagged
    s["uptime_sec"] = 9999
    assert any(f["id"] == "bettercap_down" for f in doc.diagnose(s))


# ---- causal chains ---------------------------------------------------------------------
def test_build_causal():
    assert "no monitor" in " ".join(doc.build_causal({"rfkill_blocked", "no_monitor"}))
    assert doc.build_causal({"rfkill_blocked"}) == []      # needs both


# ---- status vocabulary -----------------------------------------------------------------
def test_overall_status():
    assert doc.overall_status([]) == "OK"
    assert doc.overall_status([{"severity": "high", "outcome": "fixed"}]) == "HEALED"
    assert doc.overall_status([{"severity": "info", "outcome": "needs_user"}]) == "ATTENTION"
    assert doc.overall_status([{"severity": "warn", "outcome": "needs_user"}]) == "DEGRADED"
    assert doc.overall_status([{"severity": "high", "outcome": "needs_user"}]) == "ACTION_REQUIRED"


# ---- confidence gating on auto-fix -----------------------------------------------------
def test_low_confidence_never_autofixed():
    findings = [{"id": "plugin_crash_loop", "severity": "high", "confidence": "low",
                 "fix": {"action": "quarantine_plugin", "tier": "risky"},
                 "_detect": lambda s: True, "outcome": "detected", "howto": []}]
    calls = []
    out = doc.apply_fixes(findings, {}, "all", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {})
    assert out[0]["outcome"] == "needs_user" and calls == []   # even in 'all' mode


def test_safe_fix_auto_and_verified():
    down = lambda s: s.get("services", {}).get("bettercap", {}).get("active") is False
    findings = [{"id": "bettercap_down", "severity": "high", "confidence": "medium",
                 "fix": {"action": "restart_service", "args": {"service": "bettercap"}, "tier": "safe"},
                 "_detect": down, "outcome": "detected", "howto": []}]
    calls = []
    out = doc.apply_fixes(findings, {"services": {"bettercap": {"active": False}}},
                          "safe", lambda c: calls.append(c), doc.CircuitBreaker(), {},
                          recollect=lambda: {"services": {"bettercap": {"active": True}}})
    assert out[0]["outcome"] == "fixed"
    assert calls == [["systemctl", "restart", "bettercap"]]


def test_circuit_breaker_and_policy():
    b = doc.CircuitBreaker(max_attempts=1, window=100)
    assert b.allow("x", 0)
    b.record("x", 0)
    assert b.allow("x", 1) is False
    assert doc.policy_allows("risky", "safe") is False
    assert doc.policy_allows("safe", "safe") is True
    assert doc.policy_allows("risky", "all") is True


def test_make_handshakes_dir_action(tmp_path):
    target = tmp_path / "hs"
    assert doc.act_make_handshakes_dir({}, None, {}, {"handshakes": str(target)}) is True
    assert target.is_dir()


# ---- incident lifecycle + integration --------------------------------------------------
def _make(load_plugin, tmp_path, **opts):
    options = {"config_path": str(tmp_path / "config.toml"),
               "log_path": str(tmp_path / "pwn.log"),
               "handshakes": str(tmp_path / "hs"),
               "incident_path": str(tmp_path / "incidents.json"), "scan_every": 0}
    options.update(opts)
    (tmp_path / "config.toml").write_text('main.plugins.x.enabled = true\n')
    (tmp_path / "pwn.log").write_text("ok\n")
    (tmp_path / "hs").mkdir()
    p = load_plugin("doctor.py", options=options)
    p.on_loaded()
    return p


def test_incident_open_and_resolve(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    # inject a finding directly through the incident updater
    signals = _clean()
    findings = [{"id": "rfkill_blocked", "severity": "high", "symptom": "blocked",
                 "outcome": "needs_user"}]
    p._update_incidents(findings, signals, now=100)
    assert "rfkill_blocked" in p._open
    assert p._open["rfkill_blocked"]["snapshot"]["uptime_sec"] == signals["uptime_sec"]
    # next scan the problem is gone -> resolved
    p._update_incidents([], signals, now=200)
    assert "rfkill_blocked" not in p._open
    assert any(h["id"] == "rfkill_blocked" for h in p._history)
    assert (tmp_path / "incidents.json").exists()


def test_scan_integration_autofix(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path, autofix="safe")
    calls = []
    state = {"restarted": False}

    def runner(cmd):
        if cmd[:2] == ["systemctl", "is-active"]:
            if cmd[2] == "pwngrid-peer":
                return "active\n" if state["restarted"] else "failed\n"
            return "active\n"
        if cmd[:2] == ["systemctl", "restart"]:
            calls.append(cmd)
            if cmd[2] == "pwngrid-peer":
                state["restarted"] = True
            return ""
        if cmd[0] == "vcgencmd":
            return "throttled=0x0"
        if cmd[0] == "iw":
            return "Interface wlan0mon\n\t\ttype monitor\n"
        if cmd[0] == "rfkill":
            return "Soft blocked: no\n"
        if cmd[0] == "timedatectl":
            return "yes\n"
        if cmd[0] == "dmesg":
            return ""
        return ""

    result = p.scan(runner=runner, now=0)
    assert ["systemctl", "restart", "pwngrid-peer"] in calls
    assert any(f["id"] == "pwngrid_down" and f["outcome"] == "fixed" for f in result["findings"])


def test_ui_status_vocabulary(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p.on_ui_setup(ui)
    for status, expected in (("OK", "OK"), ("HEALED", "healed"), ("ATTENTION", "attn"),
                             ("DEGRADED", "DEGR"), ("ACTION_REQUIRED", "ACT!")):
        p._status = status
        p.on_ui_update(ui)
        assert ui.get("doctor") == expected
    p.on_unload(ui)
    assert not ui.has_element("doctor")
