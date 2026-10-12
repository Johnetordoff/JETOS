#!/usr/bin/env python3
"""Fast packaging checks for the full Linux-source-in-image rule."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_package",
    ROOT / "tools/package.py",
)
assert SPEC and SPEC.loader
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        source = temp / "linux"
        rootfs = temp / "rootfs"
        (source / "drivers/example").mkdir(parents=True)
        (source / "Makefile").write_text("VERSION = 6\n", encoding="utf-8")
        (source / "README").write_text("Linux source\n", encoding="utf-8")
        (source / "drivers/example/test.c").write_text(
            "int jetos_linux_source_test;\n",
            encoding="utf-8",
        )
        (source / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")

        target = package.copy_linux_source(source, rootfs)
        assert target == rootfs / "usr/src/linux"
        assert (target / "Makefile").read_text(encoding="utf-8") == "VERSION = 6\n"
        assert (target / "README").is_file()
        assert (target / "drivers/example/test.c").is_file()
        assert not (target / ".git").exists()

    print("JETOS full Linux source packaging: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
