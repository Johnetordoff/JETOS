#!/usr/bin/env python3
"""Fast structural tests for the JETOS source/Fat/Skinny contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"


def nested_git_metadata() -> list[Path]:
    return sorted(SOURCE.rglob(".git"))


def canonical_doc_contract() -> None:
    assert (ROOT / "MANDATE.md").is_file()
    assert (ROOT / "AGENTS.md").is_file()
    assert (ROOT / "ARCHITECTURE.md").is_file()
    assert not list(ROOT.glob("MANDATE_*.md"))
    assert not [path for path in ROOT.glob("AGENT*.md") if path.name != "AGENTS.md"]
    assert not [
        path
        for path in ROOT.glob("*ARCHITECTURE*.md")
        if path.name != "ARCHITECTURE.md"
    ]


def main() -> int:
    checks = 0

    canonical_doc_contract()
    checks += 6

    gitmodules = ROOT / ".gitmodules"
    provenance = SOURCE / "UPSTREAM_PROVENANCE.json"

    if gitmodules.exists():
        text = gitmodules.read_text(encoding="utf-8")
        assert '[submodule "source/linux"]' in text
        assert '[submodule "source/cpython"]' in text
        assert (ROOT / "tools/absorb_source.py").is_file()
        checks += 3
    else:
        assert (SOURCE / "linux/Makefile").is_file()
        assert (SOURCE / "cpython/Python/sysmodule.c").is_file()
        assert provenance.is_file()
        data = json.loads(provenance.read_text(encoding="utf-8"))
        assert data["architecture"] == "single-outer-git-repository"
        assert set(data["sources"]) == {"linux", "cpython"}
        assert not nested_git_metadata()
        checks += 6

    architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "improved, deliberately diverging descendant of CPython" in architecture
    assert "CPython 2" in architecture
    assert "one outer JETOS Git repository" in architecture
    checks += 3

    assert (SOURCE / "README.md").is_file()
    assert (SOURCE / "shared").is_dir()
    assert (SOURCE / "shared/README.md").is_file()
    assert (SOURCE / "ports").is_dir()
    assert (ROOT / "Temporary Bullshit").is_dir()
    assert not (ROOT / "vendor").exists()
    checks += 6

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'SOURCE = ROOT / "source"' in dev
    assert 'SOURCE_LINUX = SOURCE / "linux"' in dev
    assert 'SOURCE_CPYTHON = SOURCE / "cpython"' in dev
    checks += 3

    package = (ROOT / "tools/package.py").read_text(encoding="utf-8")
    assert 'PROFILE_FAT = "fat"' in package
    assert 'PROFILE_SKINNY = "skinny"' in package
    assert "Skinny profile: full source trees" in package
    checks += 3

    work_server = (ROOT / "tools/work_server.py").read_text(encoding="utf-8")
    assert '"source/linux/"' in work_server
    assert '"source/cpython/"' in work_server
    checks += 2

    print(f"JETOS source contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
