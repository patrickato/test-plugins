#!/usr/bin/env python3
"""Assemble a standalone PwnDoctor release tree from canonical test-plugins sources."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGINS = REPO / "pwnagotchi-plugins"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def doctor_version() -> str:
    tree = ast.parse((PLUGINS / "doctor.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Doctor":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "__version__":
                            return ast.literal_eval(stmt.value)
    raise RuntimeError("Doctor.__version__ not found")


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise FileNotFoundError(src)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def assemble(output_root: Path) -> Path:
    version = doctor_version()
    package = output_root / f"pwndoctor-{version}"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir(parents=True)

    copy_file(PLUGINS / "doctor.py", package / "doctor.py")
    copy_tree(PLUGINS / "doctor_packs", package / "doctor_packs")

    copy_file(PLUGINS / "doctor.config.toml", package / "examples" / "doctor.config.toml")
    copy_tree(PLUGINS / "doctor.d", package / "examples" / "doctor.d")

    copy_file(PLUGINS / "CONDITION_PACK_SCHEMA.md",
              package / "docs" / "CONDITION_PACK_SCHEMA.md")
    copy_file(PLUGINS / "DOCTOR_ROADMAP.md",
              package / "docs" / "DEVELOPMENT_ROADMAP.md")
    copy_file(PLUGINS / "DOCTOR_COMPATIBILITY_CONTRACT.md",
              package / "docs" / "UPSTREAM_COMPATIBILITY_CONTRACT.md")

    for name in (
        "README.md", "INSTALL.md", "CONFIGURATION.md", "DEPENDENCIES.md", "USAGE.md",
        "SECURITY_AND_SAFETY.md", "COMPATIBILITY.md", "TROUBLESHOOTING.md",
        "RELEASE_CHECKLIST.md", "RC_READINESS.md", "PHYSICAL_VALIDATION.md",
        "CHANGELOG.md", "PACKAGE_MANIFEST.md",
    ):
        copy_file(HERE / name, package / ("README.md" if name == "README.md" else f"docs/{name}"))

    copy_file(HERE / "COMPATIBILITY_MATRIX.json", package / "COMPATIBILITY_MATRIX.json")
    copy_file(HERE / "install.sh", package / "install.sh")
    copy_file(REPO / "LICENSE", package / "LICENSE")

    copy_file(PLUGINS / "tests" / "test_doctor.py", package / "tests" / "test_doctor.py")
    copy_file(PLUGINS / "tests" / "conftest.py", package / "tests" / "conftest.py")
    copy_file(PLUGINS / "requirements-dev.txt", package / "requirements-dev.txt")

    files = {}
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        rel = path.relative_to(package).as_posix()
        files[rel] = sha256(path)

    pack_inventory = []
    packs_root = package / "doctor_packs"
    for path in sorted(packs_root.glob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        pack_inventory.append({
            "file": path.name,
            "id": obj.get("id"),
            "version": obj.get("version"),
            "sha256": sha256(path),
            "has_fix": isinstance(obj.get("fix"), dict),
        })

    manifest = {
        "name": "PwnDoctor",
        "version": version,
        "format": 1,
        "files": files,
        "condition_packs": pack_inventory,
        "condition_pack_count": len(pack_inventory),
        "compatibility_matrix": "COMPATIBILITY_MATRIX.json",
    }
    manifest_path = package / "RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")

    sums = []
    for path in sorted(p for p in package.rglob("*") if p.is_file()
                       and p.name != "SHA256SUMS"):
        sums.append(f"{sha256(path)}  {path.relative_to(package).as_posix()}")
    (package / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")

    verify(package)
    return package


def verify(package: Path) -> None:
    manifest_path = package / "RELEASE_MANIFEST.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel, expected in data["files"].items():
        path = package / rel
        if not path.is_file():
            raise RuntimeError(f"missing packaged file: {rel}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"hash mismatch for {rel}: {actual} != {expected}")

    packs = data.get("condition_packs") or []
    if data.get("condition_pack_count") != len(packs):
        raise RuntimeError("condition pack count does not match inventory")
    seen_ids = set()
    for row in packs:
        rel = "doctor_packs/" + str(row.get("file") or "")
        path = package / rel
        if not path.is_file():
            raise RuntimeError(f"missing inventoried condition pack: {rel}")
        if sha256(path) != row.get("sha256"):
            raise RuntimeError(f"condition pack hash mismatch: {rel}")
        pack = json.loads(path.read_text(encoding="utf-8"))
        if pack.get("id") != row.get("id"):
            raise RuntimeError(f"condition pack id mismatch: {rel}")
        if pack.get("id") in seen_ids:
            raise RuntimeError(f"duplicate condition pack id: {pack.get('id')}")
        seen_ids.add(pack.get("id"))

    matrix_path = package / str(data.get("compatibility_matrix") or "")
    if not matrix_path.is_file():
        raise RuntimeError("missing compatibility matrix")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    if matrix.get("schema") != 1 or not isinstance(matrix.get("rows"), list):
        raise RuntimeError("invalid compatibility matrix")

    sums = package / "SHA256SUMS"
    if not sums.is_file():
        raise RuntimeError("missing SHA256SUMS")
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split("  ", 1)
        path = package / rel
        if sha256(path) != expected:
            raise RuntimeError(f"SHA256SUMS mismatch: {rel}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=HERE / "dist")
    ap.add_argument("--verify", type=Path,
                    help="verify an already assembled package instead of building")
    args = ap.parse_args()

    if args.verify:
        verify(args.verify.resolve())
        print(f"verified: {args.verify.resolve()}")
    else:
        package = assemble(args.output.resolve())
        print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
