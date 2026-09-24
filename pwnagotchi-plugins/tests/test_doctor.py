import importlib.util
import json
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
               "incident_path": str(tmp_path / "incidents.json"),
               "checkpoint_path": str(tmp_path / "known_good.json"),
               "breaker_path": str(tmp_path / "breaker.json"), "scan_every": 0}
    options.update(opts)
    (tmp_path / "config.toml").write_text('main.plugins.x.enabled = true\n')
    (tmp_path / "pwn.log").write_text("ok\n")
    (tmp_path / "hs").mkdir(exist_ok=True)
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


# ---- known-good checkpoint / drift (v0.4) ----------------------------------------------
def test_parse_dpkg():
    text = ("Desired=... \n||/ Name  Version  Arch  Description\n"
            "ii  python3  3.13.5-1  arm64  interpreter\n"
            "ii  bettercap  2.32  arm64  net tool\n"
            "rc  oldpkg  1.0  arm64  removed\n")
    assert doc.parse_dpkg(text) == {"python3": "3.13.5-1", "bettercap": "2.32"}


def test_parse_enabled_plugins():
    cfg = ('main.plugins.gps.enabled = true\n'
           'main.plugins.doctor.enabled = true\n'
           'main.plugins.off.enabled = false\n')
    assert doc.parse_enabled_plugins(cfg) == ["doctor", "gps"]


def test_diff_fingerprint():
    old = {"config_hash": "a", "plugins": ["gps"], "kernel": "6.1", "os": "trixie",
           "packages": {"bettercap": "2.32", "python3": "3.13.4"}}
    new = {"config_hash": "b", "plugins": ["gps", "doctor"], "kernel": "6.1", "os": "trixie",
           "packages": {"bettercap": "2.32", "python3": "3.13.5", "newpkg": "1.0"}}
    d = doc.diff_fingerprint(old, new)
    assert d["config_changed"] is True
    assert d["plugins_added"] == ["doctor"] and d["plugins_removed"] == []
    assert d["packages_added"] == ["newpkg"]
    assert d["packages_changed"] == ["python3"]
    assert d["kernel_changed"] is False and d["has_changes"] is True
    # identical -> no changes
    assert doc.diff_fingerprint(old, old)["has_changes"] is False


def test_build_and_diff_checkpoint(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p._checkpoint_path = str(tmp_path / "known_good.json")

    def runner(cmd):
        if cmd[:2] == ["dpkg", "-l"]:
            return "ii  bettercap  2.32  arm64  x\nii  python3  3.13.4  arm64  y\n"
        if cmd == ["uname", "-r"]:
            return "6.1.0\n"
        return ""

    # save a known-good checkpoint
    fp = p.save_checkpoint(runner=runner)
    assert fp["packages"]["bettercap"] == "2.32"
    assert (tmp_path / "known_good.json").exists()
    # no drift yet
    assert p.diff_since_checkpoint(runner=runner)["has_changes"] is False

    # now the config changes (enable a plugin) and a package upgrades
    (tmp_path / "config.toml").write_text('main.plugins.x.enabled = true\n'
                                          'main.plugins.newone.enabled = true\n')

    def runner2(cmd):
        if cmd[:2] == ["dpkg", "-l"]:
            return "ii  bettercap  2.33  arm64  x\nii  python3  3.13.4  arm64  y\n"
        if cmd == ["uname", "-r"]:
            return "6.1.0\n"
        return ""

    d = p.diff_since_checkpoint(runner=runner2)
    assert d["has_changes"] is True
    assert d["config_changed"] is True
    assert "newone" in d["plugins_added"]
    assert "bettercap" in d["packages_changed"]


def test_diff_none_without_checkpoint(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p._checkpoint_path = str(tmp_path / "nope.json")
    assert p.diff_since_checkpoint(runner=lambda c: "") is None


# ========================================================================================
# v0.5 — "won't-work" ailment pack + safety hardening
# ========================================================================================

# ---- new pure parsers ------------------------------------------------------------------
def test_parse_default_iface():
    text = ("Iface\tDestination\tGateway\n"
            "wlan0\t00000000\t0102A8C0\n"
            "eth0\t0002A8C0\t00000000\n")
    assert doc.parse_default_iface(text) == "wlan0"
    assert doc.parse_default_iface("Iface\tDestination\neth0\t0002A8C0\n") is None


def test_parse_journal_usage():
    assert doc.parse_journal_usage("Archived and active journals take up 152.0M in the file system.") \
        == int(152.0 * 1024 ** 2)
    assert doc.parse_journal_usage("... take up 1.5G ...") == int(1.5 * 1024 ** 3)
    assert doc.parse_journal_usage("... take up 800.0K ...") == int(800.0 * 1024)
    assert doc.parse_journal_usage("nonsense") is None


def test_parse_main_iface():
    assert doc.parse_main_iface('main.iface = "wlan0mon"\n') == "wlan0mon"
    assert doc.parse_main_iface('[main]\niface = "wlan1"\n') == "wlan1"
    assert doc.parse_main_iface('nothing = 1\n') is None


def test_config_debug_level():
    assert doc.config_debug_level('main.log.level = "debug"\n') is True
    assert doc.config_debug_level('[main.log]\ndebug = true\n') is True
    assert doc.config_debug_level('main.log.level = "info"\n') is False
    assert doc.config_debug_level('a = 1\n') is False


def test_iface_mismatch_helper():
    assert doc.iface_mismatch("wlan1", ["wlan0"]) is True
    assert doc.iface_mismatch("wlan0", ["wlan0"]) is False
    assert doc.iface_mismatch("wlan0mon", ["wlan0"]) is False   # base present -> fine
    assert doc.iface_mismatch("wlan0", None) is False           # unknown -> not flagged
    assert doc.iface_mismatch(None, ["wlan0"]) is False


# ---- new condition detection -----------------------------------------------------------
def test_wpa_supplicant_hijack_detect():
    s = _clean()
    s["wpa_supplicant"] = {"running": True}
    s["monitor_present"] = False
    ids = {f["id"] for f in doc.diagnose(s)}
    assert "wpa_supplicant_hijack" in ids
    # unknown monitor state -> not flagged (unknown means unknown)
    s["monitor_present"] = None
    assert "wpa_supplicant_hijack" not in {f["id"] for f in doc.diagnose(s)}


def test_iface_mismatch_condition():
    s = _clean()
    s["iface"] = {"configured": "wlan1", "present": ["wlan0"]}
    assert "iface_mismatch" in {f["id"] for f in doc.diagnose(s)}


def test_reboot_loop_detect_and_boot_grace():
    s = _clean()
    s["service_restarts"] = {"pwnagotchi": 8}
    assert "reboot_loop" in {f["id"] for f in doc.diagnose(s)}
    # during boot grace it must not fire
    s["uptime_sec"] = 5
    assert "reboot_loop" not in {f["id"] for f in doc.diagnose(s)}


def test_journald_bloat_and_debug_level_detect():
    s = _clean()
    s["journal_bytes"] = 300 * 1024 * 1024
    s["config"] = {"valid": True, "debug": True}
    ids = {f["id"] for f in doc.diagnose(s)}
    assert "journald_bloat" in ids and "debug_log_level" in ids


# ---- safety guards ---------------------------------------------------------------------
def test_guard_wpa_not_uplink():
    assert doc.guard_wpa_not_uplink({"net": {"default_iface": "eth0"}}, {}) is True
    assert doc.guard_wpa_not_uplink({"net": {"default_iface": None}}, {}) is True
    assert doc.guard_wpa_not_uplink({"net": {"default_iface": "wlan0"}}, {}) is False


def test_guard_media_ok():
    assert doc.guard_media_ok({"dmesg": {"sd_error": 0}}, {}) is True
    assert doc.guard_media_ok({"dmesg": {}}, {}) is True
    assert doc.guard_media_ok({"dmesg": {"sd_error": 3}}, {}) is False


def test_guard_blocks_wpa_stop_when_uplink():
    fix = {"action": "stop_wpa_supplicant", "tier": "safe", "guard": "wpa_not_uplink"}
    findings = [{"id": "wpa_supplicant_hijack", "severity": "high", "confidence": "high",
                 "fix": fix, "_detect": lambda s: False, "outcome": "detected", "howto": []}]
    calls = []
    # uplink is over wlan -> blocked, action never runs
    out = doc.apply_fixes(findings, {"net": {"default_iface": "wlan0"}}, "conservative",
                          lambda c: calls.append(c), doc.CircuitBreaker(), {},
                          recollect=lambda: {})
    assert out[0]["outcome"] == "blocked_guard" and calls == []


def test_guard_allows_wpa_stop_when_safe():
    fix = {"action": "stop_wpa_supplicant", "tier": "safe", "guard": "wpa_not_uplink"}
    findings = [{"id": "wpa_supplicant_hijack", "severity": "high", "confidence": "high",
                 "fix": fix, "_detect": lambda s: s.get("monitor_present") is False,
                 "outcome": "detected", "howto": []}]
    calls = []
    out = doc.apply_fixes(findings, {"net": {"default_iface": "eth0"}, "monitor_present": False},
                          "conservative", lambda c: calls.append(c), doc.CircuitBreaker(), {},
                          recollect=lambda: {"monitor_present": True})
    assert out[0]["outcome"] == "fixed"
    assert calls == [["systemctl", "stop", "wpa_supplicant"]]


# ---- autonomy dial / dry-run / opt-out -------------------------------------------------
def _safe_finding(detect_after_fix_clear=True):
    return [{"id": "rfkill_blocked", "severity": "high", "confidence": "high",
             "fix": {"action": "rfkill_unblock", "tier": "safe"},
             "_detect": (lambda s: not detect_after_fix_clear),
             "outcome": "detected", "howto": []}]


def test_dry_run_would_fix():
    calls = []
    out = doc.apply_fixes(_safe_finding(), {}, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {}, dry_run=True)
    assert out[0]["outcome"] == "would_fix" and calls == []


def test_disable_autofix_optout():
    calls = []
    out = doc.apply_fixes(_safe_finding(), {}, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {},
                          disabled={"rfkill_blocked"})
    assert out[0]["outcome"] == "needs_user" and calls == []


def test_levels_and_policy():
    assert doc.normalize_level("safe") == "conservative"
    assert doc.normalize_level("all") == "assertive"
    assert doc.normalize_level("garbage") == "conservative"
    assert doc.normalize_level("observe") == "observe"
    assert doc.policy_allows("safe", "conservative") is True
    assert doc.policy_allows("risky", "conservative") is False
    assert doc.policy_allows("risky", "assertive") is True
    assert doc.policy_allows("safe", "observe") is False


# ---- verification truth ----------------------------------------------------------------
def test_verification_unknown_when_no_recollect():
    out = doc.apply_fixes(_safe_finding(), {}, "conservative", lambda c: None,
                          doc.CircuitBreaker(), {}, recollect=None)
    assert out[0]["outcome"] == "executed_verification_unknown"


def test_verification_unknown_when_recollect_raises():
    def boom():
        raise RuntimeError("cannot re-read")
    out = doc.apply_fixes(_safe_finding(), {}, "conservative", lambda c: None,
                          doc.CircuitBreaker(), {}, recollect=boom)
    assert out[0]["outcome"] == "executed_verification_unknown"


# ---- action registry integrity ---------------------------------------------------------
def test_actions_and_meta_in_sync():
    assert set(doc.ACTIONS) == set(doc.ACTION_META)
    for meta in doc.ACTION_META.values():
        assert meta["tier"] in ("safe", "risky")


def test_vacuum_journal_action():
    calls = []
    assert doc.act_vacuum_journal({}, lambda c: calls.append(c), {}, {"journal_keep_mb": 50})
    assert calls == [["journalctl", "--vacuum-size=50M"]]


# ---- overall status accounts for new outcomes ------------------------------------------
def test_status_counts_new_outcomes():
    assert doc.overall_status([{"severity": "high", "outcome": "blocked_guard"}]) == "ACTION_REQUIRED"
    assert doc.overall_status([{"severity": "warn", "outcome": "would_fix"}]) == "DEGRADED"
    assert doc.overall_status([{"severity": "high",
                               "outcome": "executed_verification_unknown"}]) == "ACTION_REQUIRED"


# ---- persistent circuit breaker --------------------------------------------------------
def test_breaker_snapshot_restore():
    b = doc.CircuitBreaker(max_attempts=2, window=1000)
    b.record("x", 10)
    snap = b.snapshot()
    b2 = doc.CircuitBreaker(max_attempts=2, window=1000).restore(snap)
    assert b2.allow("x", 11) is True
    b2.record("x", 11)
    assert b2.allow("x", 12) is False          # budget exhausted, restored across "reboot"


def test_breaker_persists_across_reload(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p._breaker.record("bettercap_down", 100)
    p._breaker.record("bettercap_down", 101)
    p._breaker.record("bettercap_down", 102)
    p._save_breaker()
    # a fresh instance (simulating a reboot) loads the exhausted budget
    q = _make(load_plugin, tmp_path)
    assert q._breaker.allow("bettercap_down", 103) is False


def test_on_config_changed_reloads_autonomy(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path, autofix="off")
    assert p._autofix == "off"
    p.options["autofix"] = "assertive"
    p.options["dry_run"] = True
    p.on_config_changed({})
    assert p._autofix == "assertive" and p._dry_run is True


# ========================================================================================
# v0.6-pre1 — Condition Pack runtime + Patient Chart collaboration foundation
# ========================================================================================

def _condition_pack(**overrides):
    pack = {
        "schema": "condition-pack/v1",
        "id": "system.high_memory",
        "version": "1.0.0",
        "applies_to": {"platform": ["pwnagotchi"]},
        "severity": "warn",
        "confidence": "high",
        "signals": ["system.memory.used_pct"],
        "detect": {"key": "system.memory.used_pct", "ge": 90},
        "symptom": "memory pressure is high",
        "cause": "memory use crossed the configured condition threshold",
        "howto": ["Disable unnecessary plugins or inspect memory consumers."],
        "provenance": {"source": "test"},
    }
    pack.update(overrides)
    return pack


def test_condition_expr_unknown_strict_and_boolean_tree():
    c = {"wifi.monitor.present": False, "system.memory.used_pct": 95, "roles": ["monitor", "uplink"]}
    assert doc.eval_condition_expr({"key": "wifi.monitor.present", "is": False}, c) is True
    assert doc.eval_condition_expr({"key": "missing.key", "is": False}, c) is False
    assert doc.eval_condition_expr({"key": "wifi.monitor.present", "is": 0}, c) is False
    assert doc.eval_condition_expr({"all": [
        {"key": "system.memory.used_pct", "ge": 90},
        {"key": "roles", "contains": "monitor"},
    ]}, c) is True
    assert doc.eval_condition_expr({"any": [
        {"key": "missing.key", "present": True},
        {"key": "system.memory.used_pct", "lt": 50},
    ]}, c) is False


def test_canonical_signal_binding_first_cut():
    signals = {
        "uptime_sec": 10, "mem_pct": 91, "monitor_present": True,
        "disk": {"free_mb": 123, "root_ro": False},
        "services": {"bettercap": {"active": True}},
        "service_restarts": {"bettercap": 2},
        "net": {"default_route": True, "default_iface": "eth0", "dns_ok": True},
        "config": {"valid": True, "debug": False},
        "iface": {"configured": "wlan0mon", "present": ["wlan0", "wlan0mon"]},
    }
    c = doc.canonicalize_signals(signals)
    assert c["system.memory.used_pct"] == 91
    assert c["storage.root.read_only"] is False
    assert c["service.bettercap.active"] is True
    assert c["service.bettercap.restart_count"] == 2
    assert c["network.default_route.iface"] == "eth0"
    assert c["wifi.iface.configured"] == "wlan0mon"


def test_validate_condition_pack_and_version_gate():
    pack = _condition_pack()
    assert doc.validate_condition_pack(pack) == []
    bad = dict(pack); bad["id"] = "NOT VALID"
    assert doc.validate_condition_pack(bad)
    gated = _condition_pack(applies_to={"platform": ["pwnagotchi"],
                                        "min_version": "2.9.5", "max_version": "2.9.6"})
    assert doc.pack_applies(gated, version="2.9.5.9") is True
    assert doc.pack_applies(gated, version="2.9.7") is False
    assert doc.pack_applies(gated, platform_name="beast", version="2.9.5.9") is False


def test_local_condition_pack_loader_is_explain_only_by_default(tmp_path):
    pack = _condition_pack(fix={
        "action": "wifi.rfkill_unblock",
        "tier": "safe",
        "verify": {"key": "wifi.rfkill.blocked", "is": False},
    })
    (tmp_path / "memory.json").write_text(json.dumps(pack))
    conditions, errors = doc.load_condition_packs(str(tmp_path))
    assert errors == [] and len(conditions) == 1
    assert conditions[0]["fix"] is None
    assert any("explain-only" in x for x in conditions[0]["howto"])
    findings = doc.diagnose({"mem_pct": 95}, extra_conditions=conditions)
    assert any(x["id"] == "system.high_memory" for x in findings)


def test_pack_remedy_requires_explicit_opt_in_and_existing_allowlist(tmp_path):
    pack = _condition_pack(
        id="wifi.rfkill_test",
        signals=["wifi.rfkill.blocked"],
        detect={"key": "wifi.rfkill.blocked", "is": True},
        fix={"action": "wifi.rfkill_unblock", "tier": "safe",
             "verify": {"key": "wifi.rfkill.blocked", "is": False}},
    )
    (tmp_path / "rfkill.json").write_text(json.dumps(pack))
    conditions, errors = doc.load_condition_packs(str(tmp_path), allow_remedies=True)
    assert errors == [] and conditions[0]["fix"]["action"] == "rfkill_unblock"

    pack["fix"]["action"] = "shell.run_anything"
    (tmp_path / "rfkill.json").write_text(json.dumps(pack))
    conditions, errors = doc.load_condition_packs(str(tmp_path), allow_remedies=True)
    assert errors == [] and conditions[0]["fix"] is None
    assert any("not allow-listed" in x for x in conditions[0]["howto"])


def test_pack_loader_is_bounded_and_reports_bad_files(tmp_path):
    (tmp_path / "bad.json").write_text("{nope")
    (tmp_path / "huge.json").write_text("x" * 500)
    conditions, errors = doc.load_condition_packs(str(tmp_path), max_bytes=100)
    assert conditions == []
    assert {e["file"] for e in errors} == {"bad.json", "huge.json"}


def test_patient_chart_only_writes_on_meaningful_change(tmp_path):
    chart = doc.PatientChart(str(tmp_path / "patient.json"))
    writes = []
    chart._write = lambda: writes.append("write") or True
    signals = {"services": {"pwnagotchi": {"active": True}},
               "disk": {"free_mb": 1000, "root_ro": False},
               "monitor_present": True, "net": {"default_route": True},
               "config": {"valid": True}, "log_size": 10}
    assert chart.observe(signals, [], "OK", now=1) is True
    assert chart.observe(signals, [], "OK", now=2) is False
    assert writes == ["write"]
    assert chart.data["updated_at"] == 1


def test_patient_chart_bounds_remedy_history(tmp_path):
    chart = doc.PatientChart(str(tmp_path / "patient.json"), max_remedies=10)
    chart._write = lambda: True
    signals = {"services": {"pwnagotchi": {"active": True}}}
    for i in range(15):
        finding = {"id": "x%d" % i, "outcome": "fixed", "fix": {"action": "restart_service"}}
        chart.observe(signals, [finding], "HEALED", now=i)
    assert len(chart.data["remedies"]) == 10
    assert chart.data["remedies"][0]["condition"] == "x5"
    assert chart.summary()["remedy_count"] == 10


def test_plugin_loads_local_pack_and_patient_chart(load_plugin, tmp_path):
    packs = tmp_path / "packs"; packs.mkdir()
    patient = tmp_path / "patient.json"
    (packs / "memory.json").write_text(json.dumps(_condition_pack()))
    p = load_plugin("doctor.py", options={
        "condition_dir": str(packs),
        "patient_path": str(patient),
        "breaker_path": str(tmp_path / "breaker.json"),
        "incident_path": str(tmp_path / "incidents.json"),
        "checkpoint_path": str(tmp_path / "known_good.json"),
        "config_path": str(tmp_path / "config.toml"),
        "log_path": str(tmp_path / "pwn.log"),
        "handshakes": str(tmp_path / "hs"),
        "scan_every": 0,
    })
    p.on_loaded()
    assert len(p._pack_conditions) == 1
    assert p._pack_errors == []
    assert isinstance(p._patient, doc.PatientChart) or p._patient.__class__.__name__ == "PatientChart"


# ---- pack integration hardening (Claude, on top of OpenAI v0.6-pre1) --------------------
def test_builtin_condition_wins_over_pack_with_same_id():
    # a pack tries to redefine a core id; the built-in must take precedence
    shadow = doc.condition_from_pack(_condition_pack(
        id="rfkill_blocked", severity="info", confidence="low",
        symptom="shadow attempt", detect={"key": "system.memory.used_pct", "ge": 0}))
    s = _clean(); s["rfkill_blocked"] = True
    hits = [f for f in doc.diagnose(s, extra_conditions=[shadow]) if f["id"] == "rfkill_blocked"]
    assert len(hits) == 1                      # not duplicated
    assert hits[0]["symptom"] != "shadow attempt"   # the built-in, not the pack


def test_shipped_example_pack_loads_and_detects():
    example_dir = str(ROOT / "doctor.d")
    conds, errors = doc.load_condition_packs(example_dir)
    assert errors == []
    ids = {c["id"] for c in conds}
    assert "system.memory_pressure_warn" in ids
    # it fires as an early (info) warning below the built-in low_memory (92%) threshold
    s = _clean(); s["mem_pct"] = 88
    found = {f["id"] for f in doc.diagnose(s, extra_conditions=conds)}
    assert "system.memory_pressure_warn" in found and "low_memory" not in found


# ========================================================================================
# v0.6-pre2 — tri-state verification + chronic/recurrence Patient Chart
# ========================================================================================

def test_condition_expr_tristate_truth_rules():
    c = {"a": True, "b": False}
    assert doc.eval_condition_expr_state({"key": "missing", "is": True}, c) is None
    assert doc.eval_condition_expr_state({"all": [
        {"key": "a", "is": True},
        {"key": "missing", "is": True},
    ]}, c) is None
    # False dominates unknown in AND.
    assert doc.eval_condition_expr_state({"all": [
        {"key": "b", "is": True},
        {"key": "missing", "is": True},
    ]}, c) is False
    # True dominates unknown in OR.
    assert doc.eval_condition_expr_state({"any": [
        {"key": "a", "is": True},
        {"key": "missing", "is": True},
    ]}, c) is True


def test_version_bounded_pack_does_not_apply_when_runtime_version_unknown():
    pack = _condition_pack(applies_to={
        "platform": ["pwnagotchi"], "min_version": "2.9.5", "max_version": "2.9.6"
    })
    assert doc.pack_applies(pack, version=None) is False
    assert doc.pack_applies(pack, version="unknown") is False


def _pack_fix_finding():
    # Use memory pressure for detection so the built-in rfkill condition does not also fire.
    # The remedy is intentionally synthetic: this test is about explicit pack verification.
    pack = _condition_pack(
        id="system.pack_verify_test",
        signals=["system.memory.used_pct", "wifi.rfkill.blocked"],
        detect={"key": "system.memory.used_pct", "ge": 90},
        fix={"action": "wifi.rfkill_unblock", "tier": "safe",
             "verify": {"key": "wifi.rfkill.blocked", "is": False}},
    )
    cond = doc.condition_from_pack(pack, allow_remedy=True)
    return doc.diagnose({"mem_pct": 95}, extra_conditions=[cond])


def test_pack_fix_uses_explicit_verify_expression():
    findings = _pack_fix_finding()
    calls = []
    out = doc.apply_fixes(
        findings, {"rfkill_blocked": True}, "conservative",
        lambda c: calls.append(c), doc.CircuitBreaker(), {},
        recollect=lambda: {"rfkill_blocked": False}, now=1,
    )
    hit = [f for f in out if f["id"] == "system.pack_verify_test"][0]
    assert hit["outcome"] == "fixed"
    assert calls == [["rfkill", "unblock", "wifi"]]


def test_pack_fix_verify_missing_signal_is_unknown_not_success():
    findings = _pack_fix_finding()
    out = doc.apply_fixes(
        findings, {"rfkill_blocked": True}, "conservative",
        lambda c: None, doc.CircuitBreaker(), {},
        recollect=lambda: {}, now=1,
    )
    hit = [f for f in out if f["id"] == "system.pack_verify_test"][0]
    assert hit["outcome"] == "executed_verification_unknown"


def test_pack_fix_verify_false_is_failure():
    findings = _pack_fix_finding()
    out = doc.apply_fixes(
        findings, {"rfkill_blocked": True}, "conservative",
        lambda c: None, doc.CircuitBreaker(), {},
        recollect=lambda: {"rfkill_blocked": True}, now=1,
    )
    hit = [f for f in out if f["id"] == "system.pack_verify_test"][0]
    assert hit["outcome"] == "fix_failed"


def test_patient_chart_counts_episodes_not_scans(tmp_path):
    chart = doc.PatientChart(str(tmp_path / "patient.json"))
    writes = []
    chart._write = lambda: writes.append(chart.data["updated_at"]) or True
    signals = {"services": {"pwnagotchi": {"active": True}}}
    finding = [{"id": "bettercap_down", "outcome": "needs_user", "fix": None}]

    assert chart.observe(signals, finding, "ACTION_REQUIRED", now=10) is True
    # Same unresolved episode: no new episode, no extra persistent write.
    assert chart.observe(signals, finding, "ACTION_REQUIRED", now=20) is False
    row = chart.chronic_summary("bettercap_down")
    assert row["episodes"] == 1 and row["active"] is True

    # Clear, then recur = second episode.
    assert chart.observe(signals, [], "OK", now=30) is True
    assert chart.observe(signals, finding, "ACTION_REQUIRED", now=40) is True
    row = chart.chronic_summary("bettercap_down")
    assert row["episodes"] == 2 and row["active"] is True
    assert chart.summary()["recurring_condition_count"] == 1
    assert len(writes) == 3


def test_patient_chart_tracks_verified_remedy_outcomes(tmp_path):
    chart = doc.PatientChart(str(tmp_path / "patient.json"))
    chart._write = lambda: True
    signals = {"services": {"pwnagotchi": {"active": True}}}

    fixed = [{"id": "pwngrid_down", "outcome": "fixed",
              "fix": {"action": "restart_service"}}]
    chart.observe(signals, fixed, "HEALED", now=1)
    row = chart.chronic_summary("pwngrid_down")
    assert row["episodes"] == 1
    assert row["remedy_attempts"] == 1
    assert row["remedy_successes"] == 1
    assert row["active"] is False
    assert row["last_resolved"] == 1

    failed = [{"id": "pwngrid_down", "outcome": "fix_failed",
               "fix": {"action": "restart_service"}}]
    chart.observe(signals, failed, "ACTION_REQUIRED", now=2)
    row = chart.chronic_summary("pwngrid_down")
    assert row["episodes"] == 2
    assert row["remedy_attempts"] == 2
    assert row["remedy_failures"] == 1
    assert row["active"] is True


def test_patient_chart_persists_chronic_memory_across_reload(tmp_path):
    path = tmp_path / "patient.json"
    chart = doc.PatientChart(str(path))
    signals = {"services": {"pwnagotchi": {"active": True}}}
    chart.observe(signals, [{"id": "x", "outcome": "needs_user", "fix": None}],
                  "DEGRADED", now=1)
    chart.observe(signals, [], "OK", now=2)
    chart.observe(signals, [{"id": "x", "outcome": "needs_user", "fix": None}],
                  "DEGRADED", now=3)

    restored = doc.PatientChart(str(path))
    row = restored.chronic_summary("x")
    assert row["episodes"] == 2
    assert row["active"] is True
    assert restored.summary()["recurring_condition_count"] == 1


# ---- confirm-required tier (Claude, v0.6-pre2) ------------------------------------------
def _confirm_finding():
    return [{"id": "bettercap_down", "severity": "high", "confidence": "medium",
             "fix": {"action": "restart_service", "args": {"service": "bettercap"}, "tier": "safe"},
             "_detect": lambda s: False, "outcome": "detected", "howto": []}]


def test_confirm_required_holds_action_for_approval():
    calls = []
    out = doc.apply_fixes(_confirm_finding(), {}, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {},
                          confirm={"bettercap_down"})
    assert out[0]["outcome"] == "awaiting_confirm" and calls == []


def test_confirm_required_does_not_consume_breaker():
    b = doc.CircuitBreaker(max_attempts=1, window=1000)
    doc.apply_fixes(_confirm_finding(), {}, "conservative", lambda c: None, b, {},
                    recollect=lambda: {}, confirm={"bettercap_down"})
    # a held (unconfirmed) action must not spend the attempt budget
    assert b.allow("bettercap_down", 1) is True


def test_confirm_approval_lets_action_run():
    calls = []
    # not in the confirm set for this pass -> executes and verifies
    out = doc.apply_fixes(_confirm_finding(), {}, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {}, confirm=set())
    assert out[0]["outcome"] == "fixed"
    assert calls == [["systemctl", "restart", "bettercap"]]


def test_awaiting_confirm_counts_as_remaining():
    assert doc.overall_status([{"severity": "high",
                               "outcome": "awaiting_confirm"}]) == "ACTION_REQUIRED"


def test_plugin_scan_queues_confirm_then_force_applies(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path, autofix="conservative",
              confirm_required=["pwngrid_down"])
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
        if cmd[0] == "iw":
            return "Interface wlan0mon\n\t\ttype monitor\n"
        if cmd[0] == "rfkill":
            return "Soft blocked: no\n"
        if cmd[0] == "timedatectl":
            return "yes\n"
        return ""

    # first pass: pwngrid_down is held for approval, not restarted
    res = p.scan(runner=runner, now=0)
    pg = [f for f in res["findings"] if f["id"] == "pwngrid_down"][0]
    assert pg["outcome"] == "awaiting_confirm"
    assert ["systemctl", "restart", "pwngrid-peer"] not in calls
    # approving that id forces it to run this pass
    res2 = p.scan(runner=runner, now=1, force_ids={"pwngrid_down"})
    assert ["systemctl", "restart", "pwngrid-peer"] in calls
    pg2 = [f for f in res2["findings"] if f["id"] == "pwngrid_down"][0]
    assert pg2["outcome"] == "fixed"
