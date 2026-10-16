#!/usr/bin/env python3
"""Deterministic recursive source inventory for the JETOS checkout.

The inventory intentionally walks initialized source working trees so Linux,
the CPython-derived JetLang lineage, shared runtime source, ports, and JetOS
authored files can be measured as one source estate. Git/build metadata and
the inventory's own generated output are excluded; authored source files are
not.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHUNK_SIZE = 1024 * 1024
BINARY_SAMPLE = 8192
SCHEMA_VERSION = 2
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
CSV_FIELDS = (
    "path",
    "source_area",
    "directory",
    "name",
    "type",
    "bytes",
    "text_lines",
    "binary",
    "symlink",
)


def file_type(path: Path) -> str:
    if path.name in SPECIAL_TYPES:
        return SPECIAL_TYPES[path.name]
    suffixes = path.suffixes
    if suffixes:
        return "".join(suffixes).lower()
    return "<no-extension>"


def source_area_for_path(path: str) -> str:
    """Classify a repository-relative path into a stable source estate area."""
    if path == "source/linux" or path.startswith("source/linux/"):
        return "linux"
    if path == "source/cpython" or path.startswith("source/cpython/"):
        return "jetlang-cpython"
    if path == "source/shared" or path.startswith("source/shared/"):
        return "shared"
    if path == "source/ports" or path.startswith("source/ports/"):
        return "ports"
    if path == "source" or path.startswith("source/"):
        return "source-metadata"
    return "jetos"


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


def _new_bucket() -> dict[str, int]:
    return {"files": 0, "bytes": 0, "text_lines": 0}


def _accumulate(bucket: dict[str, int], size: int, lines: int | None) -> None:
    bucket["files"] += 1
    bucket["bytes"] += size
    if lines is not None:
        bucket["text_lines"] += lines


def scan(root: Path) -> dict[str, Any]:
    root = root.resolve()
    entries: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, int]] = defaultdict(_new_bucket)
    by_area: dict[str, dict[str, int]] = defaultdict(_new_bucket)
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
            area = source_area_for_path(rel)
            relative_path = Path(rel)
            directory = relative_path.parent.as_posix()
            if directory == ".":
                directory = ""
            row = {
                "path": rel,
                "source_area": area,
                "directory": directory,
                "name": relative_path.name,
                "type": kind,
                "bytes": size,
                "text_lines": lines,
                "binary": binary,
                "symlink": symlink,
            }
            entries.append(row)
            _accumulate(by_type[kind], size, lines)
            _accumulate(by_area[area], size, lines)

    entries.sort(key=lambda item: item["path"])
    total_bytes = sum(item["bytes"] for item in entries)
    total_text_lines = sum(item["text_lines"] or 0 for item in entries)
    text_files = sum(
        1 for item in entries if item["text_lines"] is not None and not item["symlink"]
    )
    binary_files = sum(1 for item in entries if item["binary"])
    symlinks = sum(1 for item in entries if item["symlink"])

    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "summary": {
            "files": len(entries),
            "bytes": total_bytes,
            "text_files": text_files,
            "binary_files": binary_files,
            "symlinks": symlinks,
            "text_lines": total_text_lines,
            "source_linux_initialized": (root / "source/linux/Makefile").is_file(),
            "source_cpython_initialized": (
                root / "source/cpython/Include/Python.h"
            ).is_file(),
            "shared_initialized": (root / "source/shared").is_dir(),
        },
        "source_areas": [
            {"source_area": area, **values}
            for area, values in sorted(by_area.items(), key=lambda item: item[0])
        ],
        "file_types": [
            {"type": kind, **values}
            for kind, values in sorted(by_type.items(), key=lambda item: item[0])
        ],
        "files": entries,
        "unreadable": unreadable,
    }


def write_outputs(data: dict[str, Any], output_dir: Path) -> None:
    """Write both human-readable summaries and stream-friendly machine formats."""
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "source-inventory.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "source-inventory.jsonl").open("w", encoding="utf-8") as handle:
        for item in data["files"]:
            handle.write(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n")

    with (output_dir / "source-inventory.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in data["files"]:
            writer.writerow({field: item.get(field) for field in CSV_FIELDS})

    with (output_dir / "source-tree.txt").open("w", encoding="utf-8") as handle:
        for item in data["files"]:
            handle.write(f'{item["path"]}\n')

    summary = data["summary"]
    with (output_dir / "source-inventory.md").open("w", encoding="utf-8") as handle:
        handle.write("# JETOS source inventory\n\n")
        handle.write(f'- Schema version: {data["schema_version"]}\n')
        handle.write(f'- Files: {summary["files"]:,}\n')
        handle.write(f'- Bytes: {summary["bytes"]:,}\n')
        handle.write(f'- Text lines: {summary["text_lines"]:,}\n')
        handle.write(f'- Text files: {summary["text_files"]:,}\n')
        handle.write(f'- Binary files: {summary["binary_files"]:,}\n')
        handle.write(f'- Symlinks: {summary["symlinks"]:,}\n')
        handle.write(
            "- Linux source initialized: "
            f'{summary["source_linux_initialized"]}\n'
        )
        handle.write(
            "- CPython-derived source initialized: "
            f'{summary["source_cpython_initialized"]}\n'
        )
        handle.write(f'- Shared source initialized: {summary["shared_initialized"]}\n')
        handle.write("\n## Source areas\n\n")
        handle.write("| Area | Files | Bytes | Text lines |\n")
        handle.write("|---|---:|---:|---:|\n")
        for item in data["source_areas"]:
            handle.write(
                f'| `{item["source_area"]}` | {item["files"]:,} | '
                f'{item["bytes"]:,} | {item["text_lines"]:,} |\n'
            )
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
    print("Machine inventory:", args.output_dir.resolve() / "source-inventory.json")
    print("Streaming paths:", args.output_dir.resolve() / "source-inventory.jsonl")
    if not summary["source_linux_initialized"]:
        print("NOTE: source/linux is not fully initialized; global totals are partial.")
    if not summary["source_cpython_initialized"]:
        print("NOTE: source/cpython is not fully initialized; global totals are partial.")
    if data["unreadable"]:
        print(f'NOTE: {len(data["unreadable"])} paths were unreadable.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
