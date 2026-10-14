#!/usr/bin/env python3
"""Count text lines and bytes across the current JETOS source estate."""
from __future__ import annotations

import argparse
import json

from common import complete, prepare_sources, print_completeness, scan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="initialize source submodules first")
    parser.add_argument("--json", action="store_true", help="emit summary as JSON")
    args = parser.parse_args()

    if args.prepare:
        prepare_sources()

    data = scan()
    summary = data["summary"]
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f'Files: {summary["files"]:,}')
        print(f'Bytes: {summary["bytes"]:,}')
        print(f'Text files: {summary["text_files"]:,}')
        print(f'Text lines: {summary["text_lines"]:,}')
        print(f'Binary files: {summary["binary_files"]:,}')
        print(f'Symlinks: {summary["symlinks"]:,}')
        print_completeness(data)

    return 0 if complete(data) else 2


if __name__ == "__main__":
    raise SystemExit(main())
