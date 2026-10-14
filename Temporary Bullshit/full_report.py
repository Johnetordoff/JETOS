#!/usr/bin/env python3
"""Generate and print the temporary full JETOS source accounting report."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import HERE, complete, load_inventory, prepare_sources, print_completeness, scan
from print_hierarchy import render_hierarchy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="initialize source submodules first")
    parser.add_argument("--output-dir", type=Path, default=HERE / "output")
    parser.add_argument(
        "--hierarchy-depth",
        type=int,
        default=2,
        help="visible project hierarchy depth printed in the report (default: 2)",
    )
    args = parser.parse_args()

    if args.prepare:
        prepare_sources()

    data = scan()
    output_dir = args.output_dir.resolve()
    load_inventory().write_outputs(data, output_dir)
    summary = data["summary"]
    hierarchy = render_hierarchy(data, args.hierarchy_depth)
    hierarchy_path = output_dir / f"source-hierarchy-depth-{args.hierarchy_depth}.txt"
    hierarchy_path.write_text(hierarchy + "\n", encoding="utf-8")

    print("JETOS TEMPORARY SOURCE REPORT")
    print(f'Files: {summary["files"]:,}')
    print(f'Bytes: {summary["bytes"]:,}')
    print(f'Text files: {summary["text_files"]:,}')
    print(f'Text lines: {summary["text_lines"]:,}')
    print(f'Binary files: {summary["binary_files"]:,}')
    print(f'Symlinks: {summary["symlinks"]:,}')
    print(f'File types: {len(data["file_types"]):,}')
    print()
    print("Type\tFiles\tBytes\tText lines")
    for item in data["file_types"]:
        print(f'{item["type"]}\t{item["files"]}\t{item["bytes"]}\t{item["text_lines"]}')
    print()
    print(f"PROJECT HIERARCHY ({args.hierarchy_depth} levels)")
    print(hierarchy)
    print()
    print(f'Inventory JSON: {(output_dir / "source-inventory.json").resolve()}')
    print(f'Inventory Markdown: {(output_dir / "source-inventory.md").resolve()}')
    print(f'Full file tree: {(output_dir / "source-tree.txt").resolve()}')
    print(f'Compact hierarchy: {hierarchy_path.resolve()}')
    print_completeness(data)
    return 0 if complete(data) else 2


if __name__ == "__main__":
    raise SystemExit(main())
