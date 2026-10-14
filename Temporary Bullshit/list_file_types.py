#!/usr/bin/env python3
"""List every discovered JETOS file type with counts, bytes, and text lines."""
from __future__ import annotations

import argparse

from common import complete, prepare_sources, print_completeness, scan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="initialize source submodules first")
    args = parser.parse_args()

    if args.prepare:
        prepare_sources()

    data = scan()
    print("Type\tFiles\tBytes\tText lines")
    for item in data["file_types"]:
        print(f'{item["type"]}\t{item["files"]}\t{item["bytes"]}\t{item["text_lines"]}')
    print_completeness(data)
    return 0 if complete(data) else 2


if __name__ == "__main__":
    raise SystemExit(main())
