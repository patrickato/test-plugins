"""doctor — autonomous health scanning, diagnosis, and (safe) self-healing.

Toggle it on (or hit its web page) and the Doctor scans everything it can reach, matches it
against a knowledge base of known Pwnagotchi ailments, auto-fixes the safe/reversible ones and
gives you step-by-step instructions for the rest.

v0.3 borrows discipline from the Beastagotchi "Doctor/Explain" + Black Box design:
  * Truth rules: unknown means unknown (a missing sensor is never treated as a negative);
    a low-confidence (log-inferred) finding is never auto-fixed, only explained.
  * Evidence confidence per finding (high / medium / low) gates auto-fix.
  * Incident lifecycle: a problem OPENS an incident (with a black-box snapshot of state at that
    moment) and RESOLVES when it clears — instead of spamming a row per scan.
  * Boot uptime-gating so service-down conditions don't false-alarm during startup.
  * Causal chains ("rfkill-blocked -> no monitor -> no captures") instead of disconnected warns.
  * Field status vocabulary: OK / ATTENTION / DEGRADED / ACTION.

Everything is guarded so it works regardless of Pi model, screen, or setup. Auto-fix is tiered
and configurable, every action is allow-listed and verified, a circuit breaker stops loops.

Options (main.plugins.doctor.*):
    enabled       = true
    autofix       = "safe"     # "off" | "safe" (auto low-risk) | "all"
    scan_every    = 30         # full scan every N epochs (0 = only on start / web)
    boot_grace_s  = 25         # don't flag service-down before this many seconds of uptime
    log_path      = "/etc/pwnagotchi/log/pwnagotchi.log"
    config_path   = "/etc/pwnagotchi/config.toml"
    handshakes    = "/root/handshakes"
    incident_path = "/etc/pwnagotchi/doctor_incidents.json"
    min_free_mb   = 200
    max_temp_c    = 80
    services      = ["pwnagotchi", "bettercap", "pwngrid-peer"]
    position      = "0,0"

Requires: none (Python standard library; uses systemctl/iw/rfkill/vcgencmd/timedatectl when
present, all guarded). Auto-fix actions need root, which Pwnagotchi already runs as.
"""
import hashlib
import json
import logging
import os
import shutil
import socket
import subprocess
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_SEV_RANK = {"high": 0, "warn": 1, "info": 2}
_CONF_RANK = {"high": 0, "medium": 1, "low": 2}


# ======================================================================================
# Pure parsers (unit-tested; no I/O)
# ======================================================================================
def parse_throttled(value):
    s = str(value).strip()
    if "=" in s:
        s = s.split("=", 1)[1].strip()
    try:
        n = int(s, 16) if s.lower().startswith("0x") else int(s)
    except (TypeError, ValueError):
        return {}
    return {
        "undervoltage_now": bool(n & 0x1),
        "throttled_now": bool(n & 0x4),
        "undervoltage_occurred": bool(n & 0x10000),
        "throttled_occurred": bool(n & 0x40000),
    }


def parse_dmesg(text):
    lines = [ln.lower() for ln in (text or "").splitlines()]
    def count(pred):
        return sum(1 for ln in lines if pred(ln))
    return {
        "undervoltage": count(lambda ln: "under-voltage" in ln or "undervoltage" in ln),
        "usb_reset": count(lambda ln: "usb" in ln and "reset" in ln),
        "oom": count(lambda ln: "out of memory" in ln or "oom-kill" in ln),
        "sd_error": count(lambda ln: ("mmcblk" in ln or "mmc0" in ln) and "error" in ln),
        "wifi_fw": count(lambda ln: ("brcmfmac" in ln or "firmware" in ln)
                         and ("error" in ln or "failed" in ln or "crash" in ln)),
    }


def parse_mounts_ro(text):
    for line in (text or "").splitlines():
        f = line.split()
        if len(f) >= 4 and f[1] == "/":
            return "ro" in f[3].split(",")
    return False


def parse_meminfo(text):
    """Return {swap_used_pct} from /proc/meminfo, or {} if unparseable."""
    vals = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].rstrip(":") in ("SwapTotal", "SwapFree"):
            try:
                vals[parts[0].rstrip(":")] = float(parts[1])
            except ValueError:
                pass
    total = vals.get("SwapTotal")
    if total and total > 0:
        used = total - vals.get("SwapFree", 0)
        return {"swap_used_pct": 100.0 * used / total}
    return {"swap_used_pct": 0.0} if total == 0 else {}


def parse_default_route(text):
    """True if /proc/net/route lists a default route (Destination 00000000)."""
    for line in (text or "").splitlines()[1:]:
        f = line.split()
        if len(f) >= 2 and f[1] == "00000000":
            return True
    return False


def config_valid(text):
    try:
        import tomllib
        tomllib.loads(text)
        return {"valid": True, "error": None}
    except ModuleNotFoundError:
        try:
            import toml
            toml.loads(text)
            return {"valid": True, "error": None}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def iw_has_monitor(iw_text):
    for raw in (iw_text or "").splitlines():
        line = raw.strip()
        if line.startswith("Interface ") and line.split(None, 1)[1].endswith("mon"):
            return True
        if line.startswith("type ") and line.split(None, 1)[1] == "monitor":
            return True
    return False


def parse_log_signals(text):
    lines = (text or "").lower().splitlines()
    def count(*toks):
        return sum(1 for ln in lines if all(t in ln for t in toks))
    plugins_failed = []
    for ln in lines:
        if "error while loading" in ln:
            rest = ln.split("error while loading", 1)[1].strip()
            plugins_failed.append(rest.split()[0] if rest else "?")
    return {
        "tracebacks": count("traceback"),
        "wifi_errors": count("wifi", "error"),
        "bettercap_refused": count("bettercap", "connection refused"),
        "pwngrid_errors": count("pwngrid", "error"),
        "wpa_sec_errors": count("wpa-sec", "error"),
        "plugins_failed": plugins_failed,
    }


# ======================================================================================
# "Known-good checkpoint" fingerprint + diff (answers "what changed since it worked?")
# ======================================================================================
def parse_dpkg(text):
    """Parse `dpkg -l` into {package: version} for installed (ii) packages."""
    out = {}
    for line in (text or "").splitlines():
        if line.startswith("ii "):
            parts = line.split()
            if len(parts) >= 3:
                out[parts[1]] = parts[2]
    return out


def parse_enabled_plugins(config_text):
    """Sorted list of plugin names with enabled = true in config.toml."""
    try:
        import tomllib
        data = tomllib.loads(config_text or "")
        plugins_cfg = (data.get("main", {}) or {}).get("plugins", {}) or {}
        return sorted(n for n, o in plugins_cfg.items()
                      if isinstance(o, dict) and o.get("enabled"))
    except Exception:
        import re
        found = set()
        for m in re.finditer(r"main\.plugins\.([A-Za-z0-9_\-]+)\.enabled\s*=\s*true",
                             config_text or ""):
            found.add(m.group(1))
        return sorted(found)


def diff_fingerprint(old, new):
    """Structured diff between two known-good fingerprints."""
    old, new = old or {}, new or {}
    op, np = set(old.get("plugins", [])), set(new.get("plugins", []))
    opk, npk = old.get("packages", {}) or {}, new.get("packages", {}) or {}
    changed_pkgs = sorted(n for n in set(opk) & set(npk) if opk[n] != npk[n])
    res = {
        "config_changed": old.get("config_hash") != new.get("config_hash"),
        "plugins_added": sorted(np - op),
        "plugins_removed": sorted(op - np),
        "packages_added": sorted(set(npk) - set(opk)),
        "packages_removed": sorted(set(opk) - set(npk)),
        "packages_changed": changed_pkgs,
        "kernel_changed": old.get("kernel") != new.get("kernel"),
        "os_changed": old.get("os") != new.get("os"),
    }
    res["has_changes"] = any([
        res["config_changed"], res["plugins_added"], res["plugins_removed"],
        res["packages_added"], res["packages_removed"], res["packages_changed"],
        res["kernel_changed"], res["os_changed"]])
    return res


# ======================================================================================
# Knowledge base: conditions (signature -> confidence, cause, fix / how-to)
# confidence: high (direct structured), medium (derived), low (log-inferred; never auto-fixed)
# ======================================================================================
def _svc_down(s, name):
    svc = s.get("services", {}).get(name)
    return svc is not None and svc.get("active") is False


def _booted(s):
    return s.get("uptime_sec", 1e9) >= s.get("_cfg", {}).get("boot_grace_s", 25)


CONDITIONS = [
    {"id": "sd_readonly", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("disk", {}).get("root_ro") is True,
     "symptom": "the root filesystem is mounted read-only",
     "cause": "the SD card hit an error and Linux remounted / read-only (writes silently fail)",
     "fix": {"action": "remount_rw", "tier": "risky"},
     "howto": ["Back up now — a read-only remount usually means the SD is failing.",
               "Try: sudo mount -o remount,rw /",
               "Reflash to a fresh, good-quality SD card soon."]},

    {"id": "disk_full", "severity": "high", "confidence": "high",
     "detect": lambda s: (s.get("disk", {}).get("free_mb") is not None
                          and s["disk"]["free_mb"] < s.get("_cfg", {}).get("min_free_mb", 200)),
     "symptom": "very low free disk space",
     "cause": "the SD card is nearly full (often log bloat or too many captures)",
     "fix": {"action": "prune_logs", "tier": "safe"},
     "howto": ["Enable capture_retention to prune old captures.",
               "df -h  and  du -sh /root/handshakes  to find the hog."]},

    {"id": "log_bloat", "severity": "warn", "confidence": "high",
     "detect": lambda s: (s.get("log_size") is not None
                          and s["log_size"] > s.get("_cfg", {}).get("log_max_bytes", 5 * 1024 * 1024)),
     "symptom": "the Pwnagotchi log file is very large",
     "cause": "runaway logging is eating disk and SD write cycles",
     "fix": {"action": "prune_logs", "tier": "safe"},
     "howto": ["The Doctor can truncate it; also consider quieter log levels."]},

    {"id": "bettercap_down", "severity": "high", "confidence": "medium",
     "detect": lambda s: _booted(s) and (s.get("bettercap_reachable") is False
                          or _svc_down(s, "bettercap")
                          or s.get("log", {}).get("bettercap_refused", 0) >= 1),
     "symptom": "bettercap isn't reachable",
     "cause": "bettercap crashed or its API is down (no capturing happens without it)",
     "fix": {"action": "restart_service", "args": {"service": "bettercap"}, "tier": "safe"},
     "howto": ["sudo systemctl restart bettercap",
               "journalctl -u bettercap -n 50"]},

    {"id": "pwngrid_down", "severity": "warn", "confidence": "medium",
     "detect": lambda s: _booted(s) and (_svc_down(s, "pwngrid-peer")
                          or s.get("log", {}).get("pwngrid_errors", 0) >= 1),
     "symptom": "pwngrid-peer is unhappy",
     "cause": "the peer/grid service isn't running properly",
     "fix": {"action": "restart_service", "args": {"service": "pwngrid-peer"}, "tier": "safe"},
     "howto": ["sudo systemctl restart pwngrid-peer"]},

    {"id": "rfkill_blocked", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("rfkill_blocked") is True,
     "symptom": "Wi-Fi is soft-blocked (rfkill)",
     "cause": "the wireless radio is blocked, so nothing can be captured",
     "fix": {"action": "rfkill_unblock", "tier": "safe"},
     "howto": ["sudo rfkill unblock wifi"]},

    {"id": "no_monitor", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("monitor_present") is False,
     "symptom": "no monitor-mode interface found",
     "cause": "the adapter isn't in monitor mode or doesn't support it",
     "fix": None,
     "howto": ["Confirm your Wi-Fi adapter supports monitor mode.",
               "Check bettercap's interface (main.iface).",
               "iw dev  should list an interface of 'type monitor'."]},

    {"id": "clock_wrong", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("time", {}).get("year_ok") is False,
     "symptom": "the system clock looks wrong",
     "cause": "no RTC/NTP sync — a bad clock breaks TLS and wpa-sec uploads",
     "fix": {"action": "set_time", "tier": "safe"},
     "howto": ["sudo timedatectl set-ntp true  (needs internet)",
               "Add an RTC module, or use the auto_timezone plugin."]},

    {"id": "ntp_unsynced", "severity": "info", "confidence": "medium",
     "detect": lambda s: (s.get("time", {}).get("year_ok") is True
                          and s.get("time", {}).get("ntp") is False),
     "symptom": "clock is plausible but not NTP-synced",
     "cause": "drift can accumulate and eventually break TLS/wpa-sec",
     "fix": {"action": "set_time", "tier": "safe"},
     "howto": ["sudo timedatectl set-ntp true"]},

    {"id": "config_invalid", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("config", {}).get("valid") is False,
     "symptom": "config.toml does not parse",
     "cause": "a syntax error (a hand-edit or a plugin rewrite) — Pwnagotchi may not start",
     "fix": {"action": "restore_config", "tier": "risky"},
     "howto": ["Fix the TOML syntax in /etc/pwnagotchi/config.toml.",
               "Restore: cp /etc/pwnagotchi/config.toml.doctor.bak /etc/pwnagotchi/config.toml"]},

    {"id": "plugin_crash_loop", "severity": "high", "confidence": "low",
     "detect": lambda s: (s.get("log", {}).get("tracebacks", 0) >= 3
                          or len(s.get("log", {}).get("plugins_failed", [])) >= 1),
     "symptom": "a plugin is crashing / failed to load",
     "cause": "a third-party plugin is raising exceptions",
     "fix": {"action": "quarantine_plugin", "tier": "risky"},
     "howto": ["Find the plugin in the log ('error while loading' / traceback).",
               "Disable it: main.plugins.<name>.enabled = false, then restart pwnagotchi."]},

    {"id": "handshakes_unwritable", "severity": "warn", "confidence": "high",
     "detect": lambda s: s.get("handshakes", {}).get("writable") is False,
     "symptom": "the handshakes directory is missing or not writable",
     "cause": "captures can't be saved",
     "fix": {"action": "make_handshakes_dir", "tier": "safe"},
     "howto": ["Create it: sudo mkdir -p /root/handshakes",
               "Check bettercap.handshakes points at it."]},

    {"id": "undervoltage", "severity": "high", "confidence": "high",
     "detect": lambda s: (s.get("throttled", {}).get("undervoltage_now")
                          or s.get("throttled", {}).get("undervoltage_occurred")
                          or s.get("dmesg", {}).get("undervoltage", 0) >= 1),
     "symptom": "under-voltage detected",
     "cause": "the power supply/cable can't deliver enough current (crashes & corruption)",
     "fix": None,
     "howto": ["Use a good 5V/3A supply and a short, thick USB cable.",
               "Avoid powering from a weak hub or PC port."]},

    {"id": "throttled_now", "severity": "warn", "confidence": "high",
     "detect": lambda s: (s.get("throttled", {}).get("throttled_now")
                          and not s.get("throttled", {}).get("undervoltage_now")),
     "symptom": "the CPU is currently throttled",
     "cause": "thermal throttling under load",
     "fix": None,
     "howto": ["Add cooling (see the fan_curve plugin)."]},

    {"id": "overheat", "severity": "warn", "confidence": "high",
     "detect": lambda s: (s.get("temp_c") is not None
                          and s["temp_c"] >= s.get("_cfg", {}).get("max_temp_c", 80)),
     "symptom": "high temperature",
     "cause": "sustained load or poor cooling",
     "fix": None,
     "howto": ["Add a heatsink/fan (see fan_curve). Improve airflow."]},

    {"id": "low_memory", "severity": "warn", "confidence": "high",
     "detect": lambda s: s.get("mem_pct") is not None and s["mem_pct"] >= 92,
     "symptom": "memory is nearly exhausted",
     "cause": "too many plugins / a memory leak",
     "fix": None,
     "howto": ["Disable heavy plugins; look for a leak in the log."]},

    {"id": "swap_thrash", "severity": "warn", "confidence": "medium",
     "detect": lambda s: s.get("swap_used_pct") is not None and s["swap_used_pct"] >= 60,
     "symptom": "heavy swap usage",
     "cause": "RAM pressure is spilling to the SD card (slow + SD wear)",
     "fix": None,
     "howto": ["Reduce memory use; avoid large swap on SD."]},

    {"id": "no_route", "severity": "warn", "confidence": "high",
     "detect": lambda s: s.get("net", {}).get("default_route") is False,
     "symptom": "no default network route",
     "cause": "no uplink — uploads (wpa-sec, grid) can't reach the internet",
     "fix": None,
     "howto": ["Check bt-tether/USB/Wi-Fi uplink is connected."]},

    {"id": "dns_broken", "severity": "warn", "confidence": "medium",
     "detect": lambda s: (s.get("net", {}).get("default_route") is True
                          and s.get("net", {}).get("dns_ok") is False),
     "symptom": "DNS resolution is failing",
     "cause": "a route exists but names don't resolve",
     "fix": None,
     "howto": ["Check /etc/resolv.conf and your uplink's DNS."]},

    {"id": "sd_errors", "severity": "high", "confidence": "medium",
     "detect": lambda s: s.get("dmesg", {}).get("sd_error", 0) >= 1,
     "symptom": "SD card I/O errors in the kernel log",
     "cause": "the SD card is degrading",
     "fix": None,
     "howto": ["Back up now. Reflash to a fresh, reputable SD card.",
               "See the sd_wear plugin to track write wear."]},

    {"id": "oom", "severity": "warn", "confidence": "medium",
     "detect": lambda s: s.get("dmesg", {}).get("oom", 0) >= 1,
     "symptom": "out-of-memory kills detected",
     "cause": "something is using too much RAM",
     "fix": None,
     "howto": ["Disable heavy plugins; check for a memory leak."]},

    {"id": "usb_resets", "severity": "warn", "confidence": "low",
     "detect": lambda s: s.get("dmesg", {}).get("usb_reset", 0) >= 3,
     "symptom": "repeated USB resets",
     "cause": "flaky USB power/cable/hub (often the Wi-Fi adapter dropping)",
     "fix": None,
     "howto": ["Use a powered hub or better cable for USB adapters."]},

    {"id": "wpa_sec_errors", "severity": "info", "confidence": "low",
     "detect": lambda s: s.get("log", {}).get("wpa_sec_errors", 0) >= 1,
     "symptom": "wpa-sec upload errors",
     "cause": "the wpa-sec API key or connectivity may be wrong",
     "fix": None,
     "howto": ["Check your wpa-sec api_key and internet (see captive_portal)."]},
]

# Causal chains: when all ids present, show one human sentence instead of scattered warnings.
CHAINS = [
    {"when": {"rfkill_blocked", "no_monitor"},
     "text": "Wi-Fi is rfkill-blocked → no monitor interface → no captures."},
    {"when": {"undervoltage", "usb_resets"},
     "text": "under-voltage → USB resets → the Wi-Fi adapter keeps dropping."},
    {"when": {"sd_errors", "sd_readonly"},
     "text": "SD I/O errors → the root filesystem went read-only."},
    {"when": {"disk_full", "sd_readonly"},
     "text": "disk full → write failures → read-only remount."},
    {"when": {"no_route", "dns_broken"},
     "text": "no default route → DNS fails → uploads can't reach the internet."},
    {"when": {"no_route", "wpa_sec_errors"},
     "text": "no uplink → wpa-sec uploads fail."},
]


def build_causal(finding_ids):
    ids = set(finding_ids)
    return [c["text"] for c in CHAINS if c["when"] <= ids]


# ======================================================================================
# Diagnosis (pure over signals)
# ======================================================================================
def diagnose(signals):
    findings = []
    for c in CONDITIONS:
        try:
            hit = c["detect"](signals)
        except Exception:
            hit = False
        if hit:
            findings.append({
                "id": c["id"], "severity": c["severity"], "confidence": c["confidence"],
                "symptom": c["symptom"], "cause": c["cause"], "howto": list(c.get("howto", [])),
                "fix": c.get("fix"), "_detect": c["detect"], "outcome": "detected",
            })
    findings.sort(key=lambda f: (_SEV_RANK.get(f["severity"], 9), _CONF_RANK.get(f["confidence"], 9)))
    return findings


def overall_status(findings):
    remaining = [f for f in findings if f["outcome"] in ("needs_user", "fix_failed", "gave_up")]
    if any(f["severity"] == "high" for f in remaining):
        return "ACTION_REQUIRED"
    if any(f["severity"] == "warn" for f in remaining):
        return "DEGRADED"
    if any(f["severity"] == "info" for f in remaining):
        return "ATTENTION"
    if any(f["outcome"] == "fixed" for f in findings):
        return "HEALED"
    return "OK"


# ======================================================================================
# Remediation: allow-listed actions + circuit breaker
# ======================================================================================
def act_restart_service(args, runner, signals, ctx):
    runner(["systemctl", "restart", args["service"]])
    return True


def act_rfkill_unblock(args, runner, signals, ctx):
    runner(["rfkill", "unblock", "wifi"])
    return True


def act_set_time(args, runner, signals, ctx):
    runner(["timedatectl", "set-ntp", "true"])
    return True


def act_remount_rw(args, runner, signals, ctx):
    runner(["mount", "-o", "remount,rw", "/"])
    return True


def act_make_handshakes_dir(args, runner, signals, ctx):
    path = ctx.get("handshakes")
    if not path:
        return False
    os.makedirs(path, exist_ok=True)
    return os.access(path, os.W_OK)


def act_prune_logs(args, runner, signals, ctx):
    path = ctx.get("log_path")
    keep = int(ctx.get("log_keep_lines", 1000))
    if not path or not os.path.exists(path):
        return False
    if os.path.getsize(path) <= int(ctx.get("log_max_bytes", 5 * 1024 * 1024)):
        return False
    with open(path, "rt", errors="ignore") as fp:
        lines = fp.readlines()[-keep:]
    with open(path, "w") as fp:
        fp.writelines(lines)
    return True


def act_restore_config(args, runner, signals, ctx):
    bak = ctx.get("config_path", "") + ".doctor.bak"
    if os.path.exists(bak):
        shutil.copy2(bak, ctx["config_path"])
        return True
    return False


def act_quarantine_plugin(args, runner, signals, ctx):
    failed = signals.get("log", {}).get("plugins_failed", [])
    name = failed[0] if failed else None
    path = ctx.get("config_path")
    if not name or not path or not os.path.exists(path):
        return False
    try:
        shutil.copy2(path, path + ".doctor.bak")
        with open(path, "rt", errors="ignore") as fp:
            text = fp.read()
        key = "main.plugins.%s.enabled" % name
        lines = text.splitlines()
        replaced = False
        for i, ln in enumerate(lines):
            if ln.strip().startswith(key):
                lines[i] = "%s = false" % key
                replaced = True
        if not replaced:
            lines.append("%s = false" % key)
        with open(path, "w") as fp:
            fp.write("\n".join(lines) + "\n")
        return True
    except Exception:
        return False


ACTIONS = {
    "restart_service": act_restart_service,
    "rfkill_unblock": act_rfkill_unblock,
    "set_time": act_set_time,
    "remount_rw": act_remount_rw,
    "make_handshakes_dir": act_make_handshakes_dir,
    "prune_logs": act_prune_logs,
    "restore_config": act_restore_config,
    "quarantine_plugin": act_quarantine_plugin,
}


class CircuitBreaker:
    def __init__(self, max_attempts=3, window=3600):
        self.max_attempts = max_attempts
        self.window = window
        self._events = {}

    def allow(self, key, now):
        hist = [t for t in self._events.get(key, []) if now - t < self.window]
        self._events[key] = hist
        return len(hist) < self.max_attempts

    def record(self, key, now):
        self._events.setdefault(key, []).append(now)


def policy_allows(tier, autofix):
    if autofix == "all":
        return True
    if autofix == "safe":
        return tier == "safe"
    return False


def apply_fixes(findings, signals, autofix, runner, breaker, ctx, recollect=None, now=None):
    """Attempt allowed fixes; verify; set each finding's outcome. Returns findings.

    Truth rule: a low-confidence (log-inferred) finding is NEVER auto-fixed, only explained.
    """
    now = now if now is not None else time.time()
    for f in findings:
        fix = f.get("fix")
        if not fix:
            f["outcome"] = "needs_user"
            continue
        if f.get("confidence") == "low":            # weak evidence -> explain, never auto-act
            f["outcome"] = "needs_user"
            continue
        if not policy_allows(fix.get("tier", "risky"), autofix):
            f["outcome"] = "needs_user"
            continue
        if not breaker.allow(f["id"], now):
            f["outcome"] = "gave_up"
            continue
        breaker.record(f["id"], now)
        action = ACTIONS.get(fix["action"])
        try:
            ok = bool(action and action(fix.get("args", {}), runner, signals, ctx))
        except Exception as e:
            logging.debug("[doctor] action %s failed: %s", fix.get("action"), e)
            ok = False
        if not ok:
            f["outcome"] = "fix_failed"
            continue
        if recollect is not None:
            try:
                fresh = recollect()
                f["outcome"] = "fix_failed" if f["_detect"](fresh) else "fixed"
            except Exception:
                f["outcome"] = "fixed"
        else:
            f["outcome"] = "fixed"
    return findings


# ======================================================================================
# Plugin
# ======================================================================================
_SNAPSHOT_KEYS = ("temp_c", "mem_pct", "swap_used_pct", "disk", "throttled", "services",
                  "monitor_present", "rfkill_blocked", "bettercap_reachable", "uptime_sec")
_UI_STATUS = {"OK": "OK", "HEALED": "healed", "ATTENTION": "attn",
              "DEGRADED": "DEGR", "ACTION_REQUIRED": "ACT!"}


class Doctor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.4.0"
    __license__ = "GPL3"
    __description__ = "Autonomous health scan, diagnosis, causal explanation, self-healing and known-good drift."

    def __init__(self):
        self.options = dict()
        self._findings = []
        self._status = "OK"
        self._causal = []
        self._breaker = CircuitBreaker()
        self._open = {}          # id -> {opened_at, severity, summary, snapshot}
        self._history = []

    def on_loaded(self):
        self._autofix = str(self.options.get("autofix", "safe"))
        self._scan_every = int(self.options.get("scan_every", 30))
        self._boot_grace = float(self.options.get("boot_grace_s", 25))
        self._log_path = self.options.get("log_path", "/etc/pwnagotchi/log/pwnagotchi.log")
        self._config_path = self.options.get("config_path", "/etc/pwnagotchi/config.toml")
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._incident_path = self.options.get("incident_path",
                                               "/etc/pwnagotchi/doctor_incidents.json")
        self._checkpoint_path = self.options.get("checkpoint_path",
                                                 "/etc/pwnagotchi/doctor_known_good.json")
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._max_temp_c = float(self.options.get("max_temp_c", 80))
        self._services = list(self.options.get("services",
                              ["pwnagotchi", "bettercap", "pwngrid-peer"]))
        logging.info("[doctor] loaded v%s (autofix=%s)", self.__version__, self._autofix)

    def _ctx(self):
        return {"log_path": self._log_path, "config_path": self._config_path,
                "handshakes": self._handshakes,
                "log_max_bytes": 5 * 1024 * 1024, "log_keep_lines": 1000}

    # -- collectors (guarded) ----------------------------------------------------------
    @staticmethod
    def _run(cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=6)

    def collect(self, runner=None):
        runner = runner or self._run
        s = {"_cfg": {"min_free_mb": self._min_free_mb, "max_temp_c": self._max_temp_c,
                      "boot_grace_s": self._boot_grace, "log_max_bytes": 5 * 1024 * 1024}}

        try:
            with open("/proc/uptime") as fp:
                s["uptime_sec"] = float(fp.read().split()[0])
        except Exception:
            s["uptime_sec"] = 1e9

        services = {}
        for name in self._services:
            try:
                services[name] = {"active": runner(["systemctl", "is-active", name]).strip() == "active"}
            except subprocess.CalledProcessError as e:
                services[name] = {"active": (e.output or "").strip() == "active"}
            except Exception:
                pass
        s["services"] = services

        try:
            s["throttled"] = parse_throttled(runner(["vcgencmd", "get_throttled"]))
        except Exception:
            s["throttled"] = {}

        disk = {}
        try:
            disk["free_mb"] = int(shutil.disk_usage("/").free / (1024 * 1024))
        except Exception:
            pass
        try:
            with open("/proc/mounts") as fp:
                disk["root_ro"] = parse_mounts_ro(fp.read())
        except Exception:
            pass
        s["disk"] = disk

        try:
            s["dmesg"] = parse_dmesg(runner(["dmesg", "--ctime"]))
        except Exception:
            s["dmesg"] = {}

        try:
            with open("/proc/meminfo") as fp:
                s["swap_used_pct"] = parse_meminfo(fp.read()).get("swap_used_pct")
        except Exception:
            s["swap_used_pct"] = None

        try:
            with open(self._config_path, "rt", errors="ignore") as fp:
                s["config"] = config_valid(fp.read())
        except Exception:
            s["config"] = {"valid": True, "error": None}

        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8081/api/session", timeout=2)
            s["bettercap_reachable"] = True
        except Exception as e:
            s["bettercap_reachable"] = "401" in str(e)

        try:
            s["monitor_present"] = iw_has_monitor(runner(["iw", "dev"]))
        except Exception:
            s["monitor_present"] = None
        try:
            s["rfkill_blocked"] = "yes" in runner(["rfkill", "list", "wifi"]).lower()
        except Exception:
            s["rfkill_blocked"] = None

        ntp = None
        try:
            ntp = runner(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]).strip() == "yes"
        except Exception:
            pass
        s["time"] = {"year_ok": time.gmtime().tm_year >= 2024, "ntp": ntp}

        net = {}
        try:
            with open("/proc/net/route") as fp:
                net["default_route"] = parse_default_route(fp.read())
        except Exception:
            net["default_route"] = None
        if net.get("default_route"):
            try:
                socket.setdefaulttimeout(2)
                socket.gethostbyname("api.wpa-sec.stanev.org")
                net["dns_ok"] = True
            except Exception:
                net["dns_ok"] = False
            finally:
                socket.setdefaulttimeout(None)
        s["net"] = net

        try:
            s["temp_c"] = float(pwnagotchi.temperature())
        except Exception:
            s["temp_c"] = None
        try:
            s["mem_pct"] = float(pwnagotchi.mem_usage()) * 100
        except Exception:
            s["mem_pct"] = None

        try:
            s["handshakes"] = {"writable": os.path.isdir(self._handshakes)
                               and os.access(self._handshakes, os.W_OK)}
        except Exception:
            s["handshakes"] = {}

        try:
            s["log_size"] = os.path.getsize(self._log_path)
            with open(self._log_path, "rt", errors="ignore") as fp:
                s["log"] = parse_log_signals("".join(fp.readlines()[-400:]))
        except Exception:
            s["log"] = {}
            s["log_size"] = None

        return s

    # -- the autonomous loop -----------------------------------------------------------
    def scan(self, runner=None, now=None):
        now = now if now is not None else time.time()
        signals = self.collect(runner)
        findings = diagnose(signals)
        apply_fixes(findings, signals, self._autofix, runner or self._run,
                    self._breaker, self._ctx(),
                    recollect=(lambda: self.collect(runner)) if self._autofix != "off" else None,
                    now=now)
        self._findings = findings
        self._status = overall_status(findings)
        self._causal = build_causal(f["id"] for f in findings)
        self._update_incidents(findings, signals, now)
        if findings:
            logging.info("[doctor] %s: %d issue(s), %d auto-fixed", self._status,
                         len(findings), sum(1 for f in findings if f["outcome"] == "fixed"))
        return {"status": self._status, "findings": findings, "causal": self._causal}

    def _snapshot(self, signals):
        return {k: signals.get(k) for k in _SNAPSHOT_KEYS}

    def _update_incidents(self, findings, signals, now):
        # only unresolved problems are "open incidents"
        current = {f["id"]: f for f in findings if f["outcome"] != "fixed"}
        for fid, f in current.items():
            if fid not in self._open:
                self._open[fid] = {"opened_at": now, "severity": f["severity"],
                                   "summary": f["symptom"], "snapshot": self._snapshot(signals)}
        for fid in list(self._open):
            if fid not in current:                      # cleared -> resolve
                inc = self._open.pop(fid)
                self._history.append({"id": fid, "opened_at": inc["opened_at"],
                                      "resolved_at": now, "summary": inc["summary"]})
        self._history = self._history[-100:]
        self._persist()

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(self._incident_path), exist_ok=True)
            with open(self._incident_path, "w") as fp:
                json.dump({"open": [{"id": k, **v} for k, v in self._open.items()],
                           "recent_resolved": self._history[-30:]}, fp)
        except Exception as e:
            logging.debug("[doctor] incident persist failed: %s", e)

    # -- known-good checkpoint ("what changed since it worked?") -----------------------
    def build_fingerprint(self, runner=None):
        runner = runner or self._run
        fp = {}
        try:
            with open(self._config_path, "rt", errors="ignore") as fp_cfg:
                text = fp_cfg.read()
            fp["config_hash"] = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
            fp["plugins"] = parse_enabled_plugins(text)
        except Exception:
            pass
        try:
            fp["packages"] = parse_dpkg(runner(["dpkg", "-l"]))
        except Exception:
            fp["packages"] = {}
        try:
            fp["kernel"] = runner(["uname", "-r"]).strip()
        except Exception:
            pass
        try:
            with open("/etc/os-release") as osr:
                for line in osr:
                    if line.startswith("PRETTY_NAME="):
                        fp["os"] = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        fp["saved_at"] = time.time()
        return fp

    def save_checkpoint(self, runner=None):
        fp = self.build_fingerprint(runner)
        try:
            os.makedirs(os.path.dirname(self._checkpoint_path), exist_ok=True)
            with open(self._checkpoint_path, "w") as f:
                json.dump(fp, f)
        except Exception as e:
            logging.debug("[doctor] checkpoint save failed: %s", e)
        return fp

    def load_checkpoint(self):
        try:
            if os.path.exists(self._checkpoint_path):
                with open(self._checkpoint_path) as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def diff_since_checkpoint(self, runner=None):
        old = self.load_checkpoint()
        if not old:
            return None
        return diff_fingerprint(old, self.build_fingerprint(runner))

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.scan()

    def on_epoch(self, agent, epoch, epoch_data):
        if self._scan_every and epoch % self._scan_every == 0:
            self.scan()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("doctor", LabeledValue(color=BLACK, label="dr:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("doctor", _UI_STATUS.get(self._status, "OK"))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("doctor"):
                ui.remove_element("doctor")

    # -- web ---------------------------------------------------------------------------
    def _drift_html(self, request):
        saved = None
        try:
            if request is not None and request.args.get("action") == "save_checkpoint":
                self.save_checkpoint()
                return "<h3>Known-good checkpoint saved. ✅</h3>"
            saved = self.load_checkpoint()
        except Exception:
            pass
        if not saved:
            return ("<h3>Known good</h3><p>No checkpoint yet. "
                    "<a href='?action=save_checkpoint'>Save current state as known-good</a> "
                    "while everything works.</p>")
        d = self.diff_since_checkpoint() or {}
        if not d.get("has_changes"):
            return "<h3>Known good</h3><p>Nothing has changed since your known-good checkpoint.</p>"
        rows = []
        for label, key in (("config.toml changed", "config_changed"),
                           ("kernel changed", "kernel_changed"), ("OS changed", "os_changed")):
            if d.get(key):
                rows.append("<li>%s</li>" % label)
        for label, key in (("plugins enabled", "plugins_added"),
                           ("plugins disabled", "plugins_removed"),
                           ("packages installed", "packages_added"),
                           ("packages removed", "packages_removed"),
                           ("packages upgraded/changed", "packages_changed")):
            if d.get(key):
                rows.append("<li>%s: %s</li>" % (label, ", ".join(d[key][:20])))
        return ("<h3>Changed since known-good</h3><ul>%s</ul>"
                "<p><a href='?action=save_checkpoint'>Re-save current state as known-good</a></p>"
                % "".join(rows))

    def on_webhook(self, path, request):
        drift = self._drift_html(request)
        self.scan()
        fixed = [f for f in self._findings if f["outcome"] == "fixed"]
        need = [f for f in self._findings if f["outcome"] in ("needs_user", "fix_failed", "gave_up")]
        causal = ("<h3>Likely cause chain</h3><ul>%s</ul>"
                  % "".join("<li>%s</li>" % c for c in self._causal)) if self._causal else ""
        if not self._findings:
            body = "<p><b>OK</b> — no issues detected. 🎉</p>"
        else:
            def block(f):
                steps = "".join("<li>%s</li>" % h for h in f.get("howto", []))
                return ("<tr><td>{sev}</td><td>{conf}</td><td>{sym}</td><td>{cause}</td>"
                        "<td>{outcome}</td><td><ol>{steps}</ol></td></tr>").format(
                            sev=f["severity"], conf=f["confidence"], sym=f["symptom"],
                            cause=f["cause"], outcome=f["outcome"], steps=steps)
            body = ("<p>Status: <b>{st}</b> — auto-fixed {nf}, needs you {nn}</p>{causal}"
                    "<table border=1><tr><th>sev</th><th>confidence</th><th>symptom</th>"
                    "<th>cause</th><th>outcome</th><th>what to do</th></tr>{rows}</table>").format(
                        st=self._status, nf=len(fixed), nn=len(need), causal=causal,
                        rows="".join(block(f) for f in self._findings))
        return "<html><body><h1>Doctor</h1>{}{}</body></html>".format(body, drift)
