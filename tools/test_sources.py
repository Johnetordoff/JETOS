#!/usr/bin/env python3
"""Structural tests for Gen2 intake staging versus sealed active source."""
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
    # Legacy materialization remains only as one-time intake staging. Exact pins
    # are useful for reconstructing the chosen seeds, but sealed Gen2 never builds
    # or boots from these directories directly.
    sources = load_sources_module()
    names = [item.name for item in sources.SPECS]
    assert len(names) == len(set(names))
    assert "jetos-language" in names
    assert "linux" in names
    for item in sources.SPECS:
        assert len(item.commit) == 40

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'GEN2 = ROOT / "gen2" / "vendor"' in dev
    assert 'JETOS_KERNEL_SOURCE = GEN2 / "jetos-kernel"' in dev
    assert 'JETOS_PYTHON_SOURCE = GEN2 / "jetos-python"' in dev
    assert "tools/sources.py" not in dev
    assert "github.com" not in dev

    gen2 = (ROOT / "tools/gen2.py").read_text(encoding="utf-8")
    assert 'SEEDS = ROOT / "sources"' in gen2
    assert '"jetos-python"' in gen2
    assert '"jetos-kernel"' in gen2
    assert "internalize_jetos_python" in gen2

    print("JETOS Gen2 intake/source boundary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
