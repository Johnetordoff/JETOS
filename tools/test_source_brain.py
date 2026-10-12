#!/usr/bin/env python3
"""Fast structural tests for the JETOS Source Brain/Fat/Skinny contract."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = 0

    gitmodules = (ROOT / ".gitmodules").read_text(encoding="utf-8")
    assert '[submodule "source-brain/linux"]' in gitmodules
    assert "path = source-brain/linux" in gitmodules
    assert '[submodule "source-brain/cpython"]' in gitmodules
    assert "path = source-brain/cpython" in gitmodules
    assert "vendor/linux" not in gitmodules
    assert "vendor/cpython" not in gitmodules
    checks += 6

    assert (ROOT / "source-brain/README.md").is_file()
    assert not (ROOT / "vendor").exists()
    checks += 2

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'SOURCE_BRAIN = ROOT / "source-brain"' in dev
    assert 'SOURCE_BRAIN_LINUX = SOURCE_BRAIN / "linux"' in dev
    assert 'SOURCE_BRAIN_CPYTHON = SOURCE_BRAIN / "cpython"' in dev
    assert '"--profile",\n        "fat"' in dev
    checks += 4

    package = (ROOT / "tools/package.py").read_text(encoding="utf-8")
    assert 'PROFILE_FAT = "fat"' in package
    assert 'PROFILE_SKINNY = "skinny"' in package
    assert "Skinny profile: Source Brain trees and Fat qualification tools omitted" in package
    checks += 3

    skinny = (ROOT / "SKINNY_MODE.md").read_text(encoding="utf-8")
    assert "Skinny Mode must **not** contain" in skinny
    assert "the complete Linux source tree" in skinny
    assert "the CPython source tree" in skinny
    assert "Fat-mode test fixtures" in skinny
    checks += 4

    work_server = (ROOT / "tools/work_server.py").read_text(encoding="utf-8")
    assert '"source-brain/linux/"' in work_server
    assert '"source-brain/cpython/"' in work_server
    checks += 2

    print(f"JETOS Source Brain contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
