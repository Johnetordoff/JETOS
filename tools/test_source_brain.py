#!/usr/bin/env python3
"""Fast structural tests for the JETOS Source Brain/Fat/Skinny contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BRAIN = ROOT / "source-brain"


def nested_git_metadata() -> list[Path]:
    return sorted(SOURCE_BRAIN.rglob(".git"))


def main() -> int:
    checks = 0

    gitmodules = ROOT / ".gitmodules"
    provenance = SOURCE_BRAIN / "UPSTREAM_PROVENANCE.json"

    if gitmodules.exists():
        text = gitmodules.read_text(encoding="utf-8")
        assert '[submodule "source-brain/linux"]' in text
        assert '[submodule "source-brain/cpython"]' in text
        assert (ROOT / "tools/absorb_source_brain.py").is_file()
        checks += 3
    else:
        assert (SOURCE_BRAIN / "linux/Makefile").is_file()
        assert (SOURCE_BRAIN / "cpython/Python/sysmodule.c").is_file()
        assert provenance.is_file()
        data = json.loads(provenance.read_text(encoding="utf-8"))
        assert data["architecture"] == "single-outer-git-repository"
        assert set(data["sources"]) == {"linux", "cpython"}
        assert not nested_git_metadata()
        checks += 6

    architecture = (ROOT / "JETLANG_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "improved, deliberately diverging descendant of CPython" in architecture
    assert "CPython 2" in architecture
    assert "one outer JETOS Git repository" in architecture
    assert "no Git submodules" in architecture
    checks += 4

    assert (SOURCE_BRAIN / "README.md").is_file()
    assert (SOURCE_BRAIN / "shared").is_dir()
    assert (SOURCE_BRAIN / "shared/README.md").is_file()
    assert (ROOT / "Temporary Bullshit").is_dir()
    assert (ROOT / "Temporary Bullshit/README.md").is_file()
    assert not (ROOT / "vendor").exists()
    checks += 6

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'SOURCE_BRAIN = ROOT / "source-brain"' in dev
    assert 'SOURCE_BRAIN_LINUX = SOURCE_BRAIN / "linux"' in dev
    assert 'SOURCE_BRAIN_CPYTHON = SOURCE_BRAIN / "cpython"' in dev
    assert '"--profile", "fat"' in dev or '"--profile",\n        "fat"' in dev
    checks += 4

    package = (ROOT / "tools/package.py").read_text(encoding="utf-8")
    assert 'PROFILE_FAT = "fat"' in package
    assert 'PROFILE_SKINNY = "skinny"' in package
    assert 'TEMPORARY_BULLSHIT_DIRNAME = "Temporary Bullshit"' in package
    assert "Skinny profile: Source Brain trees, Temporary Bullshit, and" in package
    checks += 4

    skinny = (ROOT / "SKINNY_MODE.md").read_text(encoding="utf-8")
    assert "Skinny Mode must **not** contain" in skinny
    assert "the complete Linux source tree" in skinny
    assert "the CPython source tree" in skinny
    assert "Temporary Bullshit/" in skinny
    assert "Fat-mode test fixtures" in skinny
    checks += 5

    work_server = (ROOT / "tools/work_server.py").read_text(encoding="utf-8")
    assert '"source-brain/linux/"' in work_server
    assert '"source-brain/cpython/"' in work_server
    checks += 2

    print(f"JETOS Source Brain contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
