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
    for name, row in (s.get("services", {}) or {}).items():
        if isinstance(row, dict):
            out["service.%s.active" % name] = row.get("active")
    for name, count in (s.get("service_restarts", {}) or {}).items():
        out["service.%s.restart_count" % name] = count
    return {k: v for k, v in out.items() if v is not None}


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
    if pack.get("schema") != "condition-pack/v1":
        errors.append("schema must be condition-pack/v1")
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
    {"id": "sd_readonly", "severity": "high", "confidence": "high",
     "detect": lambda s: s.get("disk", {}).get("root_ro") is True,
     "symptom": "the root filesystem is mounted read-only",
     "cause": "the SD card hit an error and Linux remounted / read-only (writes silently fail)",
     "fix": {"action": "remount_rw", "tier": "risky", "guard": "media_ok"},
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

    # NOTE: no_monitor migrated to a first-party bundled Condition Pack (doctor_packs/no_monitor.json).

    {"id": "wpa_supplicant_hijack", "severity": "high", "confidence": "high",
     "detect": lambda s: (s.get("wpa_supplicant", {}).get("running") is True
                          and s.get("monitor_present") is False),
     "symptom": "wpa_supplicant is holding the Wi-Fi adapter",
     "cause": "wpa_supplicant grabbed the interface, so monitor mode / capture can't start "
              "(the #1 'monitor mode won't work' cause)",
     "fix": {"action": "stop_wpa_supplicant", "tier": "safe", "guard": "wpa_not_uplink"},
     "howto": ["sudo systemctl stop wpa_supplicant   (frees the adapter)",
               "If that adapter is your own uplink, only stop it on the capture adapter.",
               "Confirm: iw dev shows an interface of 'type monitor'."]},

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


def apply_fixes(findings, signals, autofix, runner, breaker, ctx,
                recollect=None, now=None, dry_run=False, disabled=None, confirm=None,
                force=None, denied_actions=None, allow_reboot=False):
    """Attempt allowed fixes; guard; verify; set each finding's outcome. Returns findings.

    Truth rules:
      * a low-confidence (log-inferred) finding is NEVER auto-fixed, only explained;
      * a guard that says "not safe right now" blocks the action (outcome blocked_guard);
      * an action that runs but can't be re-verified is executed_verification_unknown, not fixed.

    ACTION_META-driven policy:
      * an action the owner listed in `denied_actions` is never run (explain only);
      * a reboot-requiring action is held for confirmation unless `allow_reboot` is set;
      * `force` (from the web "Confirm & apply" link) approves a held id for this pass only.
    """
    now = now if now is not None else time.time()
    disabled = set(disabled or ())
    confirm = set(confirm or ())
    force = set(force or ())
    denied_actions = set(denied_actions or ())
    level = normalize_level(autofix)
    for f in findings:
        fix = f.get("fix")
        if not fix:
            f["outcome"] = "needs_user"
            continue
        if f.get("confidence") == "low":            # weak evidence -> explain, never auto-act
            f["outcome"] = "needs_user"
            continue
        if f["id"] in disabled:                     # owner opted this condition out of auto-fix
            f["outcome"] = "needs_user"
            continue
        if fix.get("action") in denied_actions:     # owner forbade this action entirely
            f["outcome"] = "needs_user"
            continue
        if not policy_allows(fix.get("tier", "risky"), level):
            f["outcome"] = "needs_user"
            continue
        guard = fix.get("guard")
        if guard:
            fn = GUARDS.get(guard)
            try:
                safe = bool(fn and fn(signals, ctx))
            except Exception:
                safe = False
            if not safe:                            # unsafe right now -> explain, don't act
                f["outcome"] = "blocked_guard"
                continue
        # Hold for owner approval when the condition is confirm-required, or when the action
        # would require a reboot and the owner hasn't opted into reboot-class actions. `force`
        # (a one-tap approval) overrides either hold for this pass.
        needs_reboot = bool(_action_meta(fix.get("action")).get("needs_reboot"))
        held = (f["id"] in confirm) or (needs_reboot and not allow_reboot)
        if held and f["id"] not in force and not dry_run:
            f["outcome"] = "awaiting_confirm"
            continue
        if not breaker.allow(f["id"], now):
            f["outcome"] = "gave_up"
            continue
        if dry_run:                                 # would act, but the owner asked us not to
            f["outcome"] = "would_fix"
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
        if recollect is None:                       # can't verify -> unknown stays unknown
            f["outcome"] = "executed_verification_unknown"
            continue
        try:
            fresh = recollect()
        except Exception:
            f["outcome"] = "executed_verification_unknown"
            continue
        verify_state = f.get("_verify_state")
        if callable(verify_state):
            try:
                verified = verify_state(fresh)
            except Exception:
                verified = None
            if verified is True:
                f["outcome"] = "fixed"
            elif verified is False:
                f["outcome"] = "fix_failed"
            else:
                f["outcome"] = "executed_verification_unknown"
        else:
            f["outcome"] = "fix_failed" if f["_detect"](fresh) else "fixed"
    return findings



# ======================================================================================
# Patient Chart v1 — bounded device-specific memory, not an unlimited log archive
# ======================================================================================
class PatientChart:
    SCHEMA = 1

    def __init__(self, path, *, max_remedies=100):
        self.path = path
        self.max_remedies = max(10, int(max_remedies))
        self.data = {
            "schema": self.SCHEMA,
            "identity": {},
            "known_good": {},
            "coverage": {},
            "status": None,
            "chronic": {},
            "remedies": [],
            "updated_at": None,
        }
        self.load()

    def load(self):
        try:
            if self.path and os.path.exists(self.path):
                with open(self.path, "rt", encoding="utf-8") as fp:
                    obj = json.load(fp)
                if isinstance(obj, dict) and obj.get("schema") == self.SCHEMA:
                    for key in self.data:
                        if key in obj:
                            self.data[key] = obj[key]
        except Exception as exc:
            logging.debug("[doctor] patient chart load failed: %s", exc)
        return self

    def _write(self):
        if not self.path:
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

    def summary(self):
        chronic = self.data.get("chronic") or {}
        recurring = sum(1 for row in chronic.values()
                        if isinstance(row, dict) and int(row.get("episodes", 0)) >= 2)
        return {
            "schema": self.data.get("schema"),
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
    __version__ = "0.6.0-pre3"
    __license__ = "GPL3"
    __description__ = "Autonomous health scan, diagnosis, causal explanation, guarded self-healing and known-good drift."

    def __init__(self):
        self.options = dict()
        self._findings = []
        self._status = "OK"
        self._causal = []
        self._breaker = CircuitBreaker()
        self._open = {}          # id -> {opened_at, severity, summary, snapshot}
        self._history = []
        self._breaker_path = None
        self._patient = None
        self._bundled_conditions = []
        self._external_conditions = []
        self._pack_conditions = []
        self._pack_errors = []

    def _read_options(self):
        """Parse options into attrs. Called on load AND on_config_changed (live-editable)."""
        self._autofix = normalize_level(self.options.get("autofix", "conservative"))
        self._dry_run = bool(self.options.get("dry_run", False))
        self._disabled = set(self.options.get("disable_autofix", []) or [])
        self._confirm_required = set(self.options.get("confirm_required", []) or [])
        self._deny_actions = set(self.options.get("deny_actions", []) or [])
        self._allow_reboot = bool(self.options.get("allow_reboot_actions", False))
        self._scan_every = int(self.options.get("scan_every", 30))
        self._boot_grace = float(self.options.get("boot_grace_s", 25))
        self._log_path = self.options.get("log_path", "/etc/pwnagotchi/log/pwnagotchi.log")
        self._config_path = self.options.get("config_path", "/etc/pwnagotchi/config.toml")
        self._handshakes = self.options.get("handshakes", "/root/handshakes")
        self._incident_path = self.options.get("incident_path",
                                               "/etc/pwnagotchi/doctor_incidents.json")
        self._checkpoint_path = self.options.get("checkpoint_path",
                                                 "/etc/pwnagotchi/doctor_known_good.json")
        self._breaker_path = self.options.get("breaker_path",
                                              "/etc/pwnagotchi/doctor_breaker.json")
        self._patient_path = self.options.get("patient_path",
                                              "/var/lib/pwnagotchi/doctor/patient.json")
        self._condition_dir = self.options.get("condition_dir",
                                               "/etc/pwnagotchi/doctor.d")
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

        # Ordering is authority: core Python conditions win first, then first-party bundled
        # packs, then external packs. diagnose() also de-duplicates ids in that order.
        self._pack_conditions = self._bundled_conditions + self._external_conditions
        self._pack_errors = bundled_errors + external_errors
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

        return s

    # -- the autonomous loop -----------------------------------------------------------
    def scan(self, runner=None, now=None, force_ids=None):
        now = now if now is not None else time.time()
        signals = self.collect(runner)
        findings = diagnose(signals, extra_conditions=self._pack_conditions)
        acting = self._autofix not in ("off", "observe", "notify") and not self._dry_run
        # confirm-required conditions (and reboot-class actions) wait for owner approval;
        # force_ids (from the web "Confirm & apply" link) approve a specific one for this pass.
        apply_fixes(findings, signals, self._autofix, runner or self._run,
                    self._breaker, self._ctx(),
                    recollect=(lambda: self.collect(runner)) if acting else None,
                    now=now, dry_run=self._dry_run, disabled=self._disabled,
                    confirm=self._confirm_required, force=set(force_ids or ()),
                    denied_actions=self._deny_actions, allow_reboot=self._allow_reboot)
        self._save_breaker()
        self._findings = findings
        self._status = overall_status(findings)
        self._causal = build_causal(f["id"] for f in findings)
        self._update_incidents(findings, signals, now)
        if self._patient is not None:
            self._patient.observe(signals, findings, self._status, now=now,
                                  known_good=self.load_checkpoint())
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
        force_ids = None
        try:
            if request is not None:
                cid = request.args.get("confirm")
                if cid:
                    force_ids = {cid}
        except Exception:
            force_ids = None
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
        if not self._findings:
            body = mode + "<p><b>OK</b> — no issues detected. 🎉</p>"
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
            body = (mode + "<p>Status: <b>{st}</b> — auto-fixed {nf}, needs you {nn}</p>{causal}"
                    "<table border=1><tr><th>sev</th><th>confidence</th><th>symptom</th>"
                    "<th>cause</th><th>outcome</th><th>what to do</th></tr>{rows}</table>").format(
                        st=self._status, nf=len(fixed), nn=len(need), causal=causal,
                        rows="".join(block(f) for f in self._findings))
        return "<html><body><h1>Doctor</h1>{}{}</body></html>".format(body, drift)
