#!/usr/bin/env python3
"""Guard the normative JETOS Gen2 architecture constitution against drift."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = ROOT / "JETOS_CONSTITUTION.txt"


def require(text: str, *phrases: str) -> None:
    for phrase in phrases:
        assert phrase in text, f"JETOS constitution missing invariant: {phrase!r}"


def main() -> int:
    text = CONSTITUTION.read_text(encoding="utf-8")
    require(
        text,
        "JETOS NORMATIVE ARCHITECTURE CONSTITUTION",
        "JetOS Python",
        "C for native runtime/kernel/ABI/hardware work",
        "New JETOS-owned C++ MUST NOT be introduced",
        "A JETOS generation is a frozen source generation",
        "MUST NOT follow external branches",
        "command-line-first",
        "Decaptor",
        "gen2/manifest.json",
        "MUST fail rather than silently",
        "program launching",
        "CPU",
        "register",
        "Source visibility does not imply unrestricted live-memory authority",
        "Global Interpreter Lock",
        "Fat Mode and Skinny Mode",
        "MUST NOT silently repartition",
        "directly bootable",
        "build debt",
        "implementation from proof" if "implementation from proof" in text else "source review, structural tests, build success",
        "Performance changes SHOULD be benchmark-informed",
    )
    assert "external runtime identity" in text
    print("JETOS Gen2 normative constitution: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
