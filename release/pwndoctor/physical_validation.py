#!/usr/bin/env python3
"""PwnDoctor guided physical-validation recorder.

Offline, standard-library-only release tool. It records evidence; it does not change Pwnagotchi
configuration, services, interfaces, storage, or Doctor Standing Orders.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import subprocess
import time
from pathlib import Path


SCHEMA = "pwndoctor/physical-validation/v1"
RESULTS = {"pass", "fail", "skip", "pending"}

CHECKS = (
    ("clean_install", "Clean install + reboot load", True),
    ("webui_opens", "Doctor WebUI opens", True),
    ("observe_mode", "Observe mode produces sensible findings", True),
    ("dry_run", "Dry-run reports would-fix without mutation", True),
    ("safe_remedy", "One conservative safe remedy executes and verifies", True),
    ("confirm_flow", "Confirm-required hold + approval flow works", True),
    ("breaker_restart", "Persistent circuit breaker survives restart", True),
    ("patient_chart", "Patient Chart persists without scan-by-scan writes", True),
    ("known_good", "Known-good checkpoint save/diff works", True),
    ("bundled_provenance", "Bundled Condition Pack provenance is correct", True),
    ("external_explain_only", "External pack remains explain-only by default", True),
    ("bad_pack_safe", "Malformed/oversized pack fails safely", True),
    ("optional_command", "Missing optional command degrades safely", True),
    ("radio_monitor", "Radio/monitor failure case diagnosed correctly", True),
    ("invalid_config", "Invalid config case diagnosed safely", True),
    ("media_guard", "Read-only/media-error guard blocks unsafe mutation", True),
    ("verification_unknown", "Missing verification evidence remains unknown", True),
    ("narrative", "Plain-language narrative is coherent", True),
    ("support_bundle", "Sanitized support bundle is generated and inspected", True),
)


def _read_os_release(path="/etc/os-release"):
    out = {}
    try:
        for raw in Path(path).read_text(errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            out[key.strip()] = value
    except Exception:
        pass
    return out


def _pwnagotchi_version():
    try:
        import pwnagotchi  # type: ignore
        value = getattr(pwnagotchi, "__version__", None)
        if value:
            return str(value)
    except Exception:
        pass
    try:
        proc = subprocess.run(
            ["pwnagotchi", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3,
            check=False,
        )
        raw = (proc.stdout or proc.stderr or "").strip().splitlines()
        if raw:
            return raw[0].split()[-1]
    except Exception:
        pass
    return None


def doctor_version_from_source(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Doctor":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "__version__":
                            return str(ast.literal_eval(stmt.value))
    raise RuntimeError("Doctor.__version__ not found")


def compatibility_fingerprint():
    osr = _read_os_release()
    model = None
    try:
        model = Path("/proc/device-tree/model").read_text(errors="ignore").replace("\x00", "").strip()
    except Exception:
        pass
    return {
        "hardware": model or platform.machine() or None,
        "architecture": platform.machine() or None,
        "kernel": platform.release() or None,
        "python": platform.python_version() or None,
        "pwnagotchi_version": _pwnagotchi_version(),
        "os_id": osr.get("ID"),
        "os_version_id": osr.get("VERSION_ID"),
        "os_build_id": osr.get("BUILD_ID") or osr.get("IMAGE_ID"),
        "image": osr.get("PRETTY_NAME") or osr.get("NAME"),
    }


def new_record(doctor_version, *, artifact_sha256=None, now=None, compatibility=None):
    now = float(time.time() if now is None else now)
    return {
        "schema": SCHEMA,
        "doctor_version": str(doctor_version),
        "artifact_sha256": artifact_sha256,
        "started_at": now,
        "updated_at": now,
        "compatibility": dict(compatibility or compatibility_fingerprint()),
        "checks": [
            {
                "id": check_id,
                "label": label,
                "required": bool(required),
                "result": "pending",
                "notes": "",
                "updated_at": None,
            }
            for check_id, label, required in CHECKS
        ],
    }


def set_result(record, check_id, result, *, notes="", now=None):
    result = str(result).lower().strip()
    if result not in RESULTS:
        raise ValueError("result must be one of: %s" % ", ".join(sorted(RESULTS)))
    now = float(time.time() if now is None else now)
    for row in record.get("checks") or []:
        if row.get("id") == check_id:
            row["result"] = result
            row["notes"] = str(notes or "")[:2000]
            row["updated_at"] = now
            record["updated_at"] = now
            return row
    raise KeyError("unknown validation check: %s" % check_id)


def validation_summary(record):
    rows = [x for x in (record.get("checks") or []) if isinstance(x, dict)]
    counts = {name: sum(1 for row in rows if row.get("result") == name)
              for name in ("pass", "fail", "skip", "pending")}
    required = [row for row in rows if row.get("required")]
    ready = bool(required) and all(row.get("result") == "pass" for row in required)
    return {
        "counts": counts,
        "required_count": len(required),
        "ready_for_physical_validated": ready,
    }


def compatibility_matrix_row(record, row_id=None):
    summary = validation_summary(record)
    if not summary["ready_for_physical_validated"]:
        raise ValueError("physical validation is incomplete or has failures")
    compat = record.get("compatibility") or {}
    return {
        "id": row_id or "physical-%d" % int(record.get("updated_at") or time.time()),
        "evidence": "physical_validated",
        "pwnagotchi_version": compat.get("pwnagotchi_version"),
        "image": compat.get("image"),
        "hardware": compat.get("hardware"),
        "architecture": compat.get("architecture"),
        "python": compat.get("python"),
        "kernel": compat.get("kernel"),
        "notes": "PwnDoctor %s physical checklist passed; artifact_sha256=%s" % (
            record.get("doctor_version"),
            record.get("artifact_sha256") or "not-recorded",
        ),
    }


def write_record(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, path)
    return path


def load_record(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != SCHEMA:
        raise ValueError("unsupported physical-validation record")
    return obj


def _prompt(record, output):
    for row in record["checks"]:
        current = row.get("result", "pending")
        print("\n[%s] %s" % (row["id"], row["label"]))
        if row.get("notes"):
            print("  notes:", row["notes"])
        raw = input("result [p=pass/f=fail/s=skip/enter=%s/q=quit]: " % current).strip().lower()
        if raw == "q":
            write_record(output, record)
            return
        mapping = {"p": "pass", "f": "fail", "s": "skip"}
        if raw in mapping:
            notes = input("notes (optional): ").strip()
            set_result(record, row["id"], mapping[raw], notes=notes)
            write_record(output, record)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doctor", default="doctor.py", help="path to doctor.py")
    ap.add_argument("--output", default="physical-validation.json")
    ap.add_argument("--artifact-sha256")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--matrix-row", action="store_true")
    args = ap.parse_args()

    output = Path(args.output)
    if args.resume and output.exists():
        record = load_record(output)
    else:
        record = new_record(
            doctor_version_from_source(args.doctor),
            artifact_sha256=args.artifact_sha256,
        )
        write_record(output, record)

    if args.summary:
        print(json.dumps(validation_summary(record), indent=2, sort_keys=True))
        return 0
    if args.matrix_row:
        print(json.dumps(compatibility_matrix_row(record), indent=2, sort_keys=True))
        return 0

    _prompt(record, output)
    summary = validation_summary(record)
    print("\nSaved:", output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not summary["counts"]["fail"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
