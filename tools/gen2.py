#!/usr/bin/env python3
"""JETOS Gen2 intake, seal verification, and source census."""
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
SEEDS = ROOT / "sources"
COMPONENTS = {
    "jetos-python": (SEEDS / "cpython", VENDOR / "jetos-python"),
    "jetos-kernel": (SEEDS / "linux", VENDOR / "jetos-kernel"),
}
SKIP_PARTS = {".git", "__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        yield path, rel


def copy_seed(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit(
            f"missing one-time Gen2 intake seed: {source}\n"
            "Materialize the seed on the authorized development/controller machine first. "
            "Sealed Gen2 never fetches source during build or boot."
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
    """Install the Gen2-native JetOS Python identity before source is sealed."""
    sysmodule = source / "Python/sysmodule.c"
    if not sysmodule.is_file():
        raise SystemExit("JetOS Python intake is missing Python/sysmodule.c")
    text = sysmodule.read_text(encoding="utf-8")
    text = text.replace('#define NAME "cpython"', '#define NAME "jetos"', 1)
    if '#define NAME "jetos"' not in text:
        raise SystemExit("could not install JetOS Python implementation identity")

    # Remove legacy seed-identity runtime fields.
    text = "\n".join(
        line for line in text.splitlines()
        if "jetos_python_base_version" not in line
        and "jetos_language_version" not in line
    ) + "\n"

    python_include = '#include "Python.h"'
    include_line = '#include "jetos.h"          // JetOS Python identity'
    # Normalize an older JETOS include comment if one exists.
    text = text.replace(
        '#include "jetos.h"          // JETOS Language identity',
        include_line,
    )
    if '#include "jetos.h"' not in text:
        if python_include not in text:
            raise SystemExit("could not locate Python.h include for JetOS Python")
        text = text.replace(python_include, python_include + "\n" + include_line, 1)

    marker = '    SET_SYS_FROM_STRING("version", Py_GetVersion());'
    generation_line = '    SET_SYS_FROM_STRING("jetos_python_generation", JETOS_PYTHON_GENERATION);'
    if generation_line not in text:
        if marker not in text:
            raise SystemExit("could not locate sys.version initialization")
        text = text.replace(marker, marker + "\n" + generation_line, 1)
    sysmodule.write_text(text, encoding="utf-8")

    (source / "Include/jetos.h").write_text(
        "#ifndef Py_JETOS_H\n"
        "#define Py_JETOS_H\n\n"
        "/* JetOS Python Gen2 identity. */\n"
        '#define JETOS_PYTHON_GENERATION "Gen2"\n'
        "\n#endif /* Py_JETOS_H */\n",
        encoding="utf-8",
    )


def manifest_data() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    summary: dict[str, dict[str, int]] = {}
    for name, (_, root) in COMPONENTS.items():
        if not root.is_dir():
            raise SystemExit(f"Gen2 component missing: {root}")
        count = total = 0
        for path, rel in files(root):
            size = path.stat().st_size
            rows.append({"component": name, "path": rel.as_posix(), "bytes": size, "sha256": sha256(path)})
            count += 1
            total += size
        summary[name] = {"files": count, "bytes": total}
    return {
        "format": "jetos-gen2-manifest-v1",
        "generation": "Gen2",
        "sealed_ts": time.time(),
        "components": summary,
        "files": rows,
    }


def intake() -> None:
    for source, target in COMPONENTS.values():
        copy_seed(source, target)
    internalize_jetos_python(VENDOR / "jetos-python")
    GEN2.mkdir(parents=True, exist_ok=True)
    payload = manifest_data()
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("JETOS Gen2 source intake sealed.")
    for name, info in payload["components"].items():
        print(f"  {name}: {info['files']:,} files, {info['bytes']:,} bytes")


def load_manifest() -> dict[str, object]:
    if not MANIFEST.is_file():
        raise SystemExit("Gen2 is not sealed: gen2/manifest.json is missing")
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("format") != "jetos-gen2-manifest-v1":
        raise SystemExit("unsupported Gen2 manifest format")
    return payload


def verify() -> None:
    payload = load_manifest()
    rows = payload.get("files")
    if not isinstance(rows, list):
        raise SystemExit("invalid Gen2 manifest")
    roots = {name: target for name, (_, target) in COMPONENTS.items()}
    expected: set[tuple[str, str]] = set()
    failures: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            failures.append("invalid manifest row")
            continue
        name = str(row.get("component") or "")
        rel = str(row.get("path") or "")
        expected.add((name, rel))
        root = roots.get(name)
        path = root / rel if root else None
        if path is None or not path.is_file():
            failures.append(f"missing {name}/{rel}")
        elif path.stat().st_size != int(row.get("bytes") or -1):
            failures.append(f"size changed {name}/{rel}")
        elif sha256(path) != row.get("sha256"):
            failures.append(f"hash changed {name}/{rel}")
    for name, root in roots.items():
        if not root.is_dir():
            failures.append(f"component missing {name}")
            continue
        for _, rel in files(root):
            if (name, rel.as_posix()) not in expected:
                failures.append(f"unsealed file {name}/{rel.as_posix()}")
    if failures:
        raise SystemExit("Gen2 verification FAILED:\n  " + "\n  ".join(failures[:100]))
    print(f"JETOS Gen2 verification: PASS ({len(rows):,} sealed files)")


def census() -> None:
    verify()
    counts: Counter[str] = Counter()
    for _, root in COMPONENTS.values():
        for path, _ in files(root):
            counts[path.suffix or "[no extension]"] += 1
    print(f"Gen2 source files: {sum(counts.values()):,}")
    for suffix, count in counts.most_common():
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
    sub.add_parser("intake")
    sub.add_parser("verify")
    sub.add_parser("status")
    sub.add_parser("census")
    args = parser.parse_args()
    {"intake": intake, "verify": verify, "status": status, "census": census}[args.command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
