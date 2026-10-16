#!/usr/bin/env python3
"""Query a generated JETOS source inventory without walking the source tree again."""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "artifacts/source-inventory/source-inventory.jsonl"
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


def iter_inventory_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Stream rows from JSONL, or read the `files` list from the JSON artifact."""
    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(
                        f"{path}:{line_number}: invalid JSONL: {exc}"
                    ) from exc
                if not isinstance(row, dict) or "path" not in row:
                    raise SystemExit(
                        f"{path}:{line_number}: inventory row is missing path"
                    )
                yield row
        return

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    rows = data.get("files")
    if not isinstance(rows, list):
        raise SystemExit(f"{path}: expected top-level files list")
    for row in rows:
        if not isinstance(row, dict) or "path" not in row:
            raise SystemExit(f"{path}: invalid file inventory row")
        yield row


def matches(
    row: dict[str, Any],
    *,
    exact_paths: list[str],
    prefixes: list[str],
    globs: list[str],
    contains: list[str],
    areas: list[str],
    types: list[str],
) -> bool:
    path = str(row.get("path", ""))
    if exact_paths and path not in exact_paths:
        return False
    if prefixes and not any(path.startswith(prefix) for prefix in prefixes):
        return False
    if globs and not any(fnmatch.fnmatchcase(path, pattern) for pattern in globs):
        return False
    if contains and not all(fragment in path for fragment in contains):
        return False
    if areas and row.get("source_area") not in areas:
        return False
    if types and row.get("type") not in types:
        return False
    return True


def iter_matches(
    rows: Iterable[dict[str, Any]],
    *,
    exact_paths: list[str],
    prefixes: list[str],
    globs: list[str],
    contains: list[str],
    areas: list[str],
    types: list[str],
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    emitted = 0
    for row in rows:
        if not matches(
            row,
            exact_paths=exact_paths,
            prefixes=prefixes,
            globs=globs,
            contains=contains,
            areas=areas,
            types=types,
        ):
            continue
        yield row
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def emit(rows: Iterable[dict[str, Any]], format_name: str, out: TextIO) -> int:
    count = 0
    if format_name == "json":
        materialized = list(rows)
        json.dump(materialized, out, indent=2, sort_keys=True)
        out.write("\n")
        return len(materialized)

    if format_name == "csv":
        writer = csv.DictWriter(out, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in CSV_FIELDS})
            count += 1
        return count

    for row in rows:
        if format_name == "paths":
            out.write(f'{row["path"]}\n')
        else:
            out.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query JETOS source-inventory.json/jsonl by path metadata."
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--path", action="append", default=[], dest="exact_paths")
    parser.add_argument("--prefix", action="append", default=[], dest="prefixes")
    parser.add_argument("--glob", action="append", default=[], dest="globs")
    parser.add_argument("--contains", action="append", default=[])
    parser.add_argument("--area", action="append", default=[], dest="areas")
    parser.add_argument("--type", action="append", default=[], dest="types")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--format",
        choices=("jsonl", "json", "csv", "paths"),
        default="jsonl",
        dest="format_name",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="print only the number of matching paths",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    rows = iter_inventory_rows(args.inventory.resolve())
    selected = iter_matches(
        rows,
        exact_paths=args.exact_paths,
        prefixes=args.prefixes,
        globs=args.globs,
        contains=args.contains,
        areas=args.areas,
        types=args.types,
        limit=args.limit,
    )
    if args.count:
        print(sum(1 for _ in selected))
        return 0

    emit(selected, args.format_name, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
