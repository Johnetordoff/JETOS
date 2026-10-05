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
    assert not skinny.can_derive_skinny_images
    assert "target application/capability set" in skinny.application_model

    image = (ROOT / "tools/image.py").read_text(encoding="utf-8")
    assert "copy_fat_sources" in image
    assert 'ROOT / "sources" / "cpython"' in image
    assert 'ROOT / "sources" / "linux"' in image
    assert 'source_root = rootfs / "usr" / "src"' in image
    assert 'linux_target = source_root / "linux"' in image

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert "mode.CLI_CHOICES" in dev
    assert "canonical_mode == mode.SKINNY" in dev

    entry = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert "Fat Mode" in entry
    assert "Skinny Mode" in entry
    assert "mode.CLI_CHOICES" in entry

    agents = (ROOT / "AGENTS.txt").read_text(encoding="utf-8")
    for phrase in (
        "LINGUA FRANCA PROGRAMMING MODEL",
        "LIVE INTROSPECTION AND CONTROL",
        "FAT MODE AND SKINNY MODE",
    ):
        assert phrase in agents

    print("JETOS Fat/Skinny mode contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
