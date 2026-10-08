#!/usr/bin/env python3
"""Policy/structure tests for canonical JETOS Fat and Skinny modes."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import mode  # noqa: E402


def main() -> int:
    assert mode.MODES == ("fat", "skinny")
    assert mode.normalize("fat") == "fat"
    assert mode.normalize("skinny") == "skinny"
    assert mode.normalize("full") == "fat"
    assert mode.normalize("lean") == "skinny"

    fat = mode.policy("fat")
    skinny = mode.policy("skinny")
    assert fat.general_purpose_app_host
    assert fat.carries_development_source
    assert fat.carries_kernel_source
    assert fat.can_derive_skinny_images
    assert not skinny.general_purpose_app_host
    assert not skinny.carries_development_source
    assert not skinny.carries_kernel_source

    image = (ROOT / "tools/image.py").read_text(encoding="utf-8")
    assert "copy_fat_sources" in image
    assert 'GEN2_VENDOR = ROOT / "gen2" / "vendor"' in image
    assert 'GEN2_VENDOR / "jetos-python"' in image
    assert 'GEN2_VENDOR / "jetos-kernel"' in image
    assert 'python_target = source_root / "jetos-python"' in image
    assert 'kernel_target = source_root / "jetos-kernel"' in image
    assert 'ROOT / "sources" / "cpython"' not in image
    assert 'ROOT / "sources" / "linux"' not in image

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert "mode.CLI_CHOICES" in dev
    assert "canonical_mode == mode.SKINNY" in dev
    assert 'JETOS_PYTHON_SOURCE = GEN2 / "jetos-python"' in dev
    assert 'JETOS_KERNEL_SOURCE = GEN2 / "jetos-kernel"' in dev

    constitution = (ROOT / "JETOS_CONSTITUTION.txt").read_text(encoding="utf-8")
    assert "Fat Mode and Skinny Mode are profiles of the SAME JETOS generation" in constitution

    print("JETOS Gen2 Fat/Skinny mode contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
