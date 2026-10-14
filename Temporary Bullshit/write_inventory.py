#!/usr/bin/env python3
"""Write the complete recursive JETOS source inventory artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import HERE, complete, load_inventory, prepare_sources, print_completeness, scan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="initialize source submodules first")
    parser.add_argument("--output-dir", type=Path, default=HERE / "output")
    args = parser.parse_args()

    if args.prepare:
        prepare_sources()

    data = scan()
    load_inventory().write_outputs(data, args.output_dir.resolve())
    summary = data["summary"]
    print(f'Wrote inventory for {summary["files"]:,} files to {args.output_dir.resolve()}')
    print_completeness(data)
    return 0 if complete(data) else 2


if __name__ == "__main__":
    raise SystemExit(main())
