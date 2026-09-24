"""doctor — autonomous health scanning, diagnosis, and (safe) self-healing.

Toggle it on (or hit its web page) and the Doctor scans everything it can reach — services,
power/throttle flags, disk & read-only SD, kernel messages, config validity, the bettercap
API, the monitor interface, the clock, plugin load state, temperature and the log — matches
them against a knowledge base of known Pwnagotchi ailments, and then:

  * auto-fixes the safe, reversible problems itself (restart a wedged service, unblock rfkill,
    fix the clock, reclaim disk from log bloat) and reports what it did, and
  * for riskier problems, gives you the diagnosis plus exact step-by-step instructions.

Everything is guarded so it works regardless of Pi model, screen, or setup: a sensor that
isn't available is simply skipped. Auto-fix is tiered and configurable, every action is
allow-listed and verified, a circuit breaker stops it from looping, and every scan is written
to an incident log.

Options (main.plugins.doctor.*):
    enabled       = true
    autofix       = "safe"     # "off" (diagnose only) | "safe" (auto low-risk) | "all"
    scan_every    = 30         # run a full scan every N epochs (0 = only on start / web)
    log_path      = "/etc/pwnagotchi/log/pwnagotchi.log"
    config_path   = "/etc/pwnagotchi/config.toml"
    incident_path = "/etc/pwnagotchi/doctor_incidents.json"
    min_free_mb   = 200
    max_temp_c    = 80
    services      = ["pwnagotchi", "bettercap", "pwngrid-peer"]
    position      = "0,0"

Requires: none (Python standard library; uses systemctl/iw/rfkill/vcgencmd/timedatectl when
present, all guarded). Auto-fix actions need root, which Pwnagotchi already runs as.
"""
import glob
import json
import logging
import os
import shutil
import subprocess
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

_SEV_RANK = {"high": 0, "warn": 1, "info": 2}


# ======================================================================================
# Pure parsers (unit-tested; no I/O)
# ======================================================================================
def parse_throttled(value):
    """Parse `vcgencmd get_throttled` (e.g. 'throttled=0x50005') into flags."""
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
    """Count known trouble signatures in kernel messages."""
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
    """True if / is mounted read-only (a classic silent killer)."""
    for line in (text or "").splitlines():
        f = line.split()
        if len(f) >= 4 and f[1] == "/":
            return "ro" in f[3].split(",")
    return False


def config_valid(text):
    """Validate config.toml text. Returns {valid, error}."""
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
            plugins_failed.append(ln.split("error while loading", 1)[1].strip().split()[0]
                                  if ln.split("error while loading", 1)[1].strip() else "?")
    return {
        "tracebacks": count("traceback"),
        "wifi_errors": count("wifi", "error"),
        "bettercap_refused": count("bettercap", "connection refused"),
        "pwngrid_errors": count("pwngrid", "error"),
        "bt_tether_errors": count("bt-tether", "error"),
        "plugins_failed": plugins_failed,
    }


# ======================================================================================
# Knowledge base: conditions (signature -> cause -> fix / how-to)
# ======================================================================================
def _svc_down(signals, name):
    svc = signals.get("services", {}).get(name)
    return svc is not None and svc.get("active") is False


CONDITIONS = [
    {"id": "sd_readonly", "severity": "high",
     "detect": lambda s: s.get("disk", {}).get("root_ro") is True,
     "symptom": "the root filesystem is mounted read-only",
     "cause": "the SD card hit an error and Linux remounted / read-only (writes silently fail)",
     "fix": {"action": "remount_rw", "tier": "risky"},
     "howto": ["Back up your data now — a read-only remount usually means the SD is failing.",
               "Try: sudo mount -o remount,rw /",
               "If it returns, reflash to a fresh, good-quality SD card soon."]},

    {"id": "disk_full", "severity": "high",
     "detect": lambda s: (s.get("disk", {}).get("free_mb") is not None
                          and s["disk"]["free_mb"] < s.get("_cfg", {}).get("min_free_mb", 200)),
     "symptom": "very low free disk space",
     "cause": "the SD card is nearly full (often log bloat or too many captures)",
     "fix": {"action": "prune_logs", "tier": "safe"},
     "howto": ["Enable the capture_retention plugin to prune old captures.",
               "Check /etc/pwnagotchi/log for oversized logs.",
               "df -h  and  du -sh /root/handshakes  to find the hog."]},

    {"id": "bettercap_down", "severity": "high",
     "detect": lambda s: (s.get("bettercap_reachable") is False
                          or _svc_down(s, "bettercap")
                          or s.get("log", {}).get("bettercap_refused", 0) >= 1),
     "symptom": "bettercap isn't reachable",
     "cause": "bettercap crashed or its API is down (no capturing happens without it)",
     "fix": {"action": "restart_service", "args": {"service": "bettercap"}, "tier": "safe"},
     "howto": ["sudo systemctl restart bettercap",
               "Check: sudo systemctl status bettercap  and  journalctl -u bettercap -n 50"]},

    {"id": "pwngrid_down", "severity": "warn",
     "detect": lambda s: _svc_down(s, "pwngrid-peer") or s.get("log", {}).get("pwngrid_errors", 0) >= 1,
     "symptom": "pwngrid-peer is unhappy",
     "cause": "the peer/grid service isn't running properly",
     "fix": {"action": "restart_service", "args": {"service": "pwngrid-peer"}, "tier": "safe"},
     "howto": ["sudo systemctl restart pwngrid-peer"]},

    {"id": "rfkill_blocked", "severity": "high",
     "detect": lambda s: s.get("rfkill_blocked") is True,
     "symptom": "Wi-Fi is soft-blocked (rfkill)",
     "cause": "the wireless radio is blocked, so nothing can be captured",
     "fix": {"action": "rfkill_unblock", "tier": "safe"},
     "howto": ["sudo rfkill unblock wifi"]},

    {"id": "no_monitor", "severity": "high",
     "detect": lambda s: s.get("monitor_present") is False,
     "symptom": "no monitor-mode interface found",
     "cause": "the adapter isn't in monitor mode or doesn't support it",
     "fix": None,
     "howto": ["Confirm your Wi-Fi adapter supports monitor mode.",
               "Check bettercap's interface (main.iface / bettercap config).",
               "iw dev  should list an interface of 'type monitor'."]},

    {"id": "clock_wrong", "severity": "high",
     "detect": lambda s: s.get("time", {}).get("year_ok") is False,
     "symptom": "the system clock looks wrong",
     "cause": "no RTC/NTP sync — a bad clock breaks TLS and wpa-sec uploads",
     "fix": {"action": "set_time", "tier": "safe"},
     "howto": ["sudo timedatectl set-ntp true  (needs internet)",
               "Or add an RTC module, or the rtc_fix/auto_timezone plugin."]},

    {"id": "config_invalid", "severity": "high",
     "detect": lambda s: s.get("config", {}).get("valid") is False,
     "symptom": "config.toml does not parse",
     "cause": "a syntax error (often a hand-edit or a plugin rewrite) — Pwnagotchi may not start",
     "fix": {"action": "restore_config", "tier": "risky"},
     "howto": ["Fix the TOML syntax in /etc/pwnagotchi/config.toml.",
               "Restore a backup: cp /etc/pwnagotchi/config.toml.doctor.bak /etc/pwnagotchi/config.toml"]},

    {"id": "plugin_crash_loop", "severity": "high",
     "detect": lambda s: (s.get("log", {}).get("tracebacks", 0) >= 3
                          or len(s.get("log", {}).get("plugins_failed", [])) >= 1),
     "symptom": "a plugin is crashing / failed to load",
     "cause": "a third-party plugin is raising exceptions",
     "fix": {"action": "quarantine_plugin", "tier": "risky"},
     "howto": ["Find the plugin in the log ('error while loading' / traceback).",
               "Disable it: set main.plugins.<name>.enabled = false in config.toml.",
               "Restart: sudo systemctl restart pwnagotchi."]},

    {"id": "undervoltage", "severity": "high",
     "detect": lambda s: (s.get("throttled", {}).get("undervoltage_now")
                          or s.get("throttled", {}).get("undervoltage_occurred")
                          or s.get("dmesg", {}).get("undervoltage", 0) >= 1),
     "symptom": "under-voltage detected",
     "cause": "the power supply/cable can't deliver enough current (causes crashes & corruption)",
     "fix": None,
     "howto": ["Use a good 5V/3A supply and a short, thick USB cable.",
               "Avoid powering from a weak hub or PC port."]},

    {"id": "overheat", "severity": "warn",
     "detect": lambda s: (s.get("temp_c") is not None
                          and s["temp_c"] >= s.get("_cfg", {}).get("max_temp_c", 80)),
     "symptom": "high temperature",
     "cause": "sustained load or poor cooling (leads to throttling)",
     "fix": None,
     "howto": ["Add a heatsink/fan (see the fan_curve plugin).",
               "Improve enclosure airflow."]},

    {"id": "sd_errors", "severity": "high",
     "detect": lambda s: s.get("dmesg", {}).get("sd_error", 0) >= 1,
     "symptom": "SD card I/O errors in the kernel log",
     "cause": "the SD card is degrading",
     "fix": None,
     "howto": ["Back up now. Reflash to a fresh, reputable SD card.",
               "See the sd_wear plugin to track write wear."]},

    {"id": "oom", "severity": "warn",
     "detect": lambda s: s.get("dmesg", {}).get("oom", 0) >= 1,
     "symptom": "out-of-memory kills detected",
     "cause": "something is using too much RAM",
     "fix": None,
     "howto": ["Disable heavy plugins; check for a memory leak.",
               "Consider adding swap (carefully — SD wear)."]},

    {"id": "usb_resets", "severity": "warn",
     "detect": lambda s: s.get("dmesg", {}).get("usb_reset", 0) >= 3,
     "symptom": "repeated USB resets",
     "cause": "flaky USB power/cable/hub (often the Wi-Fi adapter dropping)",
     "fix": None,
     "howto": ["Use a powered hub or better cable for USB adapters.",
               "Check the supply can handle the adapter's draw."]},
]


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
                "id": c["id"], "severity": c["severity"], "symptom": c["symptom"],
                "cause": c["cause"], "howto": list(c.get("howto", [])),
                "fix": c.get("fix"), "_detect": c["detect"], "outcome": "detected",
            })
    findings.sort(key=lambda f: _SEV_RANK.get(f["severity"], 9))
    return findings


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
        shutil.copy2(path, path + ".doctor.bak")   # snapshot before edit
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
    "prune_logs": act_prune_logs,
    "restore_config": act_restore_config,
    "quarantine_plugin": act_quarantine_plugin,
}


class CircuitBreaker:
    """Stops the Doctor from attempting the same fix endlessly."""
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
    """Attempt allowed fixes; verify; set each finding's outcome. Returns findings."""
    now = now if now is not None else time.time()
    for f in findings:
        fix = f.get("fix")
        if not fix:
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
class Doctor(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.2.0"
    __license__ = "GPL3"
    __description__ = "Autonomous health scan, diagnosis and safe self-healing."

    def __init__(self):
        self.options = dict()
        self._findings = []
        self._last_report = {"fixed": [], "needs_user": [], "observed": []}
        self._breaker = CircuitBreaker()
        self._incidents = []

    def on_loaded(self):
        self._autofix = str(self.options.get("autofix", "safe"))
        self._scan_every = int(self.options.get("scan_every", 30))
        self._log_path = self.options.get("log_path", "/etc/pwnagotchi/log/pwnagotchi.log")
        self._config_path = self.options.get("config_path", "/etc/pwnagotchi/config.toml")
        self._incident_path = self.options.get("incident_path",
                                               "/etc/pwnagotchi/doctor_incidents.json")
        self._min_free_mb = int(self.options.get("min_free_mb", 200))
        self._max_temp_c = float(self.options.get("max_temp_c", 80))
        self._services = list(self.options.get("services",
                              ["pwnagotchi", "bettercap", "pwngrid-peer"]))
        logging.info("[doctor] loaded (autofix=%s)", self._autofix)

    # -- context for actions -----------------------------------------------------------
    def _ctx(self):
        return {"log_path": self._log_path, "config_path": self._config_path,
                "log_max_bytes": 5 * 1024 * 1024, "log_keep_lines": 1000}

    # -- collectors (guarded) ----------------------------------------------------------
    @staticmethod
    def _run(cmd):
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=6)

    def collect(self, runner=None):
        runner = runner or self._run
        s = {"_cfg": {"min_free_mb": self._min_free_mb, "max_temp_c": self._max_temp_c}}

        # services
        services = {}
        for name in self._services:
            try:
                out = runner(["systemctl", "is-active", name]).strip()
                services[name] = {"active": out == "active"}
            except subprocess.CalledProcessError as e:
                services[name] = {"active": (e.output or "").strip() == "active"}
            except Exception:
                pass
        s["services"] = services

        # throttle
        try:
            s["throttled"] = parse_throttled(runner(["vcgencmd", "get_throttled"]))
        except Exception:
            s["throttled"] = {}

        # disk
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

        # dmesg
        try:
            s["dmesg"] = parse_dmesg(runner(["dmesg", "--ctime"]))
        except Exception:
            s["dmesg"] = {}

        # config validity
        try:
            with open(self._config_path, "rt", errors="ignore") as fp:
                s["config"] = config_valid(fp.read())
        except Exception:
            s["config"] = {"valid": True, "error": None}

        # bettercap reachable
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8081/api/session", timeout=2)
            s["bettercap_reachable"] = True
        except Exception as e:
            # 401 means it's up but needs auth -> reachable
            s["bettercap_reachable"] = "401" in str(e)

        # interfaces / rfkill
        try:
            s["monitor_present"] = iw_has_monitor(runner(["iw", "dev"]))
        except Exception:
            s["monitor_present"] = None
        try:
            s["rfkill_blocked"] = "yes" in runner(["rfkill", "list", "wifi"]).lower()
        except Exception:
            s["rfkill_blocked"] = None

        # time
        year_ok = time.gmtime().tm_year >= 2024
        s["time"] = {"year_ok": year_ok}

        # temperature
        try:
            s["temp_c"] = float(pwnagotchi.temperature())
        except Exception:
            s["temp_c"] = None

        # log
        try:
            with open(self._log_path, "rt", errors="ignore") as fp:
                s["log"] = parse_log_signals("".join(fp.readlines()[-400:]))
        except Exception:
            s["log"] = {}

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
        report = {
            "fixed": [f for f in findings if f["outcome"] == "fixed"],
            "needs_user": [f for f in findings if f["outcome"] in ("needs_user", "fix_failed", "gave_up")],
            "observed": findings,
        }
        self._last_report = report
        self._record_incident(report, now)
        if findings:
            logging.info("[doctor] scan: %d issue(s), %d auto-fixed",
                         len(findings), len(report["fixed"]))
        return report

    def _record_incident(self, report, now):
        entry = {"t": now, "fixed": [f["id"] for f in report["fixed"]],
                 "needs_user": [f["id"] for f in report["needs_user"]]}
        if not entry["fixed"] and not entry["needs_user"]:
            return
        self._incidents.append(entry)
        self._incidents = self._incidents[-200:]
        try:
            os.makedirs(os.path.dirname(self._incident_path), exist_ok=True)
            with open(self._incident_path, "w") as fp:
                json.dump(self._incidents, fp)
        except Exception as e:
            logging.debug("[doctor] incident write failed: %s", e)

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self.scan()

    def on_epoch(self, agent, epoch, epoch_data):
        if self._scan_every and epoch % self._scan_every == 0:
            self.scan()

    # -- UI ----------------------------------------------------------------------------
    def _ui_value(self):
        need = len(self._last_report["needs_user"])
        fixed = len(self._last_report["fixed"])
        if need:
            return "%d!" % need
        if fixed:
            return "healed"
        return "OK"

    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("doctor", LabeledValue(color=BLACK, label="dr:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("doctor", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("doctor"):
                ui.remove_element("doctor")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        self.scan()
        r = self._last_report
        if not r["observed"]:
            inner = "<p>No issues detected. 🎉</p>"
        else:
            def block(f):
                steps = "".join("<li>%s</li>" % h for h in f.get("howto", []))
                return ("<tr><td>{sev}</td><td>{sym}</td><td>{cause}</td>"
                        "<td>{outcome}</td><td><ol>{steps}</ol></td></tr>").format(
                            sev=f["severity"], sym=f["symptom"], cause=f["cause"],
                            outcome=f["outcome"], steps=steps)
            inner = ("<p>Auto-fixed: {nf} &nbsp;|&nbsp; Needs you: {nn}</p>"
                     "<table border=1><tr><th>severity</th><th>symptom</th><th>cause</th>"
                     "<th>outcome</th><th>what to do</th></tr>{rows}</table>").format(
                        nf=len(r["fixed"]), nn=len(r["needs_user"]),
                        rows="".join(block(f) for f in r["observed"]))
        return "<html><body><h1>Doctor</h1>{}</body></html>".format(inner)
