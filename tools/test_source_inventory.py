#!/usr/bin/env python3
"""Fast deterministic tests for tools/source_inventory.py and its query path."""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import source_inventory
import source_inventory_query


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "source/shared").mkdir(parents=True)
        (root / "alpha.c").write_text("one\ntwo\n", encoding="utf-8")
        (root / "Makefile").write_text("all:\n\techo ok\n", encoding="utf-8")
        (root / "binary.bin").write_bytes(b"\x00abc")

        (root / "Temporary Bullshit/output").mkdir(parents=True)
        (root / "Temporary Bullshit/output/source-tree.txt").write_text(
            "generated\n", encoding="utf-8"
        )
        (root / "artifacts/source-inventory").mkdir(parents=True)
        (root / "artifacts/source-inventory/source-inventory.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (root / ".build").mkdir()
        (root / ".build/object.o").write_bytes(b"generated")
        (root / "__pycache__").mkdir()
        (root / "__pycache__/cache.pyc").write_bytes(b"generated")

        data = source_inventory.scan(root)
        summary = data["summary"]
        assert data["schema_version"] == 2
        assert summary["files"] == 3
        assert summary["bytes"] == 26
        assert summary["text_files"] == 2
        assert summary["binary_files"] == 1
        assert summary["text_lines"] == 4
        assert summary["shared_initialized"] is True

        types = {item["type"]: item for item in data["file_types"]}
        assert types[".c"]["text_lines"] == 2
        assert types["Makefile"]["text_lines"] == 2
        assert types[".bin"]["files"] == 1

        areas = {item["source_area"]: item for item in data["source_areas"]}
        assert areas["jetos"]["files"] == 3
        assert source_inventory.source_area_for_path("source/linux/kernel/fork.c") == "linux"
        assert (
            source_inventory.source_area_for_path("source/cpython/Python/ceval.c")
            == "jetlang-cpython"
        )
        assert source_inventory.source_area_for_path("source/shared/runtime.c") == "shared"
        assert source_inventory.source_area_for_path("source/ports/gcc/x.c") == "ports"

        output = root / "out"
        source_inventory.write_outputs(data, output)
        assert (output / "source-inventory.json").is_file()
        assert (output / "source-inventory.jsonl").is_file()
        assert (output / "source-inventory.csv").is_file()
        assert (output / "source-inventory.md").is_file()
        assert (output / "source-tree.txt").read_text(encoding="utf-8").splitlines() == [
            "Makefile",
            "alpha.c",
            "binary.bin",
        ]

        jsonl_rows = list(
            source_inventory_query.iter_inventory_rows(output / "source-inventory.jsonl")
        )
        json_rows = list(
            source_inventory_query.iter_inventory_rows(output / "source-inventory.json")
        )
        assert jsonl_rows == json_rows == data["files"]

        selected = list(
            source_inventory_query.iter_matches(
                jsonl_rows,
                exact_paths=[],
                prefixes=[],
                globs=["*.c"],
                contains=[],
                areas=["jetos"],
                types=[".c"],
            )
        )
        assert [row["path"] for row in selected] == ["alpha.c"]

        selected = list(
            source_inventory_query.iter_matches(
                jsonl_rows,
                exact_paths=["Makefile"],
                prefixes=[],
                globs=[],
                contains=[],
                areas=[],
                types=[],
            )
        )
        assert [row["path"] for row in selected] == ["Makefile"]

        buffer = io.StringIO()
        count = source_inventory_query.emit(selected, "jsonl", buffer)
        assert count == 1
        assert json.loads(buffer.getvalue())["path"] == "Makefile"

    print("JETOS source inventory tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
