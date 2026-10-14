#!/usr/bin/env python3
"""Print a compact JETOS project hierarchy from the canonical source inventory."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from typing import Any

from common import HERE, complete, prepare_sources, print_completeness, scan


def _node() -> dict[str, Any]:
    return {"children": {}, "is_file": False, "omitted_files": 0}


def render_hierarchy(data: dict[str, Any], max_depth: int = 2) -> str:
    """Render files from an inventory as a compact tree up to ``max_depth``.

    Paths deeper than the requested display depth are summarized on the deepest
    visible directory line so a large Linux/JetLang source tree stays readable
    without pretending that deeper files do not exist.
    """
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")

    root = _node()
    for item in data["files"]:
        parts = PurePosixPath(item["path"]).parts
        current = root
        for index, part in enumerate(parts):
            if index >= max_depth:
                current["omitted_files"] += 1
                break
            child = current["children"].setdefault(part, _node())
            current = child
            if index == len(parts) - 1:
                current["is_file"] = True

    lines = ["JETOS/"]

    def walk(current: dict[str, Any], prefix: str, depth: int) -> None:
        children = sorted(current["children"].items())
        for index, (name, child) in enumerate(children):
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            is_directory = bool(child["children"] or child["omitted_files"]) and not child["is_file"]
            suffix = "/" if is_directory else ""
            omitted = (
                f"  [… {child['omitted_files']:,} deeper files]"
                if child["omitted_files"]
                else ""
            )
            lines.append(f"{prefix}{connector}{name}{suffix}{omitted}")
            if child["children"] and depth < max_depth:
                continuation = "    " if last else "│   "
                walk(child, prefix + continuation, depth + 1)

    walk(root, "", 1)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="initialize source trees first")
    parser.add_argument("--depth", type=int, default=2, help="visible hierarchy depth (default: 2)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional output file; defaults under Temporary Bullshit/output",
    )
    args = parser.parse_args()

    if args.prepare:
        prepare_sources()

    data = scan()
    hierarchy = render_hierarchy(data, args.depth)
    print(hierarchy)

    output = args.output or (HERE / "output" / f"source-hierarchy-depth-{args.depth}.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(hierarchy + "\n", encoding="utf-8")
    print()
    print(f"Hierarchy file: {output.resolve()}")
    print_completeness(data)
    return 0 if complete(data) else 2


if __name__ == "__main__":
    raise SystemExit(main())
