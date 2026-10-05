#!/usr/bin/env python3
"""Structural tests for the JETOS visible-source model."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_sources_module():
    spec = importlib.util.spec_from_file_location("jetos_sources", ROOT / "tools/sources.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    sources = load_sources_module()
    names = [item.name for item in sources.SPECS]
    assert len(names) == len(set(names)), "source component names must be unique"
    assert "jetos-language" in names
    assert "linux" in names
    assert "gcc" in names
    assert "raspberrypi-linux" in names
    assert "raspberrypi-firmware" in names

    for item in sources.SPECS:
        assert len(item.commit) == 40, f"{item.name} must pin an exact commit"
        assert item.repository.startswith("https://github.com/")
        assert not str(sources.destination(item)).startswith(str(ROOT / ".build"))

    assert sources.SOURCE_GAPS, "do not claim source-complete until package-only gaps are closed"

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'SOURCES = ROOT / "sources"' in dev
    assert 'LINUX_SOURCE = SOURCES / "linux"' in dev
    assert 'LANGUAGE_SOURCE = SOURCES / "cpython"' in dev

    entry = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert 'sub.add_parser("sources"' in entry
    assert 'sub.add_parser("modes"' in entry

    print("JETOS visible-source model: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
