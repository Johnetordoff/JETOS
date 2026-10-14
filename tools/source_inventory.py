#!/usr/bin/env python3
"""Deterministic recursive source inventory for the JETOS checkout.

The inventory intentionally walks initialized submodule working trees so Linux,
the CPython-derived JetLang lineage, and source-brain/shared can be measured as
one source estate. Git/build metadata and the inventory's own generated output
are excluded; authored source files are not.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHUNK_SIZE = 1024 * 1024
BINARY_SAMPLE = 8192
SPECIAL_TYPES = {
    "Makefile": "Makefile",
    "Kconfig": "Kconfig",
    "Kbuild": "Kbuild",
    "Dockerfile": "Dockerfile",
    "LICENSE": "LICENSE",
    "COPYING": "COPYING",
}
IGNORED_DIR_NAMES = {".git", ".build", "__pycache__"}
IGNORED_RELATIVE_DIRS = {
    "artifacts/source-inventory",
    "Temporary Bullshit/output",
}


def file_type(path: Path) -> str:
    if path.name in SPECIAL_TYPES:
        return SPECIAL_TYPES[path.name]
    suffixes = path.suffixes
    if suffixes:
        return "".join(suffixes).lower()
    return "<no-extension>"


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            sample = handle.read(BINARY_SAMPLE)
    except OSError:
        return True
    return b"\x00" in sample


def count_text_lines(path: Path) -> int:
    lines = 0
    last_byte: bytes | None = None
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            lines += chunk.count(b"\n")
            last_byte = chunk[-1:]
    if last_byte not in (None, b"\n"):
        lines += 1
    return lines


def should_descend(root: Path, dirpath: str, name: str) -> bool:
    if name in IGNORED_DIR_NAMES:
        return False
    child = (Path(dirpath) / name).relative_to(root).as_posix()
    return child not in IGNORED_RELATIVE_DIRS


def scan(root: Path) -> dict[str, Any]:
    root = root.resolve()
    entries: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, int]] = defaultdict(
        lambda: {"files": 0, "bytes": 0, "text_lines": 0}
    )
    unreadable: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            name for name in dirnames if should_descend(root, dirpath, name)
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            rel = path.relative_to(root).as_posix()
            try:
                stat = path.lstat()
                size = stat.st_size
                symlink = path.is_symlink()
                binary = False if symlink else looks_binary(path)
                lines = None if symlink or binary else count_text_lines(path)
            except OSError as exc:
                unreadable.append(f"{rel}: {exc}")
                continue

            kind = file_type(path)
            row = {
                "path": rel,
                "type": kind,
                "bytes": size,
                "text_lines": lines,
                "binary": binary,
                "symlink": symlink,
            }
            entries.append(row)
            bucket = by_type[kind]
            bucket["files"] += 1
            bucket["bytes"] += size
            if lines is not None:
                bucket["text_lines"] += lines

    entries.sort(key=lambda item: item["path"])
    total_bytes = sum(item["bytes"] for item in entries)
    total_text_lines = sum(item["text_lines"] or 0 for item in entries)
    text_files = sum(
        1 for item in entries if item["text_lines"] is not None and not item["symlink"]
    )
    binary_files = sum(1 for item in entries if item["binary"])
    symlinks = sum(1 for item in entries if item["symlink"])

    return {
        "root": str(root),
        "summary": {
            "files": len(entries),
            "bytes": total_bytes,
            "text_files": text_files,
            "binary_files": binary_files,
            "symlinks": symlinks,
            "text_lines": total_text_lines,
            "source_brain_linux_initialized": (root / "source-brain/linux/Makefile").is_file(),
            "source_brain_cpython_initialized": (
                root / "source-brain/cpython/Include/Python.h"
            ).is_file(),
            "shared_initialized": (root / "source-brain/shared").is_dir(),
        },
        "file_types": [
            {"type": kind, **values}
            for kind, values in sorted(by_type.items(), key=lambda item: item[0])
        ],
        "files": entries,
        "unreadable": unreadable,
    }


def write_outputs(data: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "source-inventory.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "source-tree.txt").open("w", encoding="utf-8") as handle:
        for item in data["files"]:
            handle.write(f'{item["path"]}\n')

    summary = data["summary"]
    with (output_dir / "source-inventory.md").open("w", encoding="utf-8") as handle:
        handle.write("# JETOS source inventory\n\n")
        handle.write(f'- Files: {summary["files"]:,}\n')
        handle.write(f'- Bytes: {summary["bytes"]:,}\n')
        handle.write(f'- Text lines: {summary["text_lines"]:,}\n')
        handle.write(f'- Text files: {summary["text_files"]:,}\n')
        handle.write(f'- Binary files: {summary["binary_files"]:,}\n')
        handle.write(f'- Symlinks: {summary["symlinks"]:,}\n')
        handle.write(
            "- Linux source initialized: "
            f'{summary["source_brain_linux_initialized"]}\n'
        )
        handle.write(
            "- CPython-derived source initialized: "
            f'{summary["source_brain_cpython_initialized"]}\n'
        )
        handle.write(f'- Shared source initialized: {summary["shared_initialized"]}\n')
        handle.write("\n## File types\n\n")
        handle.write("| Type | Files | Bytes | Text lines |\n")
        handle.write("|---|---:|---:|---:|\n")
        for item in data["file_types"]:
            handle.write(
                f'| `{item["type"]}` | {item["files"]:,} | '
                f'{item["bytes"]:,} | {item["text_lines"]:,} |\n'
            )
        if data["unreadable"]:
            handle.write("\n## Unreadable paths\n\n")
            for error in data["unreadable"]:
                handle.write(f"- {error}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/source-inventory",
    )
    args = parser.parse_args()

    data = scan(args.root.resolve())
    write_outputs(data, args.output_dir.resolve())

    summary = data["summary"]
    print(
        "JETOS inventory: "
        f'{summary["files"]} files, '
        f'{summary["bytes"]} bytes, '
        f'{summary["text_lines"]} text lines'
    )
    if not summary["source_brain_linux_initialized"]:
        print("NOTE: source-brain/linux is not fully initialized; global totals are partial.")
    if not summary["source_brain_cpython_initialized"]:
        print("NOTE: source-brain/cpython is not fully initialized; global totals are partial.")
    if data["unreadable"]:
        print(f'NOTE: {len(data["unreadable"])} paths were unreadable.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
