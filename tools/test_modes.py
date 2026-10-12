#!/usr/bin/env python3
"""Fast guards for the Fat/Skinny source/runtime contract."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from jetos import mode  # noqa: E402


def main() -> int:
    fat = mode.policy("fat")
    skinny = mode.policy("skinny")
    assert fat.retains_bulk_source is True
    assert fat.requires_complete_source_closure is True
    assert fat.target_resolved is False
    assert fat.requires_compiled_native_runtime is True
    assert fat.can_derive_skinny is True

    assert skinny.retains_bulk_source is False
    assert skinny.requires_complete_source_closure is False
    assert skinny.target_resolved is True
    assert skinny.requires_compiled_native_runtime is True
    assert skinny.can_derive_skinny is False

    contract = (ROOT / "FAT_SKINNY_RUNTIME.md").read_text(encoding="utf-8")
    assert "portable source universe" in contract
    assert "target-resolved runtime" in contract
    assert "CPython C extension" in contract
    assert "pure C operation" in contract
    assert "running compiled artifact must be traceable" in contract
    assert "complete portable source closure is not yet qualified" in contract
    print("JETOS Fat/Skinny mode tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
