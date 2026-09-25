#!/usr/bin/env python3
"""Fetch one Condition Pack into PwnDoctor's cached catalog with pinned SHA-256.

This utility is opt-in. It stages knowledge only; cached catalog packs are explain-only at
runtime and gain no treatment authority by being fetched or signed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 128 * 1024


def fetch_pack(url, expected_sha256, output_dir, *, max_bytes=MAX_BYTES):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("catalog fetch requires https://")
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("expected SHA-256 must be 64 lowercase/uppercase hex characters")
    req = urllib.request.Request(url, headers={"User-Agent": "PwnDoctor-catalog-fetch/1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read(int(max_bytes) + 1)
    if len(raw) > int(max_bytes):
        raise ValueError("download exceeds %d byte limit" % int(max_bytes))
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("SHA-256 mismatch: %s != %s" % (actual, expected))
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != "condition-pack/v1":
        raise ValueError("download is not a condition-pack/v1 JSON object")
    pack_id = obj.get("id")
    if not isinstance(pack_id, str) or not pack_id:
        raise ValueError("pack id missing")
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in pack_id) + ".json"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / safe_name
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_bytes(raw)
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, out)
    return {"path": str(out), "sha256": actual, "id": pack_id, "authority": "explain_only"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--output-dir", default="/var/lib/pwnagotchi/doctor/catalog.d")
    args = ap.parse_args()
    row = fetch_pack(args.url, args.sha256, args.output_dir)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
