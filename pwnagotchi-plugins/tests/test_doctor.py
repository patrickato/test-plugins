import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("doctor", ROOT / "doctor.py")
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)

# First-party bundled Condition Packs (migrated from Python) live beside doctor.py. Load them
# the way the plugin does so tests can diagnose over "built-ins + bundled" just like runtime.
_BUNDLED = doc.load_condition_packs(str(ROOT / "doctor_packs"), allow_remedies=True,
                                    source_class="bundled")[0]


def _diag(signals):
    """diagnose() over Python built-ins + first-party bundled packs (runtime-equivalent)."""
    return doc.diagnose(signals, extra_conditions=_BUNDLED)


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
    s = _clean(); s["rfkill_blocked"] = True   # rfkill_blocked is now a bundled pack
    f = [x for x in _diag(s) if x["id"] == "rfkill_blocked"][0]
    assert f["confidence"] == "high"


def test_new_conditions_detect():
    s = _clean()
    s["mem_pct"] = 95                       # low_memory
    s["swap_used_pct"] = 70                 # swap_thrash
    s["net"] = {"default_route": False}     # no_route
    s["handshakes"] = {"writable": False}   # handshakes_unwritable
    s["time"] = {"year_ok": True, "ntp": False}   # ntp_unsynced
    s["throttled"] = {"throttled_now": True, "undervoltage_now": False}  # throttled_now
    ids = {f["id"] for f in _diag(s)}   # low_memory/swap_thrash/no_route are now bundled packs
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
               "breaker_path": str(tmp_path / "breaker.json"),
               "patient_path": str(tmp_path / "patient.json"),
               "support_dir": str(tmp_path / "support"), "scan_every": 0}
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
    s = _clean()                                # wpa_supplicant_hijack is now a bundled pack
    s["wpa_supplicant"] = {"running": True}
    s["monitor_present"] = False
    ids = {f["id"] for f in _diag(s)}
    assert "wpa_supplicant_hijack" in ids
    # unknown monitor state -> not flagged (unknown means unknown)
    s["monitor_present"] = None
    assert "wpa_supplicant_hijack" not in {f["id"] for f in _diag(s)}


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
    ids = {f["id"] for f in _diag(s)}   # debug_log_level is now a bundled pack
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
def test_treatment_decision_trace_explains_blocked_and_success_paths():
    no_fix = [{"id": "manual", "severity": "warn", "confidence": "high",
               "fix": None, "outcome": "detected"}]
    out = doc.apply_fixes(no_fix, {}, "conservative", lambda c: None,
                          doc.CircuitBreaker(), {}, now=1)
    assert out[0]["decision"]["reason"] == "no_remedy"
    assert out[0]["decision"]["gates"][0] == {
        "gate": "remedy", "result": "blocked", "reason": "no_remedy"
    }

    dry = _safe_finding()
    out = doc.apply_fixes(dry, {"rfkill_blocked": True}, "conservative",
                          lambda c: None, doc.CircuitBreaker(), {},
                          recollect=lambda: {"rfkill_blocked": False},
                          dry_run=True, now=1)
    trace = out[0]["decision"]
    assert out[0]["outcome"] == "would_fix"
    assert trace["reason"] == "dry_run"
    assert trace["standing_order"] == "conservative"
    assert trace["action"] == "rfkill_unblock"
    assert any(g["gate"] == "mutation" and g["result"] == "skipped"
               for g in trace["gates"])

    fixed = _safe_finding()
    out = doc.apply_fixes(fixed, {"rfkill_blocked": True}, "conservative",
                          lambda c: None, doc.CircuitBreaker(), {},
                          recollect=lambda: {"rfkill_blocked": False}, now=1)
    trace = out[0]["decision"]
    assert out[0]["outcome"] == "fixed"
    assert trace["reason"] in {"verified_fixed", "condition_cleared"}
    assert trace["gates"][-1]["gate"] == "verification"
    assert trace["gates"][-1]["result"] == "passed"


def test_treatment_decision_trace_names_owner_and_safety_gates():
    denied = _safe_finding()
    out = doc.apply_fixes(denied, {}, "conservative", lambda c: None,
                          doc.CircuitBreaker(), {}, denied_actions={"rfkill_unblock"})
    assert out[0]["decision"]["reason"] == "owner_denied_action"

    held = _confirm_finding()
    out = doc.apply_fixes(held, {}, "conservative", lambda c: None,
                          doc.CircuitBreaker(), {}, confirm={"bettercap_down"})
    assert out[0]["decision"]["reason"] == "condition_requires_confirmation"

    low = _safe_finding()
    low[0]["confidence"] = "low"
    out = doc.apply_fixes(low, {}, "assertive", lambda c: None,
                          doc.CircuitBreaker(), {})
    assert out[0]["decision"]["reason"] == "low_confidence"


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


def test_condition_pack_linter_catches_expression_and_registry_problems():
    bad = _condition_pack(
        signals=["wifi.rfkill.blocked"],
        detect={"all": [{"key": "wifi.rfkill.blocked", "is": True},
                        {"key": "future.unknown.signal", "ge": 1}],
                "extra": True},
    )
    lint = doc.lint_condition_pack(bad)
    assert lint["valid"] is False
    assert any("unsupported fields" in e for e in lint["errors"])

    pack = _condition_pack(
        signals=["wifi.rfkill.blocked"],
        detect={"key": "future.unknown.signal", "is": True},
    )
    lint = doc.lint_condition_pack(pack)
    assert lint["valid"] is True
    assert any("outside the current canonical registry" in w for w in lint["warnings"])
    assert any("missing from signals" in w for w in lint["warnings"])


def test_condition_pack_simulation_is_tristate_and_non_mutating():
    pack = _condition_pack(
        id="wifi.rfkill_sim",
        signals=["wifi.rfkill.blocked"],
        detect={"key": "wifi.rfkill.blocked", "is": True},
        fix={"action": "wifi.rfkill_unblock", "tier": "safe",
             "verify": {"key": "wifi.rfkill.blocked", "is": False}},
    )

    hit = doc.simulate_condition_pack(
        pack, {"wifi.rfkill.blocked": True}, version="2.9.5.9")
    assert hit["valid"] is True
    assert hit["applies"] is True
    assert hit["detect_state"] is True
    assert hit["would_diagnose"] is True
    assert hit["verify_state"] is False
    assert hit["remedy"]["allowlisted"] is True
    assert hit["mutation_possible"] is False

    clear = doc.simulate_condition_pack(
        pack, {"wifi.rfkill.blocked": False}, version="2.9.5.9")
    assert clear["detect_state"] is False
    assert clear["would_diagnose"] is False
    assert clear["verify_state"] is True

    unknown = doc.simulate_condition_pack(pack, {}, version="2.9.5.9")
    assert unknown["detect_state"] is None
    assert unknown["verify_state"] is None
    assert unknown["mutation_possible"] is False


def test_condition_pack_simulation_respects_version_gate_without_execution():
    pack = _condition_pack(
        applies_to={"platform": ["pwnagotchi"], "min_version": "9.0.0"},
        detect={"key": "system.memory.used_pct", "ge": 90},
    )
    row = doc.simulate_condition_pack(
        pack, {"system.memory.used_pct": 99}, version="2.9.5.9")
    assert row["valid"] is True
    assert row["applies"] is False
    assert row["would_diagnose"] is False
    assert row["mutation_possible"] is False


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


def test_patient_chart_v1_migrates_losslessly_to_v2(tmp_path):
    path = tmp_path / "patient.json"
    original = {
        "schema": 1,
        "identity": {"architecture": "aarch64"},
        "known_good": {"saved_at": 10},
        "coverage": {"radio": True},
        "status": "DEGRADED",
        "chronic": {"x": {"episodes": 3, "active": True}},
        "remedies": [{"at": 9, "condition": "x", "outcome": "fixed",
                      "action": "restart_service"}],
        "updated_at": 10,
        "future_same_schema_extension": {"preserve": True},
    }
    path.write_text(json.dumps(original))

    chart = doc.PatientChart(str(path))

    assert chart.data["schema"] == 2
    assert chart.data["identity"] == original["identity"]
    assert chart.data["chronic"] == original["chronic"]
    assert chart.data["remedies"] == original["remedies"]
    assert chart.data["future_same_schema_extension"] == {"preserve": True}
    assert chart.data["migrations"][-1] == {"from": 1, "to": 2}
    assert chart.summary()["migration_count"] == 1
    persisted = json.loads(path.read_text())
    assert persisted["schema"] == 2
    assert persisted["chronic"]["x"]["episodes"] == 3


def test_patient_chart_migration_is_idempotent():
    obj = doc.PatientChart._blank()
    migrated, changed = doc.PatientChart.migrate(obj)
    assert changed is False
    assert migrated["schema"] == 2
    assert migrated["migrations"] == []


def test_older_doctor_never_overwrites_future_patient_chart(tmp_path):
    path = tmp_path / "patient.json"
    raw = {"schema": 99, "identity": {"future": True}, "opaque": {"keep": "me"}}
    path.write_text(json.dumps(raw))
    before = path.read_text()

    chart = doc.PatientChart(str(path))

    assert chart.load_error
    assert chart._write_enabled is False
    assert chart._write() is False
    chart.observe({"services": {"pwnagotchi": {"active": True}}}, [], "OK", now=1)
    assert path.read_text() == before


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
    # one user/external pack, plus the first-party bundled packs shipped beside doctor.py
    assert len(p._external_conditions) == 1
    assert "system.high_memory" in {c["id"] for c in p._external_conditions}
    assert len(p._bundled_conditions) >= len(_MIGRATED_IDS)
    assert p._pack_conditions == p._bundled_conditions + p._external_conditions
    assert p._pack_errors == []
    assert isinstance(p._patient, doc.PatientChart) or p._patient.__class__.__name__ == "PatientChart"


# ---- pack integration hardening (Claude, on top of OpenAI v0.6-pre1) --------------------
def test_builtin_condition_wins_over_pack_with_same_id():
    # a pack tries to redefine a core (still-Python) id; the built-in must take precedence.
    # overheat stays in Python (config-tunable threshold), so it's a valid built-in to shadow.
    shadow = doc.condition_from_pack(_condition_pack(
        id="overheat", severity="info", confidence="low",
        symptom="shadow attempt", detect={"key": "system.memory.used_pct", "ge": 0}))
    s = _clean(); s["temp_c"] = 99             # trips the Python overheat condition
    hits = [f for f in doc.diagnose(s, extra_conditions=[shadow]) if f["id"] == "overheat"]
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


# ========================================================================================
# v0.6-pre3 — bundled/external Condition Pack trust boundary + provenance
# ========================================================================================

def test_condition_pack_loader_records_sha_and_source_class(tmp_path):
    pack = _condition_pack()
    raw = json.dumps(pack, sort_keys=True).encode()
    path = tmp_path / "x.json"
    path.write_bytes(raw)
    conds, errors = doc.load_condition_packs(str(tmp_path), source_class="external")
    assert errors == [] and len(conds) == 1
    prov = conds[0]["provenance"]
    assert prov["source_class"] == "external"
    assert prov["source"] == "test"  # explicit pack provenance is preserved
    assert prov["sha256"] == __import__("hashlib").sha256(raw).hexdigest()


def test_bundled_pack_can_keep_existing_allowlisted_remedy(tmp_path):
    pack = _condition_pack(
        id="wifi.bundled_rfkill",
        signals=["wifi.rfkill.blocked"],
        detect={"key": "wifi.rfkill.blocked", "is": True},
        fix={"action": "wifi.rfkill_unblock", "tier": "safe",
             "verify": {"key": "wifi.rfkill.blocked", "is": False}},
    )
    (tmp_path / "bundled.json").write_text(json.dumps(pack))
    conds, errors = doc.load_condition_packs(
        str(tmp_path), allow_remedies=True, source_class="bundled")
    assert errors == [] and len(conds) == 1
    assert conds[0]["fix"]["action"] == "rfkill_unblock"
    assert conds[0]["provenance"]["source_class"] == "bundled"


def test_external_pack_same_remedy_stays_explain_only_by_default(tmp_path):
    pack = _condition_pack(
        id="wifi.external_rfkill",
        signals=["wifi.rfkill.blocked"],
        detect={"key": "wifi.rfkill.blocked", "is": True},
        fix={"action": "wifi.rfkill_unblock", "tier": "safe",
             "verify": {"key": "wifi.rfkill.blocked", "is": False}},
    )
    (tmp_path / "external.json").write_text(json.dumps(pack))
    conds, errors = doc.load_condition_packs(str(tmp_path), source_class="external")
    assert errors == [] and len(conds) == 1
    assert conds[0]["fix"] is None
    assert any("explain-only" in line for line in conds[0]["howto"])


# ---- ACTION_META-driven policy (Claude, v0.6-pre3) --------------------------------------
def _reboot_finding():
    # restore_config is a reboot-class action in ACTION_META
    return [{"id": "config_invalid", "severity": "high", "confidence": "high",
             "fix": {"action": "restore_config", "tier": "risky"},
             "_detect": lambda s: False, "outcome": "detected", "howto": []}]


def test_deny_actions_blocks_action():
    calls = []
    out = doc.apply_fixes(_safe_finding(), {}, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {},
                          denied_actions={"rfkill_unblock"})
    assert out[0]["outcome"] == "needs_user" and calls == []


def test_reboot_action_held_even_at_assertive():
    calls = []
    out = doc.apply_fixes(_reboot_finding(), {}, "assertive", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {})
    assert out[0]["outcome"] == "awaiting_confirm" and calls == []


def test_reboot_action_runs_when_allowed():
    calls = []
    out = doc.apply_fixes(_reboot_finding(), {}, "assertive", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {}, allow_reboot=True)
    # restore_config needs a backup file to succeed; without one it reports fix_failed, but the
    # point here is that it was *attempted* (not held) once reboot-class actions are allowed
    assert out[0]["outcome"] in ("fixed", "fix_failed")


def test_reboot_action_runs_when_forced():
    calls = []
    out = doc.apply_fixes(_reboot_finding(), {}, "assertive", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: {},
                          force={"config_invalid"})
    assert out[0]["outcome"] in ("fixed", "fix_failed")


def test_action_meta_needs_reboot_flags():
    assert doc.ACTION_META["restore_config"]["needs_reboot"] is True
    assert doc.ACTION_META["quarantine_plugin"]["needs_reboot"] is True
    assert doc.ACTION_META["rfkill_unblock"]["needs_reboot"] is False


# ---- built-in -> bundled Condition Pack migration (Claude, v0.6-pre3) --------------------
_MIGRATED_IDS = {"no_monitor", "no_route", "dns_broken", "sd_errors",
                 "low_memory", "swap_thrash", "debug_log_level",
                 # remedy-carrying (v0.6-final):
                 "rfkill_blocked", "sd_readonly", "wpa_supplicant_hijack",
                 "config_invalid", "handshakes_unwritable"}
# The subset that ships a remedy (bundled = trusted, so remedies are retained).
_MIGRATED_REMEDY_IDS = {"rfkill_blocked", "sd_readonly", "wpa_supplicant_hijack",
                        "config_invalid", "handshakes_unwritable"}


def test_migrated_conditions_left_python_conditions():
    python_ids = {c["id"] for c in doc.CONDITIONS}
    assert not (_MIGRATED_IDS & python_ids)   # removed from Python


def test_bundled_packs_load_as_trusted_first_party():
    ids = {c["id"] for c in _BUNDLED}
    assert _MIGRATED_IDS <= ids
    for c in _BUNDLED:
        if c["id"] in _MIGRATED_IDS:
            assert (c.get("provenance") or {}).get("source_class") == "bundled"


def test_migrated_conditions_still_detect_via_bundled():
    checks = [
        ("no_monitor", {"monitor_present": False}),
        ("no_route", {"net": {"default_route": False}}),
        ("dns_broken", {"net": {"default_route": True, "dns_ok": False}}),
        ("sd_errors", {"dmesg": {"sd_error": 2}}),
        ("low_memory", {"mem_pct": 95}),
        ("swap_thrash", {"swap_used_pct": 70}),
        ("debug_log_level", {"config": {"valid": True, "debug": True}}),
        ("rfkill_blocked", {"rfkill_blocked": True}),
        ("sd_readonly", {"disk": {"free_mb": 5000, "root_ro": True}}),
        ("wpa_supplicant_hijack", {"wpa_supplicant": {"running": True},
                                   "monitor_present": False}),
        ("config_invalid", {"config": {"valid": False}}),
        ("handshakes_unwritable", {"handshakes": {"writable": False}}),
    ]
    for cid, patch in checks:
        s = _clean()
        s.update(patch)
        assert cid in {f["id"] for f in _diag(s)}, cid


def test_plugin_loads_bundled_conditions(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    bundled_ids = {c["id"] for c in p._bundled_conditions}
    assert _MIGRATED_IDS <= bundled_ids


def test_migrated_conditions_clean_on_healthy_signals():
    # nothing migrated should fire on a clean device
    assert not (_MIGRATED_IDS & {f["id"] for f in _diag(_clean())})


# ========================================================================================
# v0.6-pre4 — compatibility fingerprint
# ========================================================================================

def test_parse_os_release():
    text = 'ID=debian\nVERSION_ID="13"\nBUILD_ID=20260924\n# comment\n'
    out = doc.parse_os_release(text)
    assert out["ID"] == "debian"
    assert out["VERSION_ID"] == "13"
    assert out["BUILD_ID"] == "20260924"


def test_compatibility_fingerprint_shape(monkeypatch):
    monkeypatch.setattr(doc.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(doc.platform, "release", lambda: "6.12-test")
    fp = doc.compatibility_fingerprint(
        'ID=debian\nVERSION_ID="13"\nIMAGE_ID=pwnagotchi-test\n'
    )
    assert fp["architecture"] == "aarch64"
    assert fp["kernel"] == "6.12-test"
    assert fp["os_id"] == "debian"
    assert fp["os_version_id"] == "13"
    assert fp["os_build_id"] == "pwnagotchi-test"
    assert "python_version" in fp
    assert "pwnagotchi_version" in fp


def test_patient_chart_identity_includes_compatibility_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(doc, "compatibility_fingerprint", lambda os_release_text=None: {
        "pwnagotchi_version": "2.9.5.9",
        "python_version": "3.13.0",
        "architecture": "aarch64",
        "kernel": "6.12",
        "os_id": "debian",
        "os_version_id": "13",
        "os_build_id": "image-x",
    })
    ident = doc.PatientChart.identity_from({"iface": {}, "services": {}})
    assert ident["pwnagotchi_version"] == "2.9.5.9"
    assert ident["python_version"] == "3.13.0"
    assert ident["os_id"] == "debian"
    assert ident["os_build_id"] == "image-x"


# ---- bundled remedy path end-to-end (Claude, v0.6-final) ---------------------------------
def _bundled_by_id(cid, *, allow_remedies=True):
    conds, _ = doc.load_condition_packs(str(ROOT / "doctor_packs"), allow_remedies=allow_remedies,
                                        source_class="bundled")
    for c in conds:
        if c["id"] == cid:
            return c
    raise AssertionError("bundled pack %s not found" % cid)


def test_bundled_remedy_packs_retain_fix_when_trusted():
    for cid in _MIGRATED_REMEDY_IDS:
        c = _bundled_by_id(cid, allow_remedies=True)
        assert isinstance(c.get("fix"), dict) and c["fix"].get("action"), cid


def test_bundled_remedy_packs_explain_only_when_external():
    # the exact same JSON, loaded as an external/user pack, must NOT carry an executable remedy
    for cid in _MIGRATED_REMEDY_IDS:
        c = _bundled_by_id(cid, allow_remedies=False)
        assert c.get("fix") is None, cid


def test_bundled_rfkill_pack_runs_and_verifies():
    cond = _bundled_by_id("rfkill_blocked")
    s = _clean(); s["rfkill_blocked"] = True
    findings = doc.diagnose(s, extra_conditions=[cond])
    calls = []
    # recollect clears the block -> fix.verify (wifi.rfkill.blocked is false) -> fixed
    fresh = _clean(); fresh["rfkill_blocked"] = False
    out = doc.apply_fixes(findings, s, "conservative", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: fresh)
    f = [x for x in out if x["id"] == "rfkill_blocked"][0]
    assert f["outcome"] == "fixed"
    assert ["rfkill", "unblock", "wifi"] in calls


def test_bundled_wpa_pack_guarded_and_verified():
    cond = _bundled_by_id("wpa_supplicant_hijack")
    s = _clean(); s["wpa_supplicant"] = {"running": True}; s["monitor_present"] = False

    # uplink is over wlan -> guard (not_uplink) blocks, action never runs
    blocked = doc.diagnose({**s, "net": {"default_iface": "wlan0"}}, extra_conditions=[cond])
    calls = []
    out = doc.apply_fixes(blocked, {**s, "net": {"default_iface": "wlan0"}}, "conservative",
                          lambda c: calls.append(c), doc.CircuitBreaker(), {}, recollect=lambda: {})
    assert out[0]["outcome"] == "blocked_guard" and calls == []

    # uplink over eth -> guard passes, stop runs, verify (monitor present) -> fixed
    safe_sig = {**s, "net": {"default_iface": "eth0"}}
    findings = doc.diagnose(safe_sig, extra_conditions=[cond])
    calls2 = []
    fresh = _clean()  # monitor_present True in _clean -> verify passes
    out2 = doc.apply_fixes(findings, safe_sig, "conservative", lambda c: calls2.append(c),
                           doc.CircuitBreaker(), {}, recollect=lambda: fresh)
    f = [x for x in out2 if x["id"] == "wpa_supplicant_hijack"][0]
    assert f["outcome"] == "fixed"
    assert ["systemctl", "stop", "wpa_supplicant"] in calls2


def test_bundled_sd_readonly_media_guard_blocks_on_failing_card():
    cond = _bundled_by_id("sd_readonly")
    # root is read-only AND the kernel reports SD I/O errors -> media_ok guard blocks remount
    s = _clean(); s["disk"] = {"free_mb": 5000, "root_ro": True}; s["dmesg"] = {"sd_error": 3}
    findings = doc.diagnose(s, extra_conditions=[cond])
    calls = []
    out = doc.apply_fixes(findings, s, "assertive", lambda c: calls.append(c),
                          doc.CircuitBreaker(), {}, recollect=lambda: s)
    assert out[0]["outcome"] == "blocked_guard" and calls == []


# ========================================================================================
# v0.7 — plain-language narrative + sanitized support bundle (Claude)
# ========================================================================================
def test_redact_text():
    t = doc.redact_text("client aa:bb:cc:dd:ee:ff at 192.168.1.5 mailed bob@example.com")
    assert "aa:bb:cc:dd:ee:ff" not in t and "<mac>" in t
    assert "192.168.1.5" not in t and "<ip>" in t
    assert "bob@example.com" not in t and "<email>" in t
    assert doc.redact_text("nothing sensitive here") == "nothing sensitive here"


def test_redact_config():
    cfg = ('main.plugins.wpa_sec.api_key = "SECRET123"\n'
           'main.plugins.doctor.enabled = true\n'
           'main.bt.mac = "aa:bb:cc:dd:ee:ff"\n'
           'main.plugins.gps.latitude = 40.1\n'
           'main.plugins.doctor.min_free_mb = 200\n')
    out = doc.redact_config(cfg)
    assert "SECRET123" not in out
    assert "40.1" not in out                       # latitude key redacted
    assert "aa:bb:cc:dd:ee:ff" not in out          # mac key redacted
    assert "main.plugins.doctor.enabled = true" in out    # benign kept
    assert "main.plugins.doctor.min_free_mb = 200" in out  # benign kept


def test_narrate_states():
    assert "healthy" in doc.narrate("OK", [])
    fixed = [{"outcome": "fixed", "symptom": "Wi-Fi soft-blocked", "severity": "high"}]
    assert "Auto-fixed" in doc.narrate("HEALED", fixed)
    remaining = [{"outcome": "needs_user", "symptom": "no monitor interface",
                  "severity": "high", "howto": ["check the adapter"]}]
    n = doc.narrate("ACTION_REQUIRED", remaining)
    assert "Needs you" in n and "no monitor interface" in n and "check the adapter" in n


def test_narrate_awaiting_and_drift():
    awaiting = [{"outcome": "awaiting_confirm", "symptom": "bettercap down", "severity": "high"}]
    n = doc.narrate("ACTION_REQUIRED", awaiting, causal=["a -> b"],
                    drift={"has_changes": True, "config_changed": True,
                           "plugins_added": ["newplug"]})
    assert "approval" in n and "Likely chain" in n
    assert "known-good checkpoint" in n and "config.toml changed" in n and "newplug" in n


def test_scan_sets_narrative(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.scan(runner=lambda c: "", now=0)
    assert isinstance(p.narrative(), str) and p.narrative()


def test_build_support_bundle_is_sanitized(load_plugin, tmp_path):
    import zipfile
    p = _make(load_plugin, tmp_path)
    # a config with a secret + a MAC-bearing key, and a log line with PII
    (tmp_path / "config.toml").write_text(
        'main.plugins.wpa_sec.api_key = "TOPSECRETKEY"\n'
        'main.plugins.doctor.enabled = true\n')
    (tmp_path / "pwn.log").write_text(
        "handshake from aa:bb:cc:dd:ee:ff on 10.0.0.9 ssid HomeNet\n")
    p._status = "DEGRADED"
    p._findings = [{"severity": "warn", "confidence": "high", "symptom": "sym",
                    "cause": "cz", "outcome": "needs_user", "howto": ["do x"]}]
    p._narrative = doc.narrate(p._status, p._findings)
    out = p.build_support_bundle()
    assert out and out.endswith(".zip") and __import__("os").path.exists(out)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "REPORT.txt" in names and "config.redacted.toml" in names
        cfg = z.read("config.redacted.toml").decode()
        assert "TOPSECRETKEY" not in cfg and "<redacted>" in cfg
        log = z.read("pwnagotchi.log.tail.redacted.txt").decode()
        assert "aa:bb:cc:dd:ee:ff" not in log and "10.0.0.9" not in log
        report = z.read("REPORT.txt").decode()
        assert "PwnDoctor support report" in report and "FINDINGS" in report


def test_support_bundle_action_via_webhook(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)

    class _Req:
        args = {"action": "support_bundle"}
    # patch scan to avoid real collectors; just exercise the action branch
    p.scan = lambda runner=None, now=None, force_ids=None: {"status": "OK", "findings": []}
    html = p.on_webhook("/", _Req())
    assert "support bundle" in html.lower()
