#!/usr/bin/env python3
"""Guard the short normative JETOS architecture constitution against drift."""
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
        "JETOS Language/Python",
        "C for native code",
        "New JETOS-owned C++ MUST NOT be introduced",
        "A JETOS fork is not a frozen snapshot",
        "Merge conflicts are architectural decisions",
        'blindly selecting "ours" or "theirs"',
        "Fat Mode MUST carry",
        "Skinny Mode MAY omit development source",
        "one process-wide Global Interpreter Lock",
        "individual bytes or bits",
        "command-line/interactive JETOS Language control path",
        "Local JETOS UI rendering MUST NOT require HTTP",
        "canonical JETOS product artifact is a directly bootable image",
        "MUST NOT silently repartition",
        "source -> build rule -> artifact -> installed file -> image",
        "implementation from proof",
        "Performance decisions MUST be benchmark-informed",
    )

    assert "README.md, AGENTS.txt" in text
    assert "case by case" in text
    assert "newest stable CPython" in text
    assert "jailbreaking iPhone/iPad" in text

    print("JETOS normative constitution: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
