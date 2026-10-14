#!/usr/bin/env python3
"""Fast deterministic tests for tools/source_inventory.py."""
from __future__ import annotations

import tempfile
from pathlib import Path

import source_inventory


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "source-brain/shared").mkdir(parents=True)
        (root / "alpha.c").write_text("one\ntwo\n", encoding="utf-8")
        (root / "Makefile").write_text("all:\n\techo ok\n", encoding="utf-8")
        (root / "binary.bin").write_bytes(b"\x00abc")

        data = source_inventory.scan(root)
        summary = data["summary"]
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

        output = root / "out"
        source_inventory.write_outputs(data, output)
        assert (output / "source-inventory.json").is_file()
        assert (output / "source-inventory.md").is_file()
        assert (output / "source-tree.txt").read_text(encoding="utf-8").splitlines() == [
            "Makefile",
            "alpha.c",
            "binary.bin",
        ]

    print("JETOS source inventory tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
