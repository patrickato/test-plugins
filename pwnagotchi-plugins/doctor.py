"""doctor — autonomous health scanning, diagnosis, and (safe) self-healing.

Toggle it on (or hit its web page) and the Doctor scans everything it can reach, matches it
against a knowledge base of known Pwnagotchi ailments, auto-fixes the safe/reversible ones and
gives you step-by-step instructions for the rest. It is the Pwnagotchi's "immune system":
sensing is broad, acting is narrow and gated.

Discipline borrowed from the Beastagotchi "Doctor/Explain" + Black Box design:
  * Truth rules: unknown means unknown (a missing sensor is never treated as a negative);
    a low-confidence (log-inferred) finding is never auto-fixed, only explained.
  * Evidence confidence per finding (high / medium / low) gates auto-fix.
  * Incident lifecycle: a problem OPENS an incident (with a black-box snapshot of state at that
    moment) and RESOLVES when it clears — instead of spamming a row per scan.
  * Boot uptime-gating so service-down conditions don't false-alarm during startup.
  * Causal chains ("rfkill-blocked -> no monitor -> no captures") instead of disconnected warns.
  * Field status vocabulary: OK / ATTENTION / DEGRADED / ACTION.

v0.5 hardening (from the Claude<->OpenAI collaboration):
  * Verification truth: an action that runs but can't be re-verified reports
    "executed_verification_unknown", never "fixed". Unknown stays unknown.
  * Persistent circuit breaker: attempt budgets survive a restart/reboot, so the Doctor can't
    get trapped in restart -> forget -> restart.
  * Safety guards on risky actions: it won't stop wpa_supplicant if that adapter is carrying
    your uplink, and won't remount / read-write when the SD looks like it's failing.
  * Autonomy dial (Standing Orders) the end user controls and can change at any time:
    off / observe / notify / conservative (default) / assertive, plus dry_run and a
    per-condition opt-out list. on_config_changed re-reads it live.
  * "Won't-work" ailment pack: reboot/crash-loop, wpa_supplicant hijack (+ uplink-safe stop),
    interface-name mismatch, journald bloat (+ vacuum), debug-log-level-in-production.

Everything is guarded so it works regardless of Pi model, screen, or setup. Auto-fix is tiered
and configurable, every action is allow-listed, guarded and verified, a circuit breaker stops
loops.

Options (main.plugins.doctor.*):
    enabled          = true
    autofix          = "conservative"  # off | observe | notify | conservative | assertive
                                       #   (legacy: "safe"->conservative, "all"->assertive)
    dry_run          = false           # log what it *would* do, change nothing
    disable_autofix  = []              # condition ids to never auto-fix (still explained)
    confirm_required = []              # condition ids that queue for one-tap approval instead
                                       #   of auto-fixing (outcome "awaiting_confirm"; approve
                                       #   from the web page)
    deny_actions     = []              # action names the owner forbids entirely (explain only)
    allow_reboot_actions = false       # allow reboot-class actions (restore_config,
                                       #   quarantine_plugin) to auto-run; otherwise they queue
                                       #   for confirmation even at "assertive"
    support_dir      = "/var/lib/pwnagotchi/doctor"   # where the sanitized support bundle is written
    support_log_lines = 400            # how many log lines to include (redacted) in the bundle
    scan_every       = 30              # full scan every N epochs (0 = only on start / web)
    boot_grace_s     = 25              # don't flag service-down before this many seconds uptime
    log_path         = "/etc/pwnagotchi/log/pwnagotchi.log"
    config_path      = "/etc/pwnagotchi/config.toml"
    handshakes       = "/root/handshakes"
    incident_path    = "/etc/pwnagotchi/doctor_incidents.json"
    checkpoint_path  = "/etc/pwnagotchi/doctor_known_good.json"
    breaker_path     = "/etc/pwnagotchi/doctor_breaker.json"
    min_free_mb      = 200
    max_temp_c       = 80
    journal_max_mb   = 200             # flag journald bloat above this
    journal_keep_mb  = 100             # vacuum target when trimming the journal
    restart_loop_threshold = 5         # NRestarts >= this (after boot) = crash loop
    services         = ["pwnagotchi", "bettercap", "pwngrid-peer"]
    position         = "0,0"

Requires: none (Python standard library; uses systemctl/iw/rfkill/vcgencmd/timedatectl/
journalctl when present, all guarded). Auto-fix actions need root, which Pwnagotchi runs as.
"""
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

PUBLIC_CONTRACTS = {
    "condition_pack": "condition-pack/v1",
    "patient_chart": 2,
    "doctor_status": "pwndoctor/status/v1",
    "physical_validation": "pwndoctor/physical-validation/v1",
    "health_provider": "pwndoctor/provider/v1",
}

_SEV_RANK = {"high": 0, "warn": 1, "info": 2}
_CONF_RANK = {"high": 0, "medium": 1, "low": 2}


# ======================================================================================
# Pure parsers (unit-tested; no I/O)
# ======================================================================================

def parse_os_release(text):
    """Parse /etc/os-release style KEY=VALUE lines into a small dictionary."""
    out = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key.strip()] = value
    return out


def compatibility_fingerprint(os_release_text=None):
    """Stable, privacy-light environment fingerprint for upstream compatibility work."""
    if os_release_text is None:
        try:
            with open("/etc/os-release", "rt", errors="ignore") as fp:
                os_release_text = fp.read()
        except Exception:
            os_release_text = ""
    osr = parse_os_release(os_release_text)
    return {
        "pwnagotchi_version": getattr(pwnagotchi, "__version__", None),
        "python_version": "%d.%d.%d" % tuple(sys.version_info[:3]),
        "architecture": platform.machine() or None,
        "kernel": platform.release() or None,
        "os_id": osr.get("ID"),
        "os_version_id": osr.get("VERSION_ID"),
        "os_build_id": osr.get("BUILD_ID") or osr.get("IMAGE_ID"),
    }


# --- redaction (for the sanitized support bundle) -------------------------------------
_MAC_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# config keys whose *values* are secret/location/identity and must never leave the device
_SENSITIVE_KEYS = ("password", "passwd", "secret", "token", "api_key", "apikey", "psk",
                   "ssid", "bssid", "lat", "lon", "latitude", "longitude", "gps",
                   "whitelist", "allowlist", "email", "key")


def redact_text(text):
    """Strip MACs, emails and IPv4 addresses from free text (logs, JSON)."""
    if not text:
        return text or ""
    t = _MAC_RE.sub("<mac>", text)
    t = _EMAIL_RE.sub("<email>", t)
    t = _IPV4_RE.sub("<ip>", t)
    return t


def redact_config(text):
    """Redact secret/location/identity option *values* by key name; scrub MAC/IP/email too."""
    lines = []
    for line in (text or "").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0]
            if any(tok in key.lower() for tok in _SENSITIVE_KEYS):
                lines.append(key + '= "<redacted>"')
                continue
        lines.append(redact_text(line))
    return "\n".join(lines)


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


def parse_default_iface(text):
    """Interface name that owns the default route (00000000), or None."""
    for line in (text or "").splitlines()[1:]:
        f = line.split()
        if len(f) >= 2 and f[1] == "00000000":
            return f[0]
    return None


def parse_journal_usage(text):
    """Bytes used by journald from `journalctl --disk-usage` output, or None."""
    import re
    m = re.search(r"take up\s+([\d.]+)\s*([KMGT]?)B?", text or "", re.IGNORECASE)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    mult = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    return int(num * mult.get(m.group(2).upper(), 1))


def parse_main_iface(config_text):
    """The configured main.iface value from config.toml, or None."""
    try:
        import tomllib
        data = tomllib.loads(config_text or "")
        val = (data.get("main", {}) or {}).get("iface")
        return val if isinstance(val, str) and val else None
    except Exception:
        import re
        m = re.search(r'^\s*main\.iface\s*=\s*"([^"]+)"', config_text or "", re.MULTILINE)
        return m.group(1) if m else None


def config_debug_level(config_text):
    """True if config.toml turns on debug/verbose logging (fills the SD in normal use)."""
    text = config_text or ""
    try:
        import tomllib
        data = tomllib.loads(text)
        main = data.get("main", {}) or {}
        log = main.get("log", {}) or {}
        if str(log.get("level", "")).lower() == "debug":
            return True
        if log.get("debug") is True or main.get("debug") is True or data.get("debug") is True:
            return True
        return False
    except Exception:
        import re
        if re.search(r'log\.level\s*=\s*"debug"', text, re.IGNORECASE):
            return True
        if re.search(r'(^|\.)debug\s*=\s*true', text, re.IGNORECASE | re.MULTILINE):
            return True
        return False


def iface_mismatch(configured, present):
    """True if the configured Wi-Fi interface (its base, ignoring a 'mon' suffix) is absent."""
    if not configured or present is None:
        return False
    base = configured[:-3] if configured.endswith("mon") else configured
    return base not in present and configured not in present



# ======================================================================================
# Condition Pack v1 runtime (data-only shared PwnDoctor <-> Beast contract)
# ======================================================================================
_MISSING = object()
_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,127}$")
_PACK_ACTION_ALIASES = {
    "service.restart": "restart_service",
    "wifi.rfkill_unblock": "rfkill_unblock",
    "time.enable_ntp": "set_time",
    "storage.remount_rw": "remount_rw",
    "filesystem.ensure_handshakes_dir": "make_handshakes_dir",
    "logs.prune_pwnagotchi": "prune_logs",
    "service.stop_wpa_supplicant": "stop_wpa_supplicant",
    "logs.vacuum_journal": "vacuum_journal",
    "config.restore_backup": "restore_config",
    "plugin.quarantine": "quarantine_plugin",
}
_PACK_GUARD_ALIASES = {
    "not_uplink": "wpa_not_uplink",
    "uplink.not_wlan": "wpa_not_uplink",
    "media_ok": "media_ok",
    "storage.media_ok": "media_ok",
}


def _strict_equal(left, right):
    """Schema is-operator means strict equality; bool does not silently equal int 1/0."""
    return type(left) is type(right) and left == right


def canonicalize_signals(signals):
    """Flatten collector output into the first shared canonical namespace cut."""
    s = signals or {}
    disk = s.get("disk", {}) or {}
    throttled = s.get("throttled", {}) or {}
    dmesg = s.get("dmesg", {}) or {}
    net = s.get("net", {}) or {}
    cfg = s.get("config", {}) or {}
    iface = s.get("iface", {}) or {}
    hs = s.get("handshakes", {}) or {}
    wpa = s.get("wpa_supplicant", {}) or {}
    out = {
        "system.uptime_sec": s.get("uptime_sec"),
        "system.memory.used_pct": s.get("mem_pct"),
        "system.swap.used_pct": s.get("swap_used_pct"),
        "system.temp.cpu_c": s.get("temp_c"),
        "storage.root.free_mb": disk.get("free_mb"),
        "storage.root.read_only": disk.get("root_ro"),
        "storage.sd.io_error_count": dmesg.get("sd_error"),
        "power.undervoltage.current": throttled.get("undervoltage_now"),
        "power.undervoltage.occurred": throttled.get("undervoltage_occurred"),
        "power.throttled.current": throttled.get("throttled_now"),
        "wifi.monitor.present": s.get("monitor_present"),
        "wifi.rfkill.blocked": s.get("rfkill_blocked"),
        "wifi.wpa_supplicant.running": wpa.get("running"),
        "wifi.iface.configured": iface.get("configured"),
        "wifi.iface.present": iface.get("present"),
        "network.default_route.present": net.get("default_route"),
        "network.default_route.iface": net.get("default_iface"),
        "network.dns.ok": net.get("dns_ok"),
        "pwnagotchi.config.valid": cfg.get("valid"),
        "pwnagotchi.config.debug": cfg.get("debug"),
        "pwnagotchi.handshakes.writable": hs.get("writable"),
        "pwnagotchi.bettercap.reachable": s.get("bettercap_reachable"),
        "system.journal.bytes": s.get("journal_bytes"),
    }
    provider = s.get("_provider_canonical", {}) or {}
    if isinstance(provider, dict):
        for key, value in provider.items():
            if value is not None and canonical_key_known(key) and out.get(key) is None:
                out[key] = value

    for name, row in (s.get("services", {}) or {}).items():
        if isinstance(row, dict):
            out["service.%s.active" % name] = row.get("active")
    for name, count in (s.get("service_restarts", {}) or {}).items():
        out["service.%s.restart_count" % name] = count
    return {k: v for k, v in out.items() if v is not None}


def load_health_provider_snapshots(directory, *, now=None, max_files=64,
                                   max_bytes=128 * 1024, max_age_s=300):
    """Load bounded, fresh, read-only specialist snapshots from tmpfs.

    Provider snapshots may add canonical evidence and explain-only findings. They cannot
    provide remedies/actions.
    """
    now = float(time.time() if now is None else now)
    canonical, findings, evidence_meta, providers, errors = {}, [], {}, [], []
    if not directory or not os.path.isdir(directory):
        return canonical, findings, evidence_meta, providers, errors
    try:
        names = sorted(x for x in os.listdir(directory) if x.lower().endswith(".json"))
    except Exception as exc:
        return {}, [], {}, [], [{"file": str(directory), "error": "list failed: %s" % exc}]
    for name in names[:max_files]:
        path = os.path.join(directory, name)
        try:
            if os.path.getsize(path) > max_bytes:
                raise ValueError("provider snapshot exceeds %d byte limit" % max_bytes)
            with open(path, "rt", encoding="utf-8") as fp:
                obj = json.load(fp)
            if not isinstance(obj, dict) or obj.get("schema") != PUBLIC_CONTRACTS["health_provider"]:
                raise ValueError("schema must be %s" % PUBLIC_CONTRACTS["health_provider"])
            provider_id = obj.get("id")
            if not isinstance(provider_id, str) or not _PACK_ID_RE.fullmatch(provider_id):
                raise ValueError("provider id must be a lowercase namespaced identifier")
            observed_at = float(obj.get("observed_at"))
            age = now - observed_at
            if age < 0 or age > float(max_age_s):
                raise ValueError("provider snapshot stale or future-dated (age=%.1fs)" % age)

            accepted = 0
            for key, value in (obj.get("signals") or {}).items():
                if not canonical_key_known(key):
                    continue
                if key not in canonical:
                    canonical[key] = value
                    evidence_meta[key] = {
                        "observed_at": observed_at,
                        "provider": provider_id,
                    }
                    accepted += 1

            for row in obj.get("findings") or []:
                if not isinstance(row, dict):
                    continue
                fid = row.get("id")
                if not isinstance(fid, str) or not _PACK_ID_RE.fullmatch(fid):
                    continue
                severity = row.get("severity", "info")
                confidence = row.get("confidence", "medium")
                if severity not in ("high", "warn", "info") or confidence not in ("high", "medium", "low"):
                    continue
                findings.append({
                    "id": fid,
                    "severity": severity,
                    "confidence": confidence,
                    "symptom": str(row.get("symptom") or "specialist finding")[:240],
                    "cause": str(row.get("cause") or "")[:500],
                    "howto": [str(x)[:500] for x in (row.get("howto") or [])[:20]],
                    "fix": None,
                    "_detect": lambda s: True,
                    "_verify_state": None,
                    "provenance": {
                        "source_class": "provider",
                        "source": provider_id,
                        "observed_at": observed_at,
                    },
                    "outcome": "detected",
                })
            providers.append({
                "id": provider_id,
                "observed_at": observed_at,
                "age_s": age,
                "signal_count": accepted,
                "finding_count": len(obj.get("findings") or []),
            })
        except Exception as exc:
            errors.append({"file": name, "error": str(exc)[:240]})
    if len(names) > max_files:
        errors.append({"file": str(directory),
                       "error": "provider count exceeds %d; extras ignored" % max_files})
    return canonical, findings, evidence_meta, providers, errors


def merge_provider_findings(findings, provider_findings):
    """Append explain-only specialist findings without shadowing core/pack ids."""
    out = list(findings or [])
    seen = {row.get("id") for row in out}
    for row in provider_findings or []:
        if row.get("id") not in seen:
            out.append(row)
            seen.add(row.get("id"))
    out.sort(key=lambda f: (_SEV_RANK.get(f.get("severity"), 9),
                            _CONF_RANK.get(f.get("confidence"), 9)))
    return out


def eval_condition_expr_state(expr, canonical):
    """Tri-state evaluator: True / False / None (unknown).

    Detection treats unknown as a non-match. Verification keeps unknown distinct so a missing
    post-action signal can never become a false success or false failure.
    """
    if not isinstance(expr, dict):
        return None
    if "all" in expr:
        rows = expr.get("all")
        if not isinstance(rows, list) or not rows:
            return None
        states = [eval_condition_expr_state(x, canonical) for x in rows]
        if any(x is False for x in states):
            return False
        if any(x is None for x in states):
            return None
        return True
    if "any" in expr:
        rows = expr.get("any")
        if not isinstance(rows, list) or not rows:
            return None
        states = [eval_condition_expr_state(x, canonical) for x in rows]
        if any(x is True for x in states):
            return True
        if any(x is None for x in states):
            return None
        return False

    key = expr.get("key")
    if not isinstance(key, str) or not key:
        return None
    value = canonical.get(key, _MISSING)
    if value is _MISSING or value is None:
        return None

    if "present" in expr:
        return bool(expr.get("present")) is True
    if "is" in expr:
        return _strict_equal(value, expr.get("is"))
    if "contains" in expr:
        needle = expr.get("contains")
        try:
            return needle in value
        except (TypeError, ValueError):
            return None
    for op, fn in (
        ("ge", lambda a, b: a >= b),
        ("gt", lambda a, b: a > b),
        ("le", lambda a, b: a <= b),
        ("lt", lambda a, b: a < b),
    ):
        if op in expr:
            try:
                return bool(fn(value, expr.get(op)))
            except (TypeError, ValueError):
                return None
    return None


def eval_condition_expr(expr, canonical):
    """Detection helper: only a proven True matches; False and unknown do not."""
    return eval_condition_expr_state(expr, canonical) is True

def validate_condition_pack(pack):
    """Return schema errors; empty means structurally loadable."""
    errors = []
    if not isinstance(pack, dict):
        return ["pack must be a JSON object"]
    if pack.get("schema") != PUBLIC_CONTRACTS["condition_pack"]:
        errors.append("schema must be %s" % PUBLIC_CONTRACTS["condition_pack"])
    pid = pack.get("id")
    if not isinstance(pid, str) or not _PACK_ID_RE.fullmatch(pid):
        errors.append("id must be a lowercase namespaced identifier")
    if pack.get("severity") not in ("high", "warn", "info"):
        errors.append("severity must be high|warn|info")
    if pack.get("confidence") not in ("high", "medium", "low"):
        errors.append("confidence must be high|medium|low")
    if not isinstance(pack.get("detect"), dict):
        errors.append("detect must be an expression object")
    if not isinstance(pack.get("symptom"), str) or not pack.get("symptom"):
        errors.append("symptom is required")
    if not isinstance(pack.get("cause"), str):
        errors.append("cause must be a string")
    howto = pack.get("howto", [])
    if not isinstance(howto, list) or any(not isinstance(x, str) for x in howto):
        errors.append("howto must be a list of strings")
    fix = pack.get("fix")
    if fix is not None and (not isinstance(fix, dict) or not isinstance(fix.get("action"), str)):
        errors.append("fix.action must be a string when fix is present")
    return errors


_CANONICAL_STATIC_KEYS = frozenset({
    "system.uptime_sec", "system.memory.used_pct", "system.swap.used_pct",
    "system.temp.cpu_c", "storage.root.free_mb", "storage.root.read_only",
    "storage.sd.io_error_count", "power.undervoltage.current",
    "power.undervoltage.occurred", "power.throttled.current",
    "wifi.monitor.present", "wifi.rfkill.blocked", "wifi.wpa_supplicant.running",
    "wifi.iface.configured", "wifi.iface.present", "network.default_route.present",
    "network.default_route.iface", "network.dns.ok", "pwnagotchi.config.valid",
    "pwnagotchi.config.debug", "pwnagotchi.handshakes.writable",
    "pwnagotchi.bettercap.reachable", "system.journal.bytes",
})
_EXPR_COMPARE_OPS = frozenset({"is", "present", "contains", "ge", "gt", "le", "lt"})


def canonical_key_known(key):
    if key in _CANONICAL_STATIC_KEYS:
        return True
    return bool(re.fullmatch(r"service\.[a-zA-Z0-9_.-]+\.(?:active|restart_count)", str(key or "")))


def _lint_expr(expr, path="expr"):
    errors, keys = [], []
    if not isinstance(expr, dict):
        return ["%s must be an expression object" % path], keys

    branch_ops = [name for name in ("all", "any") if name in expr]
    if branch_ops:
        if len(branch_ops) != 1 or "key" in expr:
            errors.append("%s must use exactly one of all|any|key" % path)
            return errors, keys
        op = branch_ops[0]
        rows = expr.get(op)
        if not isinstance(rows, list) or not rows:
            errors.append("%s.%s must be a non-empty list" % (path, op))
            return errors, keys
        for i, row in enumerate(rows):
            sub_errors, sub_keys = _lint_expr(row, "%s.%s[%d]" % (path, op, i))
            errors.extend(sub_errors)
            keys.extend(sub_keys)
        unknown_fields = set(expr) - {op}
        if unknown_fields:
            errors.append("%s has unsupported fields: %s" %
                          (path, ", ".join(sorted(unknown_fields))))
        return errors, keys

    key = expr.get("key")
    if not isinstance(key, str) or not key:
        errors.append("%s.key must be a non-empty string" % path)
        return errors, keys
    keys.append(key)
    compare_ops = [name for name in _EXPR_COMPARE_OPS if name in expr]
    if len(compare_ops) != 1:
        errors.append("%s must contain exactly one comparison operator" % path)
    allowed = {"key"} | _EXPR_COMPARE_OPS
    unknown_fields = set(expr) - allowed
    if unknown_fields:
        errors.append("%s has unsupported fields: %s" %
                      (path, ", ".join(sorted(unknown_fields))))
    return errors, keys


def inspect_pack_provenance(pack, *, actual_sha256=None, expected_sha256=None,
                            signature_verified=None):
    """Describe provenance evidence without granting treatment authority.

    Cryptographic verification is intentionally supplied by a future catalog/verifier layer.
    This function only normalizes identity/hash/signature evidence.
    """
    provenance = pack.get("provenance") if isinstance(pack, dict) else None
    provenance = provenance if isinstance(provenance, dict) else {}
    signature = provenance.get("signature")
    if signature_verified is True:
        signature_status = "verified"
    elif signature_verified is False:
        signature_status = "invalid"
    elif signature:
        signature_status = "unverified"
    else:
        signature_status = "absent"

    hash_match = None
    if expected_sha256 is not None and actual_sha256 is not None:
        hash_match = str(expected_sha256).lower() == str(actual_sha256).lower()

    return {
        "publisher": provenance.get("publisher") or provenance.get("author"),
        "key_id": provenance.get("key_id"),
        "signature_algorithm": provenance.get("signature_algorithm") or provenance.get("alg"),
        "signature_status": signature_status,
        "content_sha256": actual_sha256,
        "expected_sha256": expected_sha256,
        "hash_match": hash_match,
        "authority_delta": "none",
    }


def evaluate_evidence_freshness(pack, evidence_meta, *, now=None):
    """Evaluate optional pack evidence-age requirements as true/false/unknown."""
    rule = pack.get("evidence") if isinstance(pack, dict) else None
    if not isinstance(rule, dict) or "max_age_s" not in rule:
        return {
            "required": False, "state": True, "fresh_keys": [],
            "stale_keys": [], "unknown_keys": [],
        }
    try:
        max_age = float(rule.get("max_age_s"))
    except (TypeError, ValueError):
        return {
            "required": True, "state": None, "fresh_keys": [],
            "stale_keys": [], "unknown_keys": ["<invalid-max-age>"],
        }
    now = float(time.time() if now is None else now)
    keys = rule.get("required_fresh")
    if not isinstance(keys, list) or not keys:
        lint = lint_condition_pack(pack)
        keys = lint.get("referenced_keys") or []
    meta = evidence_meta if isinstance(evidence_meta, dict) else {}
    fresh, stale, unknown = [], [], []
    for key in keys:
        row = meta.get(key)
        observed_at = row.get("observed_at") if isinstance(row, dict) else None
        try:
            age = now - float(observed_at)
        except (TypeError, ValueError):
            unknown.append(key)
            continue
        if age < 0 or age > max_age:
            stale.append(key)
        else:
            fresh.append(key)
    state = False if stale else (None if unknown else True)
    return {
        "required": True,
        "state": state,
        "max_age_s": max_age,
        "fresh_keys": sorted(fresh),
        "stale_keys": sorted(stale),
        "unknown_keys": sorted(unknown),
    }


def lint_condition_pack(pack):
    """Deep offline lint. Returns structured errors/warnings; never executes a remedy."""
    errors = list(validate_condition_pack(pack))
    warnings = []
    referenced = []

    if isinstance(pack, dict):
        detect = pack.get("detect")
        if isinstance(detect, dict):
            expr_errors, expr_keys = _lint_expr(detect, "detect")
            errors.extend(expr_errors)
            referenced.extend(expr_keys)

        fix = pack.get("fix")
        if isinstance(fix, dict):
            verify = fix.get("verify")
            if verify is None:
                warnings.append("fix has no explicit verify expression")
            elif isinstance(verify, dict):
                expr_errors, expr_keys = _lint_expr(verify, "fix.verify")
                errors.extend(expr_errors)
                referenced.extend(expr_keys)
            else:
                errors.append("fix.verify must be an expression object when present")

            raw_action = fix.get("action")
            mapped_action = _PACK_ACTION_ALIASES.get(raw_action, raw_action)
            if mapped_action not in globals().get("ACTIONS", {}):
                warnings.append("fix action is not in this Doctor's allow-list: %s" % raw_action)

            raw_guard = fix.get("guard")
            if raw_guard:
                mapped_guard = _PACK_GUARD_ALIASES.get(raw_guard, raw_guard)
                if mapped_guard not in globals().get("GUARDS", {}):
                    warnings.append("fix guard is unknown to this Doctor: %s" % raw_guard)

        provenance = pack.get("provenance")
        if provenance is not None and not isinstance(provenance, dict):
            errors.append("provenance must be an object when present")
        elif isinstance(provenance, dict) and provenance.get("signature"):
            if not (provenance.get("publisher") or provenance.get("author")):
                warnings.append("signed provenance has no publisher/author identity")
            if not provenance.get("key_id"):
                warnings.append("signed provenance has no key_id")
            if not (provenance.get("signature_algorithm") or provenance.get("alg")):
                warnings.append("signed provenance has no signature_algorithm")

        evidence = pack.get("evidence")
        if evidence is not None:
            if not isinstance(evidence, dict):
                errors.append("evidence must be an object when present")
            else:
                try:
                    max_age = float(evidence.get("max_age_s"))
                    if max_age <= 0:
                        raise ValueError()
                except (TypeError, ValueError):
                    errors.append("evidence.max_age_s must be a positive number")
                required_fresh = evidence.get("required_fresh", [])
                if required_fresh is not None and (
                    not isinstance(required_fresh, list) or
                    any(not isinstance(x, str) for x in required_fresh)
                ):
                    errors.append("evidence.required_fresh must be a list of canonical-key strings")

        declared = pack.get("signals", [])
        if declared is None:
            declared = []
        if not isinstance(declared, list) or any(not isinstance(x, str) for x in declared):
            errors.append("signals must be a list of canonical-key strings")
            declared = []
        referenced_unique = sorted(set(referenced))
        declared_unique = sorted(set(declared))
        missing_declarations = sorted(set(referenced_unique) - set(declared_unique))
        unused_declarations = sorted(set(declared_unique) - set(referenced_unique))
        if missing_declarations:
            warnings.append("referenced keys missing from signals: %s" %
                            ", ".join(missing_declarations))
        if unused_declarations:
            warnings.append("declared signals not referenced by detect/verify: %s" %
                            ", ".join(unused_declarations))
        unknown_keys = sorted(k for k in set(referenced_unique) if not canonical_key_known(k))
        if unknown_keys:
            warnings.append("keys outside the current canonical registry: %s" %
                            ", ".join(unknown_keys))
    else:
        referenced_unique, declared_unique = [], []

    # Stable de-duplication keeps CLI/UI output deterministic.
    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "referenced_keys": referenced_unique,
        "declared_signals": declared_unique,
    }


def simulate_condition_pack(pack, canonical_signals, *, platform_name="pwnagotchi",
                            version=None, evidence_meta=None, now=None):
    """Pure/dry Condition Pack replay against canonical signals.

    This intentionally has no runner/action parameter and cannot mutate the device.
    """
    lint = lint_condition_pack(pack)
    result = {
        "valid": lint["valid"],
        "errors": list(lint["errors"]),
        "warnings": list(lint["warnings"]),
        "referenced_keys": list(lint["referenced_keys"]),
        "applies": False,
        "detect_state": None,
        "verify_state": None,
        "would_diagnose": False,
        "remedy": {
            "declared": False,
            "action": None,
            "mapped_action": None,
            "allowlisted": False,
            "guard": None,
            "guard_known": True,
        },
        "freshness": {"required": False, "state": True, "fresh_keys": [],
                      "stale_keys": [], "unknown_keys": []},
        "provenance": inspect_pack_provenance(pack),
        "mutation_possible": False,
    }
    if not lint["valid"]:
        return result

    result["applies"] = pack_applies(
        pack, platform_name=platform_name, version=version
    )
    if not result["applies"]:
        return result

    canonical = dict(canonical_signals or {})
    freshness = evaluate_evidence_freshness(pack, evidence_meta, now=now)
    result["freshness"] = freshness
    result["detect_state"] = eval_condition_expr_state(pack.get("detect"), canonical)
    result["would_diagnose"] = (
        result["detect_state"] is True and
        (not freshness.get("required") or freshness.get("state") is True)
    )

    fix = pack.get("fix")
    if isinstance(fix, dict):
        raw_action = fix.get("action")
        mapped_action = _PACK_ACTION_ALIASES.get(raw_action, raw_action)
        raw_guard = fix.get("guard")
        mapped_guard = _PACK_GUARD_ALIASES.get(raw_guard, raw_guard) if raw_guard else None
        result["remedy"] = {
            "declared": True,
            "action": raw_action,
            "mapped_action": mapped_action,
            "allowlisted": mapped_action in globals().get("ACTIONS", {}),
            "guard": raw_guard,
            "guard_known": (not raw_guard or mapped_guard in globals().get("GUARDS", {})),
        }
        verify = fix.get("verify")
        if isinstance(verify, dict):
            result["verify_state"] = eval_condition_expr_state(verify, canonical)

    # Explicit invariant for callers/tests: this API never executes anything.
    result["mutation_possible"] = False
    return result


def _version_key(value):
    if not value:
        return None
    nums = [int(x) for x in re.findall(r"\d+", str(value))[:8]]
    return tuple(nums) if nums else None


def pack_applies(pack, *, platform_name="pwnagotchi", version=None):
    applies = pack.get("applies_to") if isinstance(pack, dict) else None
    if not isinstance(applies, dict):
        return True
    platforms = applies.get("platform")
    if isinstance(platforms, list) and platforms and platform_name not in platforms:
        return False
    current = _version_key(version)
    minimum = _version_key(applies.get("min_version"))
    maximum = _version_key(applies.get("max_version"))
    if (minimum is not None or maximum is not None) and current is None:
        return False
    if current is not None and minimum is not None and current < minimum:
        return False
    if current is not None and maximum is not None and current > maximum:
        return False
    return True


def condition_from_pack(pack, *, allow_remedy=False):
    """Compile a validated data pack into runtime condition shape."""
    canonical_detect = pack["detect"]

    def detect(signals):
        return eval_condition_expr(canonical_detect, canonicalize_signals(signals))

    raw_fix = pack.get("fix")
    verify_expr = raw_fix.get("verify") if isinstance(raw_fix, dict) else None

    def verify_state(signals):
        if not isinstance(verify_expr, dict):
            return None
        return eval_condition_expr_state(verify_expr, canonicalize_signals(signals))

    fix = None
    unavailable_action = None
    if allow_remedy and isinstance(raw_fix, dict):
        action = _PACK_ACTION_ALIASES.get(raw_fix.get("action"), raw_fix.get("action"))
        if action in globals().get("ACTIONS", {}):
            fix = dict(raw_fix)
            fix["action"] = action
            guard = fix.get("guard")
            if guard:
                mapped = _PACK_GUARD_ALIASES.get(guard, guard)
                if mapped in globals().get("GUARDS", {}):
                    fix["guard"] = mapped
                else:
                    fix = None
        else:
            unavailable_action = raw_fix.get("action")

    howto = list(pack.get("howto", []))
    if raw_fix and not allow_remedy:
        howto.append("This external condition pack is explain-only under current Doctor policy.")
    elif unavailable_action:
        howto.append("Pack remedy action '%s' is not allow-listed on this Doctor." % unavailable_action)

    return {
        "id": pack["id"], "severity": pack["severity"], "confidence": pack["confidence"],
        "detect": detect, "symptom": pack["symptom"], "cause": pack.get("cause", ""),
        "fix": fix, "howto": howto, "runbook": pack.get("runbook"),
        "provenance": pack.get("provenance") or {"source": "local"}, "_pack": True,
        "_verify_state": verify_state if isinstance(verify_expr, dict) else None,
    }


def load_condition_packs(directory, *, allow_remedies=False, max_packs=128,
                         max_bytes=128 * 1024, platform_name="pwnagotchi", version=None,
                         source_class="external"):
    """Bounded local/offline loader. Returns (runtime_conditions, errors)."""
    conditions, errors = [], []
    if not directory or not os.path.isdir(directory):
        return conditions, errors
    try:
        names = sorted(x for x in os.listdir(directory) if x.lower().endswith(".json"))
    except Exception as exc:
        return [], [{"file": str(directory), "error": "list failed: %s" % exc}]
    for name in names[:max_packs]:
        pack_path = os.path.join(directory, name)
        try:
            if os.path.getsize(pack_path) > max_bytes:
                raise ValueError("pack exceeds %d byte limit" % max_bytes)
            with open(pack_path, "rb") as fp:
                raw = fp.read()
            digest = hashlib.sha256(raw).hexdigest()
            pack = json.loads(raw.decode("utf-8"))
            pack = dict(pack)
            provenance = dict(pack.get("provenance") or {})
            provenance.setdefault("source", name)
            provenance["source_class"] = source_class
            provenance["sha256"] = digest
            pack["provenance"] = provenance
            schema_errors = validate_condition_pack(pack)
            if schema_errors:
                raise ValueError("; ".join(schema_errors))
            if not pack_applies(pack, platform_name=platform_name, version=version):
                continue
            conditions.append(condition_from_pack(pack, allow_remedy=allow_remedies))
        except Exception as exc:
            errors.append({"file": name, "error": str(exc)[:240]})
    if len(names) > max_packs:
        errors.append({"file": str(directory), "error": "pack count exceeds %d; extras ignored" % max_packs})
    return conditions, errors



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
    # NOTE: sd_readonly migrated to a bundled Condition Pack (doctor_packs/sd_readonly.json).

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

    # NOTE: rfkill_blocked, no_monitor, wpa_supplicant_hijack migrated to bundled Condition Packs
    # (doctor_packs/*.json). wpa_supplicant_hijack keeps its guard (not_uplink) + fix.verify there.

    {"id": "iface_mismatch", "severity": "high", "confidence": "high",
     "detect": lambda s: iface_mismatch(s.get("iface", {}).get("configured"),
                                        s.get("iface", {}).get("present")),
     "symptom": "the configured Wi-Fi interface isn't present",
     "cause": "main.iface points at an adapter that doesn't exist (wrong name, e.g. wlan1 vs "
              "wlan0, or the adapter didn't enumerate)",
     "fix": None,
     "howto": ["Run: iw dev   and   ls /sys/class/net   to see the real names.",
               "Set main.iface in /etc/pwnagotchi/config.toml to the adapter you use.",
               "If the adapter is missing entirely, check power/cable/USB."]},

    {"id": "reboot_loop", "severity": "high", "confidence": "medium",
     "detect": lambda s: (_booted(s)
                          and (s.get("service_restarts", {}).get("pwnagotchi") or 0)
                          >= s.get("_cfg", {}).get("restart_loop_threshold", 5)),
     "symptom": "the pwnagotchi service is restarting repeatedly (crash loop)",
     "cause": "pwnagotchi keeps crashing and systemd keeps restarting it — usually a bad plugin "
              "or a recent config/edit",
     "fix": None,
     "howto": ["journalctl -u pwnagotchi -n 100   to see the crash.",
               "Suspect a recently enabled plugin or config edit — the 'what changed since "
               "known-good' view below helps.",
               "Disable the offending plugin, or restore config.toml."]},

    {"id": "journald_bloat", "severity": "warn", "confidence": "high",
     "detect": lambda s: (s.get("journal_bytes") is not None
                          and s["journal_bytes"] > s.get("_cfg", {}).get(
                              "journal_max_bytes", 200 * 1024 * 1024)),
     "symptom": "the systemd journal is using a lot of space",
     "cause": "journald logs have grown large (disk pressure + SD wear)",
     "fix": {"action": "vacuum_journal", "tier": "safe"},
     "howto": ["sudo journalctl --vacuum-size=100M",
               "On an SD-based Pi, consider Storage=volatile for journald."]},

    # NOTE: debug_log_level migrated to a bundled Condition Pack (doctor_packs/debug_log_level.json).

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

    # NOTE: config_invalid migrated to a bundled Condition Pack (doctor_packs/config_invalid.json).

    {"id": "plugin_crash_loop", "severity": "high", "confidence": "low",
     "detect": lambda s: (s.get("log", {}).get("tracebacks", 0) >= 3
                          or len(s.get("log", {}).get("plugins_failed", [])) >= 1),
     "symptom": "a plugin is crashing / failed to load",
     "cause": "a third-party plugin is raising exceptions",
     "fix": {"action": "quarantine_plugin", "tier": "risky"},
     "howto": ["Find the plugin in the log ('error while loading' / traceback).",
               "Disable it: main.plugins.<name>.enabled = false, then restart pwnagotchi."]},

    # NOTE: handshakes_unwritable migrated to a bundled Condition Pack
    # (doctor_packs/handshakes_unwritable.json).

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

    # NOTE: low_memory, swap_thrash, no_route, dns_broken, sd_errors migrated to bundled
    # Condition Packs (doctor_packs/*.json). Threshold/boot-gated/computed conditions stay below.

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
    {"when": {"wpa_supplicant_hijack", "no_monitor"},
     "text": "wpa_supplicant holds the adapter → no monitor interface → no captures."},
    {"when": {"iface_mismatch", "no_monitor"},
     "text": "the configured Wi-Fi interface isn't present → no monitor interface → no captures."},
    {"when": {"reboot_loop", "config_invalid"},
     "text": "invalid config.toml → pwnagotchi keeps crashing (reboot loop)."},
    {"when": {"journald_bloat", "disk_full"},
     "text": "journal bloat → the disk fills up."},
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

# Root -> downstream symptoms. Presence of a root never hides diagnosis; it only prevents
# redundant automatic treatment of the downstream symptom in the same pass.
CAUSAL_ROOTS = {
    "rfkill_blocked": {"no_monitor"},
    "wpa_supplicant_hijack": {"no_monitor"},
    "iface_mismatch": {"no_monitor"},
    "config_invalid": {"reboot_loop"},
    "journald_bloat": {"disk_full"},
    "undervoltage": {"usb_resets"},
    "sd_errors": {"sd_readonly"},
    "disk_full": {"sd_readonly"},
    "no_route": {"dns_broken", "wpa_sec_errors"},
}


def suppress_downstream_treatments(findings):
    by_id = {row.get("id"): row for row in (findings or []) if row.get("id")}
    for root, downstream_ids in CAUSAL_ROOTS.items():
        if root not in by_id:
            continue
        for child in downstream_ids:
            row = by_id.get(child)
            if row is not None and row.get("fix"):
                row["_suppressed_by"] = root
    return findings


def recovery_posture(signals, findings=None):
    """Conservative recovery posture for questionable media/config integrity."""
    signals = signals or {}
    reasons = []
    dmesg = signals.get("dmesg", {}) or {}
    disk = signals.get("disk", {}) or {}
    config = signals.get("config", {}) or {}
    ids = {row.get("id") for row in (findings or []) if row.get("id")}
    if int(dmesg.get("sd_error", 0) or 0) > 0:
        reasons.append("storage_io_errors")
    if disk.get("root_ro") is True:
        reasons.append("root_read_only")
    if config.get("valid") is False and "reboot_loop" in ids:
        reasons.append("invalid_config_crash_loop")
    return {
        "active": bool(reasons),
        "reasons": sorted(set(reasons)),
        "policy": "confirm_mutations",
    }


def build_causal(finding_ids):
    ids = set(finding_ids)
    return [c["text"] for c in CHAINS if c["when"] <= ids]


# ======================================================================================
# Diagnosis (pure over signals)
# ======================================================================================
def diagnose(signals, extra_conditions=None):
    findings = []
    seen = set()
    # Built-ins first so a data pack can never shadow (redefine) a core condition id.
    for c in list(CONDITIONS) + list(extra_conditions or []):
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        try:
            hit = c["detect"](signals)
        except Exception:
            hit = False
        if hit:
            findings.append({
                "id": c["id"], "severity": c["severity"], "confidence": c["confidence"],
                "symptom": c["symptom"], "cause": c["cause"], "howto": list(c.get("howto", [])),
                "fix": c.get("fix"), "_detect": c["detect"],
                "_verify_state": c.get("_verify_state"),
                "provenance": c.get("provenance"),
                "outcome": "detected",
            })
    findings.sort(key=lambda f: (_SEV_RANK.get(f["severity"], 9), _CONF_RANK.get(f["confidence"], 9)))
    return findings


# Outcomes that mean "still a live problem the owner should see."
_REMAINING = ("needs_user", "fix_failed", "gave_up", "blocked_guard", "would_fix",
              "executed_verification_unknown", "awaiting_confirm")


def overall_status(findings):
    remaining = [f for f in findings if f["outcome"] in _REMAINING]
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
# Plain-language narrative ("explain better") — pure, for the web page / logs / digest
# ======================================================================================
_STATUS_HEAD = {
    "OK": "Everything looks healthy — no problems detected.",
    "HEALED": "All clear now — I detected and fixed problem(s) this cycle.",
    "ATTENTION": "Mostly fine, with a minor thing to note.",
    "DEGRADED": "Degraded — some functions may not be working well.",
    "ACTION_REQUIRED": "Needs attention — something important is wrong.",
}


def narrate(status, findings, causal=None, drift=None):
    """Stitch status + findings + causal chain + known-good drift into one human paragraph."""
    findings = findings or []
    fixed = [f for f in findings if f.get("outcome") == "fixed"]
    awaiting = [f for f in findings if f.get("outcome") == "awaiting_confirm"]
    remaining = [f for f in findings
                 if f.get("outcome") in _REMAINING and f.get("outcome") != "awaiting_confirm"]
    parts = [_STATUS_HEAD.get(status, "Health status: %s." % status)]
    if fixed:
        parts.append("Auto-fixed: %s." % ", ".join(f.get("symptom", "?") for f in fixed))
    if awaiting:
        parts.append("Waiting for your approval: %s (open the Doctor page to confirm)."
                     % ", ".join(f.get("symptom", "?") for f in awaiting))
    if remaining:
        top = remaining[:3]
        parts.append("Needs you: %s." % "; ".join(
            "%s — %s" % (f.get("symptom", "?"), (f.get("howto") or ["see the Doctor page"])[0])
            for f in top))
        if len(remaining) > 3:
            parts.append("(+%d more on the Doctor page.)" % (len(remaining) - 3))
    if causal:
        parts.append("Likely chain: %s" % " ".join(causal))
    if drift and drift.get("has_changes"):
        bits = []
        if drift.get("config_changed"):
            bits.append("config.toml changed")
        if drift.get("plugins_added"):
            bits.append("plugins enabled (%s)" % ", ".join(drift["plugins_added"][:5]))
        if drift.get("plugins_removed"):
            bits.append("plugins disabled (%s)" % ", ".join(drift["plugins_removed"][:5]))
        if drift.get("packages_changed"):
            bits.append("packages changed (%s)" % ", ".join(drift["packages_changed"][:5]))
        if drift.get("kernel_changed"):
            bits.append("kernel changed")
        if drift.get("os_changed"):
            bits.append("OS changed")
        if bits:
            parts.append("Since your known-good checkpoint: %s." % "; ".join(bits))
    return " ".join(parts)


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


def act_stop_wpa_supplicant(args, runner, signals, ctx):
    runner(["systemctl", "stop", "wpa_supplicant"])
    return True


def act_vacuum_journal(args, runner, signals, ctx):
    mb = int(ctx.get("journal_keep_mb", 100))
    runner(["journalctl", "--vacuum-size=%dM" % mb])
    return True


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
    "stop_wpa_supplicant": act_stop_wpa_supplicant,
    "vacuum_journal": act_vacuum_journal,
    "restore_config": act_restore_config,
    "quarantine_plugin": act_quarantine_plugin,
}

# Richer-than-safe|risky action metadata (data only for now; report + future policy in v0.6).
# tier stays the policy handle; the attributes describe *why* an action is (or isn't) benign.
ACTION_META = {
    "restart_service":    {"tier": "safe",  "reversible": True,  "destructive": False,
                           "interrupts_service": True,  "affects_connectivity": False,
                           "needs_reboot": False},
    "rfkill_unblock":     {"tier": "safe",  "reversible": True,  "destructive": False,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "set_time":           {"tier": "safe",  "reversible": True,  "destructive": False,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "make_handshakes_dir":{"tier": "safe",  "reversible": True,  "destructive": False,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "prune_logs":         {"tier": "safe",  "reversible": False, "destructive": True,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "vacuum_journal":     {"tier": "safe",  "reversible": False, "destructive": True,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "stop_wpa_supplicant":{"tier": "safe",  "reversible": True,  "destructive": False,
                           "interrupts_service": True,  "affects_connectivity": True,
                           "needs_reboot": False},
    "remount_rw":         {"tier": "risky", "reversible": True,  "destructive": False,
                           "interrupts_service": False, "affects_connectivity": False,
                           "needs_reboot": False},
    "restore_config":     {"tier": "risky", "reversible": True,  "destructive": False,
                           "interrupts_service": True,  "affects_connectivity": False,
                           "needs_reboot": True},
    "quarantine_plugin":  {"tier": "risky", "reversible": True,  "destructive": False,
                           "interrupts_service": True,  "affects_connectivity": False,
                           "needs_reboot": True},
}


# Safety guards: a fix may name a guard; it only runs when the guard confirms it's safe *now*.
def guard_wpa_not_uplink(signals, ctx):
    """Safe to stop wpa_supplicant unless it appears to carry the owner's uplink."""
    up = (signals.get("net", {}) or {}).get("default_iface")
    return not (isinstance(up, str) and up.startswith("wlan"))


def guard_media_ok(signals, ctx):
    """Safe to remount rw only when the kernel isn't reporting SD I/O errors."""
    return (signals.get("dmesg", {}) or {}).get("sd_error", 0) < 1


GUARDS = {
    "wpa_not_uplink": guard_wpa_not_uplink,
    "media_ok": guard_media_ok,
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

    def snapshot(self):
        """JSON-able copy of the attempt history (for persistence across reboots)."""
        return {k: list(v) for k, v in self._events.items() if v}

    def restore(self, data):
        if isinstance(data, dict):
            self._events = {k: [float(t) for t in v]
                            for k, v in data.items() if isinstance(v, list)}
        return self


# Autonomy levels (Standing Orders). off/observe/notify never act; conservative acts on safe
# fixes only; assertive also acts on risky ones. Legacy "safe"/"all" map in.
_LEVEL_ALIASES = {"safe": "conservative", "all": "assertive", "on": "conservative",
                  "true": "conservative", "1": "conservative"}
_LEVELS = ("off", "observe", "notify", "conservative", "assertive")


def normalize_level(value):
    v = str(value).strip().lower()
    v = _LEVEL_ALIASES.get(v, v)
    return v if v in _LEVELS else "conservative"


def policy_allows(tier, level):
    level = normalize_level(level)
    if level == "assertive":
        return True
    if level == "conservative":
        return tier == "safe"
    return False


def _action_meta(action):
    return ACTION_META.get(action, {})


def _decision_start(finding, level, dry_run=False):
    fix = finding.get("fix") if isinstance(finding, dict) else None
    fix = fix if isinstance(fix, dict) else {}
    row = {
        "condition": finding.get("id") if isinstance(finding, dict) else None,
        "action": fix.get("action"),
        "tier": fix.get("tier"),
        "standing_order": level,
        "dry_run": bool(dry_run),
        "gates": [],
    }
    finding["decision"] = row
    return row


def _decision_gate(finding, gate, result, reason=None):
    row = finding.setdefault("decision", {"gates": []})
    gates = row.setdefault("gates", [])
    item = {"gate": gate, "result": result}
    if reason:
        item["reason"] = reason
    gates.append(item)
    return item


def _decision_finish(finding, outcome, reason):
    finding["outcome"] = outcome
    row = finding.setdefault("decision", {"gates": []})
    row["outcome"] = outcome
    row["reason"] = reason
    return finding


def annotate_remedy_efficacy(findings, patient, *, min_verified=4, poor_success_rate=0.25):
    """Attach per-device remedy history; poor verified efficacy can only reduce autonomy."""
    if patient is None:
        return findings
    for finding in findings or []:
        fix = finding.get("fix")
        if not isinstance(fix, dict):
            continue
        stats = patient.remedy_efficacy(finding.get("id"), action=fix.get("action"))
        finding["efficacy"] = stats
        verified = int(stats.get("verified_attempts", 0) or 0)
        rate = stats.get("success_rate")
        if verified >= int(min_verified) and rate is not None and float(rate) < float(poor_success_rate):
            finding["_efficacy_hold"] = True
    return findings


def apply_fixes(findings, signals, autofix, runner, breaker, ctx,
                recollect=None, now=None, dry_run=False, disabled=None, confirm=None,
                force=None, denied_actions=None, allow_reboot=False, recovery=None):
    """Attempt allowed fixes; guard; verify; set outcome + machine-readable decision trace.

    The trace is observational only: it explains the exact existing gates and never expands
    treatment authority.
    """
    now = now if now is not None else time.time()
    disabled = set(disabled or ())
    confirm = set(confirm or ())
    force = set(force or ())
    denied_actions = set(denied_actions or ())
    level = normalize_level(autofix)

    for f in findings:
        fix = f.get("fix")
        _decision_start(f, level, dry_run=dry_run)

        if not fix:
            _decision_gate(f, "remedy", "blocked", "no_remedy")
            _decision_finish(f, "needs_user", "no_remedy")
            continue
        _decision_gate(f, "remedy", "passed")

        if f.get("confidence") == "low":
            _decision_gate(f, "confidence", "blocked", "low_confidence")
            _decision_finish(f, "needs_user", "low_confidence")
            continue
        _decision_gate(f, "confidence", "passed")

        if f["id"] in disabled:
            _decision_gate(f, "condition_opt_out", "blocked", "owner_disabled_condition")
            _decision_finish(f, "needs_user", "owner_disabled_condition")
            continue
        _decision_gate(f, "condition_opt_out", "passed")

        if fix.get("action") in denied_actions:
            _decision_gate(f, "action_veto", "blocked", "owner_denied_action")
            _decision_finish(f, "needs_user", "owner_denied_action")
            continue
        _decision_gate(f, "action_veto", "passed")

        if not policy_allows(fix.get("tier", "risky"), level):
            _decision_gate(f, "standing_orders", "blocked", "autonomy_level_disallows_tier")
            _decision_finish(f, "needs_user", "autonomy_level_disallows_tier")
            continue
        _decision_gate(f, "standing_orders", "passed")

        if f.get("_suppressed_by"):
            _decision_gate(f, "root_cause", "blocked", "suppressed_by:%s" % f["_suppressed_by"])
            _decision_finish(f, "needs_user", "downstream_treatment_suppressed")
            continue
        _decision_gate(f, "root_cause", "passed")

        guard = fix.get("guard")
        if guard:
            fn = GUARDS.get(guard)
            try:
                safe = bool(fn and fn(signals, ctx))
            except Exception:
                safe = False
            if not safe:
                _decision_gate(f, "guard", "blocked", str(guard))
                _decision_finish(f, "blocked_guard", "guard_blocked")
                continue
            _decision_gate(f, "guard", "passed", str(guard))

        recovery_active = bool((recovery or {}).get("active"))
        efficacy_hold = bool(f.get("_efficacy_hold"))
        needs_reboot = bool(_action_meta(fix.get("action")).get("needs_reboot"))
        held = (f["id"] in confirm) or (needs_reboot and not allow_reboot) or recovery_active or efficacy_hold
        if held and f["id"] not in force and not dry_run:
            if recovery_active:
                reason = "recovery_mode_requires_confirmation"
            elif efficacy_hold:
                reason = "poor_historical_efficacy_requires_confirmation"
            elif f["id"] in confirm:
                reason = "condition_requires_confirmation"
            else:
                reason = "reboot_action_requires_confirmation"
            _decision_gate(f, "confirmation", "blocked", reason)
            _decision_finish(f, "awaiting_confirm", reason)
            continue
        _decision_gate(
            f, "confirmation", "passed",
            "owner_forced" if f["id"] in force else ("dry_run" if dry_run else None)
        )

        if not breaker.allow(f["id"], now):
            _decision_gate(f, "circuit_breaker", "blocked", "attempt_budget_exhausted")
            _decision_finish(f, "gave_up", "circuit_breaker_open")
            continue
        _decision_gate(f, "circuit_breaker", "passed")

        if dry_run:
            _decision_gate(f, "mutation", "skipped", "dry_run")
            _decision_finish(f, "would_fix", "dry_run")
            continue

        breaker.record(f["id"], now)
        action = ACTIONS.get(fix["action"])
        try:
            ok = bool(action and action(fix.get("args", {}), runner, signals, ctx))
        except Exception as e:
            logging.debug("[doctor] action %s failed: %s", fix.get("action"), e)
            ok = False
        if not ok:
            _decision_gate(f, "action", "failed", "action_returned_false_or_raised")
            _decision_finish(f, "fix_failed", "action_failed")
            continue
        _decision_gate(f, "action", "passed")

        if recollect is None:
            _decision_gate(f, "verification", "unknown", "no_recollect")
            _decision_finish(f, "executed_verification_unknown", "verification_unavailable")
            continue
        try:
            fresh = recollect()
        except Exception:
            _decision_gate(f, "verification", "unknown", "recollect_failed")
            _decision_finish(f, "executed_verification_unknown", "verification_unavailable")
            continue

        verify_state = f.get("_verify_state")
        if callable(verify_state):
            try:
                verified = verify_state(fresh)
            except Exception:
                verified = None
            if verified is True:
                _decision_gate(f, "verification", "passed")
                _decision_finish(f, "fixed", "verified_fixed")
            elif verified is False:
                _decision_gate(f, "verification", "failed")
                _decision_finish(f, "fix_failed", "verification_failed")
            else:
                _decision_gate(f, "verification", "unknown", "missing_or_unreadable_evidence")
                _decision_finish(f, "executed_verification_unknown", "verification_unknown")
        else:
            remains = bool(f["_detect"](fresh))
            if remains:
                _decision_gate(f, "verification", "failed")
                _decision_finish(f, "fix_failed", "condition_still_present")
            else:
                _decision_gate(f, "verification", "passed")
                _decision_finish(f, "fixed", "condition_cleared")
    return findings



# ======================================================================================
# Patient Chart v2 — bounded device-specific memory with explicit schema migration
# ======================================================================================
class PatientChart:
    SCHEMA = PUBLIC_CONTRACTS["patient_chart"]

    @classmethod
    def _blank(cls):
        return {
            "schema": cls.SCHEMA,
            "identity": {},
            "known_good": {},
            "coverage": {},
            "status": None,
            "chronic": {},
            "remedies": [],
            "migrations": [],
            "updated_at": None,
        }

    @classmethod
    def migrate(cls, obj):
        """Return (migrated_object, changed).

        Migrations are monotonic and lossless for fields Doctor owns. A chart from a
        *newer* Doctor is deliberately rejected rather than downgraded/overwritten.
        """
        if not isinstance(obj, dict):
            raise ValueError("patient chart must be an object")
        try:
            schema = int(obj.get("schema", 1))
        except (TypeError, ValueError):
            raise ValueError("patient chart schema is invalid")
        if schema > cls.SCHEMA:
            raise RuntimeError("patient chart schema %s is newer than supported %s" %
                               (schema, cls.SCHEMA))
        if schema < 1:
            raise ValueError("patient chart schema is unsupported")

        out = dict(obj)
        changed = False
        while schema < cls.SCHEMA:
            if schema == 1:
                history = list(out.get("migrations") or [])
                history.append({"from": 1, "to": 2})
                out["migrations"] = history[-16:]
                schema = 2
                out["schema"] = schema
                changed = True
            else:
                raise RuntimeError("no patient chart migration from schema %s" % schema)

        # Fill newly introduced optional keys without discarding unknown forward-compatible
        # data that may have been written by another component on the same schema.
        for key, value in cls._blank().items():
            if key not in out:
                out[key] = value
                changed = True
        return out, changed

    def __init__(self, path, *, max_remedies=100):
        self.path = path
        self.max_remedies = max(10, int(max_remedies))
        self.data = self._blank()
        self.load_error = None
        self._write_enabled = True
        self.load()

    def load(self):
        try:
            if self.path and os.path.exists(self.path):
                with open(self.path, "rt", encoding="utf-8") as fp:
                    obj = json.load(fp)
                migrated, changed = self.migrate(obj)
                self.data = migrated
                if changed:
                    self._write()
        except RuntimeError as exc:
            # Critical rollback rule: an older Doctor must never clobber a Patient Chart
            # created by a newer schema it cannot understand.
            self.load_error = str(exc)
            self._write_enabled = False
            logging.warning("[doctor] patient chart left read-only: %s", exc)
        except Exception as exc:
            self.load_error = str(exc)
            logging.debug("[doctor] patient chart load failed: %s", exc)
        return self

    def _write(self):
        if not self.path or not self._write_enabled:
            return False
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                json.dump(self.data, fp, indent=2, sort_keys=True, default=str)
                fp.write("\n")
            try:
                os.chmod(tmp, 0o600)
            except Exception:
                pass
            os.replace(tmp, self.path)
            return True
        except Exception as exc:
            logging.debug("[doctor] patient chart save failed: %s", exc)
            return False

    @staticmethod
    def coverage_from(signals):
        s = signals or {}
        return {
            "services": bool(s.get("services")),
            "storage": bool(s.get("disk")),
            "power": bool(s.get("throttled")),
            "radio": s.get("monitor_present") is not None or s.get("rfkill_blocked") is not None,
            "network": bool(s.get("net")),
            "pwnagotchi_config": bool(s.get("config")),
            "logs": s.get("log_size") is not None or bool(s.get("log")),
        }

    @staticmethod
    def identity_from(signals):
        s = signals or {}
        model = None
        try:
            with open("/proc/device-tree/model", "rt", errors="ignore") as fp:
                model = fp.read().replace(chr(0), "").strip() or None
        except Exception:
            pass
        compat = compatibility_fingerprint()
        return {
            "model": model,
            "architecture": compat.get("architecture"),
            "kernel": compat.get("kernel"),
            "pwnagotchi_version": compat.get("pwnagotchi_version"),
            "python_version": compat.get("python_version"),
            "os_id": compat.get("os_id"),
            "os_version_id": compat.get("os_version_id"),
            "os_build_id": compat.get("os_build_id"),
            "configured_iface": (s.get("iface", {}) or {}).get("configured"),
            "interfaces": (s.get("iface", {}) or {}).get("present"),
            "services": sorted((s.get("services", {}) or {}).keys()),
        }

    def observe(self, signals, findings, status, *, now=None, known_good=None):
        """Persist meaningful patient changes, episode transitions and remedy outcomes only.

        IncidentEngine remains the source of truth for open/resolved incidents. The chart keeps
        compact recurrence memory so Doctor can recognize "this keeps happening" across reboot.
        """
        now = float(time.time() if now is None else now)
        changed = False
        identity = self.identity_from(signals)
        coverage = self.coverage_from(signals)
        if identity != self.data.get("identity"):
            self.data["identity"] = identity
            changed = True
        if coverage != self.data.get("coverage"):
            self.data["coverage"] = coverage
            changed = True
        if status != self.data.get("status"):
            self.data["status"] = status
            changed = True
        if known_good is not None:
            summary = {
                "saved_at": known_good.get("saved_at"),
                "kernel": known_good.get("kernel"),
                "os": known_good.get("os"),
                "plugin_count": len(known_good.get("plugins", []) or []),
                "package_count": len(known_good.get("packages", {}) or {}),
            }
            if summary != self.data.get("known_good"):
                self.data["known_good"] = summary
                changed = True

        chronic = self.data.setdefault("chronic", {})
        present = {f.get("id"): f for f in (findings or []) if f.get("id")}
        action_outcomes = {"fixed", "fix_failed", "executed_verification_unknown"}

        # Open/re-open episodes only on transition, not every scan.
        for fid, finding in present.items():
            row = chronic.setdefault(fid, {
                "episodes": 0, "active": False, "first_seen": now,
                "last_opened": None, "last_resolved": None, "last_outcome": None,
                "remedy_attempts": 0, "remedy_successes": 0,
                "remedy_failures": 0, "verification_unknowns": 0,
            })
            if not row.get("active"):
                row["episodes"] = int(row.get("episodes", 0)) + 1
                row["active"] = True
                row["last_opened"] = now
                if row.get("first_seen") is None:
                    row["first_seen"] = now
                changed = True

            outcome = finding.get("outcome")
            if outcome in action_outcomes:
                event = {
                    "at": now,
                    "condition": fid,
                    "outcome": outcome,
                    "action": ((finding.get("fix") or {}).get("action")
                               if isinstance(finding.get("fix"), dict) else None),
                }
                if not self.data["remedies"] or self.data["remedies"][-1] != event:
                    self.data["remedies"].append(event)
                    self.data["remedies"] = self.data["remedies"][-self.max_remedies:]
                    row["remedy_attempts"] = int(row.get("remedy_attempts", 0)) + 1
                    if outcome == "fixed":
                        row["remedy_successes"] = int(row.get("remedy_successes", 0)) + 1
                    elif outcome == "fix_failed":
                        row["remedy_failures"] = int(row.get("remedy_failures", 0)) + 1
                    else:
                        row["verification_unknowns"] = int(row.get("verification_unknowns", 0)) + 1
                    row["last_outcome"] = outcome
                    changed = True

            # A condition detected and fixed in the same scan is a complete episode.
            if outcome == "fixed" and row.get("active"):
                row["active"] = False
                row["last_resolved"] = now
                changed = True

        # If a previously active condition is no longer detected, close the recurrence episode.
        for fid, row in chronic.items():
            if row.get("active") and fid not in present:
                row["active"] = False
                row["last_resolved"] = now
                if row.get("last_outcome") not in action_outcomes:
                    row["last_outcome"] = "cleared"
                changed = True

        if changed:
            self.data["updated_at"] = now
            self._write()
        return changed

    def chronic_summary(self, condition_id=None):
        chronic = self.data.get("chronic") or {}
        if condition_id is not None:
            row = chronic.get(condition_id)
            return dict(row) if isinstance(row, dict) else None
        return {k: dict(v) for k, v in chronic.items() if isinstance(v, dict)}

    def remedy_efficacy(self, condition_id, action=None):
        rows = [
            row for row in (self.data.get("remedies") or [])
            if isinstance(row, dict)
            and row.get("condition") == condition_id
            and (action is None or row.get("action") == action)
        ]
        successes = sum(1 for row in rows if row.get("outcome") == "fixed")
        failures = sum(1 for row in rows if row.get("outcome") == "fix_failed")
        unknowns = sum(1 for row in rows if row.get("outcome") == "executed_verification_unknown")
        verified = successes + failures
        rate = (float(successes) / verified) if verified else None
        if verified < 2:
            classification = "insufficient_history"
        elif rate is not None and rate >= 0.75:
            classification = "usually_effective"
        elif rate is not None and rate < 0.25:
            classification = "poor_history"
        else:
            classification = "mixed_history"
        return {
            "condition": condition_id,
            "action": action,
            "attempts": len(rows),
            "verified_attempts": verified,
            "successes": successes,
            "failures": failures,
            "verification_unknowns": unknowns,
            "success_rate": rate,
            "classification": classification,
        }

    def rank_remedies(self, condition_id, remedies):
        """Stable per-device ranking; history never grants authority."""
        scored = []
        for index, remedy in enumerate(remedies or []):
            action = remedy.get("action") if isinstance(remedy, dict) else None
            stats = self.remedy_efficacy(condition_id, action=action)
            rate = stats.get("success_rate")
            # No evidence is neutral; known poor history sorts last.
            score = 0.5 if rate is None else float(rate)
            scored.append((score, -int(stats.get("verified_attempts", 0) or 0), -index, remedy, stats))
        scored.sort(reverse=True, key=lambda row: row[:3])
        return [{"remedy": row[3], "efficacy": row[4]} for row in scored]

    def summary(self):
        chronic = self.data.get("chronic") or {}
        recurring = sum(1 for row in chronic.values()
                        if isinstance(row, dict) and int(row.get("episodes", 0)) >= 2)
        return {
            "schema": self.data.get("schema"),
            "load_error": self.load_error,
            "migration_count": len(self.data.get("migrations") or []),
            "status": self.data.get("status"),
            "identity": dict(self.data.get("identity") or {}),
            "coverage": dict(self.data.get("coverage") or {}),
            "known_good": dict(self.data.get("known_good") or {}),
            "remedy_count": len(self.data.get("remedies") or []),
            "condition_count": len(chronic),
            "recurring_condition_count": recurring,
            "updated_at": self.data.get("updated_at"),
        }


# ======================================================================================
# Plugin
# ======================================================================================
_SNAPSHOT_KEYS = ("temp_c", "mem_pct", "swap_used_pct", "disk", "throttled", "services",
                  "monitor_present", "rfkill_blocked", "bettercap_reachable", "uptime_sec",
                  "wpa_supplicant", "iface", "journal_bytes", "service_restarts", "net")
_UI_STATUS = {"OK": "OK", "HEALED": "healed", "ATTENTION": "attn",
              "DEGRADED": "DEGR", "ACTION_REQUIRED": "ACT!"}


class Doctor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.7.0-pre1"
    __license__ = "GPL3"
    __description__ = "Autonomous health scan, diagnosis, plain-language explanation, guarded self-healing, known-good drift and a sanitized support bundle."

    def __init__(self):
        self.options = dict()
        self._findings = []
        self._status = "OK"
        self._causal = []
        self._narrative = _STATUS_HEAD["OK"]
        self._breaker = CircuitBreaker()
        self._open = {}          # id -> {opened_at, severity, summary, snapshot}
        self._history = []
        self._breaker_path = None
        self._patient = None
        self._bundled_conditions = []
        self._external_conditions = []
        self._catalog_conditions = []
        self._pack_conditions = []
        self._pack_errors = []
        self._providers = []
        self._provider_errors = []
        self._provider_evidence_meta = {}
        self._recovery = {"active": False, "reasons": [], "policy": "confirm_mutations"}

    def _read_options(self):
        """Parse options into attrs. Called on load AND on_config_changed (live-editable)."""
        self._autofix = normalize_level(self.options.get("autofix", "conservative"))
        self._dry_run = bool(self.options.get("dry_run", False))
        self._disabled = set(self.options.get("disable_autofix", []) or [])
        self._confirm_required = set(self.options.get("confirm_required", []) or [])
        self._deny_actions = set(self.options.get("deny_actions", []) or [])
        self._allow_reboot = bool(self.options.get("allow_reboot_actions", False))
        self._support_dir = self.options.get("support_dir", "/var/lib/pwnagotchi/doctor")
        self._support_log_lines = int(self.options.get("support_log_lines", 400))
        self._scan_every = int(self.options.get("scan_every", 30))
        self._boot_grace = float(self.options.get("boot_grace_s", 25))
        self._log_path = self.options.get("log_path", "/etc/pwnagotchi/log/pwnagotchi.log")
        self._config_path = self.options.get("config_path", "/etc/pwnagotchi/config.toml")
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._incident_path = self.options.get("incident_path",
                                               "/etc/pwnagotchi/doctor_incidents.json")
        self._checkpoint_path = self.options.get("checkpoint_path",
                                                 "/etc/pwnagotchi/doctor_known_good.json")
        self._checkpoint_generations = max(
            1, min(20, int(self.options.get("checkpoint_generations", 5)))
        )
        self._breaker_path = self.options.get("breaker_path",
                                              "/etc/pwnagotchi/doctor_breaker.json")
        self._patient_path = self.options.get("patient_path",
                                              "/var/lib/pwnagotchi/doctor/patient.json")
        self._condition_dir = self.options.get("condition_dir",
                                               "/etc/pwnagotchi/doctor.d")
        self._catalog_dir = self.options.get("catalog_dir",
                                             "/var/lib/pwnagotchi/doctor/catalog.d")
        self._enable_cached_catalog = bool(self.options.get("enable_cached_catalog", False))
        self._provider_dir = self.options.get("provider_dir", "/run/pwnagotchi/health.d")
        self._provider_max_age_s = max(1, int(self.options.get("provider_max_age_s", 300)))
        self._allow_pack_remedies = bool(self.options.get("allow_pack_remedies", False))
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._max_temp_c = float(self.options.get("max_temp_c", 80))
        self._journal_max_mb = int(self.options.get("journal_max_mb", 200))
        self._journal_keep_mb = int(self.options.get("journal_keep_mb", 100))
        self._restart_loop_threshold = int(self.options.get("restart_loop_threshold", 5))
        self._services = list(self.options.get("services",
                              ["pwnagotchi", "bettercap", "pwngrid-peer"]))

    def on_loaded(self):
        self._read_options()
        self._load_breaker()
        self._patient = PatientChart(self._patient_path)
        self._reload_condition_packs()
        logging.info("[doctor] loaded v%s (autonomy=%s, dry_run=%s, packs=%d)",
                     self.__version__, self._autofix, self._dry_run, len(self._pack_conditions))

    def on_config_changed(self, config):
        # Standing Orders (autonomy dial, opt-outs, thresholds) are editable at any time.
        old_patient_path = getattr(self, "_patient_path", None)
        self._read_options()
        if old_patient_path != self._patient_path or self._patient is None:
            self._patient = PatientChart(self._patient_path)
        self._reload_condition_packs()
        logging.info("[doctor] config reloaded (autonomy=%s, dry_run=%s, packs=%d)",
                     self._autofix, self._dry_run, len(self._pack_conditions))

    def _reload_condition_packs(self):
        version = getattr(pwnagotchi, "__version__", None)

        # First-party bundled Medical Library. These packs ship in the same release artifact as
        # doctor.py, so moving a built-in condition from Python to JSON must not silently remove
        # its existing remedy authority. They still cannot introduce executable actions outside
        # ACTIONS/GUARDS, and all normal confidence/Standing-Order/circuit-breaker rules apply.
        bundled_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doctor_packs")
        self._bundled_conditions, bundled_errors = load_condition_packs(
            bundled_dir, allow_remedies=True, platform_name="pwnagotchi", version=version,
            source_class="bundled")

        # User/community packs are a separate trust class. They stay explain-only unless the
        # owner explicitly opts in, and even then may only call actions already allow-listed.
        self._external_conditions, external_errors = load_condition_packs(
            self._condition_dir, allow_remedies=self._allow_pack_remedies,
            platform_name="pwnagotchi", version=version, source_class="external")

        # Cached catalog knowledge is always explain-only. Staging/fetching knowledge never
        # grants treatment authority, even if the JSON names an allow-listed action.
        if self._enable_cached_catalog:
            self._catalog_conditions, catalog_errors = load_condition_packs(
                self._catalog_dir, allow_remedies=False,
                platform_name="pwnagotchi", version=version, source_class="catalog")
        else:
            self._catalog_conditions, catalog_errors = [], []

        # Ordering is authority: core Python -> bundled -> owner external -> cached catalog.
        self._pack_conditions = (self._bundled_conditions + self._external_conditions
                                 + self._catalog_conditions)
        self._pack_errors = bundled_errors + external_errors + catalog_errors
        for row in self._pack_errors[:10]:
            logging.warning("[doctor] condition pack skipped: %s: %s",
                            row.get("file"), row.get("error"))

    def _ctx(self):
        return {"log_path": self._log_path, "config_path": self._config_path,
                "handshakes": self._handshakes, "journal_keep_mb": self._journal_keep_mb,
                "log_max_bytes": 5 * 1024 * 1024, "log_keep_lines": 1000}

    # -- persistent circuit breaker (survives restart/reboot) ---------------------------
    def _load_breaker(self):
        try:
            if self._breaker_path and os.path.exists(self._breaker_path):
                with open(self._breaker_path) as fp:
                    self._breaker.restore(json.load(fp))
        except Exception as e:
            logging.debug("[doctor] breaker load failed: %s", e)

    def _save_breaker(self):
        try:
            if self._breaker_path:
                os.makedirs(os.path.dirname(self._breaker_path), exist_ok=True)
                with open(self._breaker_path, "w") as fp:
                    json.dump(self._breaker.snapshot(), fp)
        except Exception as e:
            logging.debug("[doctor] breaker save failed: %s", e)

    # -- collectors (guarded) ----------------------------------------------------------
    @staticmethod
    def _run(cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=6)

    def collect(self, runner=None):
        runner = runner or self._run
        s = {"_cfg": {"min_free_mb": self._min_free_mb, "max_temp_c": self._max_temp_c,
                      "boot_grace_s": self._boot_grace, "log_max_bytes": 5 * 1024 * 1024,
                      "journal_max_bytes": self._journal_max_mb * 1024 * 1024,
                      "restart_loop_threshold": self._restart_loop_threshold}}

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

        restarts = {}
        for name in self._services:
            try:
                out = runner(["systemctl", "show", name, "-p", "NRestarts", "--value"]).strip()
                restarts[name] = int(out or 0)
            except Exception:
                pass
        s["service_restarts"] = restarts

        try:
            active = runner(["systemctl", "is-active", "wpa_supplicant"]).strip() == "active"
            s["wpa_supplicant"] = {"running": active}
        except subprocess.CalledProcessError as e:
            s["wpa_supplicant"] = {"running": (e.output or "").strip() == "active"}
        except Exception:
            s["wpa_supplicant"] = {}

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

        cfg_text = None
        try:
            with open(self._config_path, "rt", errors="ignore") as fp:
                cfg_text = fp.read()
            s["config"] = config_valid(cfg_text)
            s["config"]["debug"] = config_debug_level(cfg_text)
        except Exception:
            s["config"] = {"valid": True, "error": None, "debug": False}

        # Wi-Fi interface: what config asks for vs. what's actually present.
        iface = {"configured": parse_main_iface(cfg_text)}
        try:
            iface["present"] = sorted(n for n in os.listdir("/sys/class/net")
                                      if n.startswith("wlan"))
        except Exception:
            iface["present"] = None
        s["iface"] = iface

        try:
            s["journal_bytes"] = parse_journal_usage(runner(["journalctl", "--disk-usage"]))
        except Exception:
            s["journal_bytes"] = None

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
                route_text = fp.read()
            net["default_route"] = parse_default_route(route_text)
            net["default_iface"] = parse_default_iface(route_text)
        except Exception:
            net["default_route"] = None
            net["default_iface"] = None
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

        provider_signals, provider_findings, provider_meta, providers, provider_errors = (
            load_health_provider_snapshots(
                self._provider_dir, now=time.time(), max_age_s=self._provider_max_age_s
            )
        )
        s["_provider_canonical"] = provider_signals
        s["_provider_findings"] = provider_findings
        self._provider_evidence_meta = provider_meta
        self._providers = providers
        self._provider_errors = provider_errors

        return s

    # -- the autonomous loop -----------------------------------------------------------
    def scan(self, runner=None, now=None, force_ids=None):
        now = now if now is not None else time.time()
        signals = self.collect(runner)
        findings = diagnose(signals, extra_conditions=self._pack_conditions)
        findings = merge_provider_findings(findings, signals.get("_provider_findings") or [])
        suppress_downstream_treatments(findings)
        annotate_remedy_efficacy(findings, self._patient)
        recovery = recovery_posture(signals, findings)
        self._recovery = recovery
        acting = self._autofix not in ("off", "observe", "notify") and not self._dry_run
        # confirm-required conditions (and reboot-class actions) wait for owner approval;
        # force_ids (from the web "Confirm & apply" link) approve a specific one for this pass.
        apply_fixes(findings, signals, self._autofix, runner or self._run,
                    self._breaker, self._ctx(),
                    recollect=(lambda: self.collect(runner)) if acting else None,
                    now=now, dry_run=self._dry_run, disabled=self._disabled,
                    confirm=self._confirm_required, force=set(force_ids or ()),
                    denied_actions=self._deny_actions, allow_reboot=self._allow_reboot,
                    recovery=recovery)
        self._save_breaker()
        self._findings = findings
        self._status = overall_status(findings)
        self._causal = build_causal(f["id"] for f in findings)
        self._narrative = narrate(self._status, findings, self._causal)
        self._update_incidents(findings, signals, now)
        if self._patient is not None:
            self._patient.observe(signals, findings, self._status, now=now,
                                  known_good=self.load_checkpoint())
        if findings:
            logging.info("[doctor] %s: %d issue(s), %d auto-fixed", self._status,
                         len(findings), sum(1 for f in findings if f["outcome"] == "fixed"))
        return {"status": self._status, "findings": findings, "causal": self._causal,
                "recovery": dict(self._recovery)}

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

    def _load_checkpoint_store(self):
        try:
            if os.path.exists(self._checkpoint_path):
                with open(self._checkpoint_path) as f:
                    obj = json.load(f)
                if isinstance(obj, dict) and obj.get("schema") == 2:
                    gens = [x for x in (obj.get("generations") or []) if isinstance(x, dict)]
                    current = obj.get("current") if isinstance(obj.get("current"), dict) else None
                    if current is None and gens:
                        current = gens[-1]
                    return {"schema": 2, "current": current, "generations": gens}
                # Backward-compatible import of the original single-fingerprint format.
                if isinstance(obj, dict) and (
                        "saved_at" in obj or "config_hash" in obj or "packages" in obj):
                    return {"schema": 2, "current": obj, "generations": [obj]}
        except Exception as exc:
            logging.debug("[doctor] checkpoint load failed: %s", exc)
        return {"schema": 2, "current": None, "generations": []}

    def save_checkpoint(self, runner=None):
        fp = self.build_fingerprint(runner)
        store = self._load_checkpoint_store()
        generations = list(store.get("generations") or [])
        generations.append(fp)
        generations = generations[-self._checkpoint_generations:]
        payload = {"schema": 2, "current": fp, "generations": generations}
        try:
            parent = os.path.dirname(self._checkpoint_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self._checkpoint_path + ".tmp"
            with open(tmp, "w") as out:
                json.dump(payload, out, indent=2, sort_keys=True)
                out.write("\n")
            try:
                os.chmod(tmp, 0o600)
            except Exception:
                pass
            os.replace(tmp, self._checkpoint_path)
        except Exception as e:
            logging.debug("[doctor] checkpoint save failed: %s", e)
        return fp

    def load_checkpoint(self, generation=0):
        store = self._load_checkpoint_store()
        generations = store.get("generations") or []
        if generation in (None, 0):
            current = store.get("current")
            return dict(current) if isinstance(current, dict) else None
        try:
            offset = int(generation)
        except (TypeError, ValueError):
            return None
        if offset < 0 or offset >= len(generations):
            return None
        row = generations[-1 - offset]
        return dict(row) if isinstance(row, dict) else None

    def checkpoint_history(self):
        store = self._load_checkpoint_store()
        rows = []
        for fp in reversed(store.get("generations") or []):
            rows.append({
                "saved_at": fp.get("saved_at"),
                "kernel": fp.get("kernel"),
                "os": fp.get("os"),
                "plugin_count": len(fp.get("plugins") or []),
                "package_count": len(fp.get("packages") or {}),
                "config_hash": fp.get("config_hash"),
            })
        return rows

    def diff_since_checkpoint(self, runner=None, generation=0):
        old = self.load_checkpoint(generation=generation)
        if not old:
            return None
        return diff_fingerprint(old, self.build_fingerprint(runner))

    # -- plain-language narrative + sanitized support bundle ----------------------------
    def narrative(self):
        """Current human-readable summary (also reusable by daily_digest etc.)."""
        return self._narrative

    def status_contract(self):
        """Stable privacy-light machine-readable Doctor status for local consumers."""
        patient = self._patient.summary() if self._patient is not None else {}
        findings = []
        for finding in self._findings:
            findings.append({
                "id": finding.get("id"),
                "severity": finding.get("severity"),
                "confidence": finding.get("confidence"),
                "symptom": finding.get("symptom"),
                "outcome": finding.get("outcome"),
                "decision": dict(finding.get("decision") or {}),
                "provenance": dict(finding.get("provenance") or {}),
            })
        history = self.checkpoint_history()
        return {
            "schema": PUBLIC_CONTRACTS["doctor_status"],
            "doctor_version": self.__version__,
            "status": self._status,
            "narrative": self._narrative,
            "autonomy": {
                "level": self._autofix,
                "dry_run": bool(self._dry_run),
            },
            "findings": findings,
            "causal": list(self._causal or []),
            "patient": patient,
            "packs": {
                "bundled": len(self._bundled_conditions),
                "external": len(self._external_conditions),
                "catalog": len(self._catalog_conditions),
                "errors": list(self._pack_errors),
            },
            "recovery": dict(self._recovery),
            "providers": {
                "count": len(self._providers),
                "items": list(self._providers),
                "errors": list(self._provider_errors),
            },
            "known_good": {
                "generation_count": len(history),
                "current_saved_at": history[0].get("saved_at") if history else None,
            },
            "compatibility": compatibility_fingerprint(),
        }

    def _support_report(self):
        lines = [
            "PwnDoctor support report",
            "generated: %s UTC" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "doctor version: %s" % self.__version__,
            "status: %s" % self._status,
            "",
            "SUMMARY",
            narrate(self._status, self._findings, self._causal),
            "",
            "FINDINGS",
        ]
        if not self._findings:
            lines.append("  (none)")
        for f in self._findings:
            lines.append("- [%s/%s] %s -> %s" % (f.get("severity", "?"), f.get("confidence", "?"),
                                                 f.get("symptom", "?"), f.get("outcome", "?")))
            lines.append("    cause: %s" % f.get("cause", ""))
            for step in f.get("howto", []):
                lines.append("    - %s" % step)
        return redact_text("\n".join(lines))

    def build_support_bundle(self, out_path=None, runner=None):
        """Write a forum-ready, REDACTED zip: report + config + log tail + incidents + chart +
        environment. Secrets/SSIDs/MACs/IPs/GPS/emails are stripped. Returns the path (or None)."""
        import zipfile
        ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        if out_path is None:
            base = self._support_dir or os.path.dirname(self._patient_path or "") or "."
            out_path = os.path.join(base, "doctor_support_%s.zip" % ts)

        files = {"REPORT.txt": self._support_report()}
        try:
            with open(self._config_path, "rt", errors="ignore") as fp:
                files["config.redacted.toml"] = redact_config(fp.read())
        except Exception:
            pass
        try:
            with open(self._log_path, "rt", errors="ignore") as fp:
                tail = "".join(fp.readlines()[-self._support_log_lines:])
            files["pwnagotchi.log.tail.redacted.txt"] = redact_text(tail)
        except Exception:
            pass
        try:
            if os.path.exists(self._incident_path):
                with open(self._incident_path, "rt", errors="ignore") as fp:
                    files["incidents.json"] = redact_text(fp.read())
        except Exception:
            pass
        try:
            if self._patient is not None:
                files["patient_summary.json"] = json.dumps(self._patient.summary(),
                                                           indent=2, default=str)
        except Exception:
            pass
        try:
            env = {"doctor_version": self.__version__,
                   "compatibility": compatibility_fingerprint(),
                   "drift": self.diff_since_checkpoint(runner=runner),
                   "pack_count": len(self._pack_conditions),
                   "pack_errors": self._pack_errors}
            files["environment.json"] = redact_text(json.dumps(env, indent=2, default=str))
        except Exception:
            pass

        try:
            parent = os.path.dirname(out_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
                for name, content in files.items():
                    z.writestr(name, content if isinstance(content, str) else str(content))
            try:
                os.chmod(out_path, 0o600)
            except Exception:
                pass
            return out_path
        except Exception as e:
            logging.debug("[doctor] support bundle failed: %s", e)
            return None

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
        force_ids = None
        action = None
        try:
            if request is not None:
                action = request.args.get("action")
                cid = request.args.get("confirm")
                if cid:
                    force_ids = {cid}
        except Exception:
            force_ids = None
        # One-click sanitized support bundle (write to disk; bounded response with the path).
        if action == "support_bundle":
            self.scan(force_ids=force_ids)
            out = self.build_support_bundle()
            if out:
                size = os.path.getsize(out) if os.path.exists(out) else 0
                msg = ("<h3>Support bundle written ✅</h3>"
                       "<p><code>%s</code> (%d bytes)</p>"
                       "<p>It's sanitized (MACs, IPs, SSIDs, keys, GPS and emails stripped). "
                       "Copy it off with scp and attach it to a forum post or issue.</p>"
                       "<p><a href='?'>&larr; back to Doctor</a></p>" % (out, size))
            else:
                msg = ("<h3>Support bundle failed</h3><p>Could not write the bundle "
                       "(check the support_dir path/permissions).</p><p><a href='?'>&larr; back</a></p>")
            return "<html><body><h1>Doctor</h1>%s</body></html>" % msg
        drift = self._drift_html(request)
        self.scan(force_ids=force_ids)
        fixed = [f for f in self._findings if f["outcome"] == "fixed"]
        need = [f for f in self._findings
                if f["outcome"] in ("needs_user", "fix_failed", "gave_up", "awaiting_confirm")]
        causal = ("<h3>Likely cause chain</h3><ul>%s</ul>"
                  % "".join("<li>%s</li>" % c for c in self._causal)) if self._causal else ""
        patient = self._patient.summary() if self._patient is not None else {}
        coverage = patient.get("coverage") or {}
        covered = sum(1 for v in coverage.values() if v)
        recurring = int(patient.get("recurring_condition_count", 0) or 0)
        mode = ("<p><small>autonomy: <b>%s</b>%s · condition packs: %d · "
                "patient coverage: %d/%d · recurring: %d</small></p>"
                % (self._autofix, " · dry-run" if self._dry_run else "",
                   len(self._pack_conditions), covered, len(coverage), recurring))
        summary = "<h3>Summary</h3><p>%s</p>" % self._narrative
        tools = "<p><a href='?action=support_bundle'>Download sanitized support bundle</a></p>"
        if not self._findings:
            body = mode + summary + "<p><b>OK</b> — no issues detected. 🎉</p>" + tools
            return "<html><body><h1>Doctor</h1>{}{}</body></html>".format(body, drift)
        else:
            def block(f):
                steps = "".join("<li>%s</li>" % h for h in f.get("howto", []))
                outcome = f["outcome"]
                if outcome == "awaiting_confirm":
                    outcome += (" — <a href='?confirm=%s'>Confirm &amp; apply</a>" % f["id"])
                return ("<tr><td>{sev}</td><td>{conf}</td><td>{sym}</td><td>{cause}</td>"
                        "<td>{outcome}</td><td><ol>{steps}</ol></td></tr>").format(
                            sev=f["severity"], conf=f["confidence"], sym=f["symptom"],
                            cause=f["cause"], outcome=outcome, steps=steps)
            body = (mode + summary
                    + "<p>Status: <b>{st}</b> — auto-fixed {nf}, needs you {nn}</p>{causal}"
                    "<table border=1><tr><th>sev</th><th>confidence</th><th>symptom</th>"
                    "<th>cause</th><th>outcome</th><th>what to do</th></tr>{rows}</table>{tools}").format(
                        st=self._status, nf=len(fixed), nn=len(need), causal=causal,
                        rows="".join(block(f) for f in self._findings), tools=tools)
        return "<html><body><h1>Doctor</h1>{}{}</body></html>".format(body, drift)
