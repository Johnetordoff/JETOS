#!/usr/bin/env python3
"""JETOS Gen2 frozen-source intake, sealing, verification, and census."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
GEN2 = ROOT / "gen2"
VENDOR = GEN2 / "vendor"
MANIFEST = GEN2 / "manifest.json"
SEED_ROOT = ROOT / "sources"

COMPONENTS = {
    "jetos-python": (SEED_ROOT / "cpython", VENDOR / "jetos-python"),
    "jetos-kernel": (SEED_ROOT / "linux", VENDOR / "jetos-kernel"),
}

SKIP_PARTS = {".git", "__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ordinary_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        yield path, rel


def copy_component(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit(
            f"missing Gen2 intake seed: {source}\n"
            "Materialize the one-time intake seed on the authorized development/controller "
            "machine first; Gen2 build/boot never fetches it automatically."
        )
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo"),
    )


def internalize_jetos_python(source: Path) -> None:
    """Turn the admitted Python seed into JetOS Python before the Gen2 seal."""
    sysmodule = source / "Python/sysmodule.c"
    if not sysmodule.is_file():
        raise SystemExit("JetOS Python intake is missing Python/sysmodule.c")
    text = sysmodule.read_text(encoding="utf-8")
    if '#define NAME "cpython"' in text:
        text = text.replace('#define NAME "cpython"', '#define NAME "jetos"', 1)
    if '#define NAME "jetos"' not in text:
        raise SystemExit("could not install JetOS Python implementation identity")

    # Remove old seed-identity runtime fields if the legacy intake tooling added them.
    text = "\n".join(
        line for line in text.splitlines()
        if "jetos_python_base_version" not in line
    ) + "\n"
    include_line = '#include "jetos.h"          // JETOS Language identity'
    if include_line not in text:
        python_include = '#include "Python.h"'
        if python_include not in text:
            raise SystemExit("could not locate Python.h include for JetOS Python identity")
        text = text.replace(python_include, python_include + "\n" + include_line, 1)
    sysmodule.write_text(text, encoding="utf-8")

    header = source / "Include/jetos.h"
    header.write_text(
        "#ifndef Py_JETOS_H\n"
        "#define Py_JETOS_H\n\n"
        "/* JetOS Python identity. Historical intake provenance is not runtime identity. */\n"
        '#define JETOS_PYTHON_GENERATION "Gen2"\n'
        "\n#endif /* Py_JETOS_H */\n",
        encoding="utf-8",
    )


def build_manifest() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    components: dict[str, dict[str, object]] = {}
    for name, (_, root) in COMPONENTS.items():
        count = 0
        size = 0
        if not root.is_dir():
            raise SystemExit(f"Gen2 component is missing: {root}")
        for path, rel in ordinary_files(root):
            stat = path.stat()
            rows.append({
                "component": name,
                "path": rel.as_posix(),
                "bytes": stat.st_size,
                "sha256": digest(path),
            })
            count += 1
            size += stat.st_size
        components[name] = {"files": count, "bytes": size}
    return {
        "format": "jetos-gen2-manifest-v1",
        "generation": "Gen2",
        "sealed_ts": time.time(),
        "components": components,
        "files": rows,
    }


def write_manifest(payload: dict[str, object]) -> None:
    GEN2.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def intake() -> None:
    for _, (source, target) in COMPONENTS.items():
        copy_component(source, target)
    internalize_jetos_python(VENDOR / "jetos-python")
    payload = build_manifest()
    write_manifest(payload)
    print("JETOS Gen2 source intake sealed.")
    print(f"  manifest: {MANIFEST}")
    for name, info in payload["components"].items():
        print(f"  {name}: {info['files']:,} files, {info['bytes']:,} bytes")


def load_manifest() -> dict[str, object]:
    if not MANIFEST.is_file():
        raise SystemExit("Gen2 is not sealed: gen2/manifest.json is missing")
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if value.get("format") != "jetos-gen2-manifest-v1":
        raise SystemExit("unsupported Gen2 manifest format")
    return value


def verify() -> None:
    payload = load_manifest()
    expected = payload.get("files")
    if not isinstance(expected, list):
        raise SystemExit("invalid Gen2 manifest file list")
    failures: list[str] = []
    seen: set[tuple[str, str]] = set()
    roots = {name: target for name, (_, target) in COMPONENTS.items()}
    for row in expected:
        if not isinstance(row, dict):
            failures.append("invalid manifest row")
            continue
        component = str(row.get("component") or "")
        relative = str(row.get("path") or "")
        seen.add((component, relative))
        root = roots.get(component)
        if root is None:
            failures.append(f"unknown component {component}")
            continue
        path = root / relative
        if not path.is_file():
            failures.append(f"missing {component}/{relative}")
            continue
        stat = path.stat()
        if stat.st_size != int(row.get("bytes") or -1):
            failures.append(f"size changed {component}/{relative}")
            continue
        if digest(path) != row.get("sha256"):
            failures.append(f"hash changed {component}/{relative}")
    for component, root in roots.items():
        if not root.is_dir():
            failures.append(f"component missing {component}")
            continue
        for _, rel in ordinary_files(root):
            if (component, rel.as_posix()) not in seen:
                failures.append(f"unsealed file {component}/{rel.as_posix()}")
    if failures:
        raise SystemExit("Gen2 verification FAILED:\n  " + "\n  ".join(failures[:100]))
    print(f"JETOS Gen2 verification: PASS ({len(expected):,} sealed files)")


def census() -> None:
    verify()
    suffixes: Counter[str] = Counter()
    total = 0
    for _, (_, root) in COMPONENTS.items():
        for path, _ in ordinary_files(root):
            suffixes[path.suffix if path.suffix else "[no extension]"] += 1
            total += 1
    print(f"Gen2 source files: {total:,}")
    for suffix, count in suffixes.most_common():
        print(f"  {suffix}: {count:,}")


def status() -> None:
    print("JETOS Gen2")
    print(f"  sealed: {MANIFEST.is_file()}")
    for name, (_, target) in COMPONENTS.items():
        print(f"  {name}: {'present' if target.is_dir() else 'missing'} -> {target.relative_to(ROOT)}")
    if MANIFEST.is_file():
        verify()


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS Gen2 frozen source manager")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("intake", help="copy the current intake seeds into Gen2, internalize them, and seal")
    sub.add_parser("verify", help="verify every frozen Gen2 file")
    sub.add_parser("status", help="show Gen2 source presence and seal state")
    sub.add_parser("census", help="verify and count Gen2 source files by type")
    args = parser.parse_args()
    if args.command == "intake":
        intake()
    elif args.command == "verify":
        verify()
    elif args.command == "status":
        status()
    elif args.command == "census":
        census()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
