#!/usr/bin/env python3
"""Guard the normative JETOS architecture constitution against drift."""
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
        'blindly choose "ours" or "theirs"',
        "case by case",
        "newest stable CPython",
        "exact Linux kernel source corresponding to the running system",
        "Source visibility and runtime visibility are distinct properties",
        "one process-wide Global Interpreter Lock",
        "individual bytes or bits",
        "command-line/interactive JETOS Language control path",
        "SAME JETOS version and source lineage",
        "Fat Mode MUST be able to derive, build, and program/flash Skinny images",
        "target application/capability set",
        "canonical JETOS product artifact is a directly bootable image",
        "MUST NOT silently repartition",
        "source -> build rule -> artifact -> installed file -> image",
        "jailbreaking iPhone/iPad",
        "implementation from proof",
        "Performance decisions MUST be benchmark-informed",
    )

    assert "README.md, AGENTS.txt" in text
    assert "HTTP, DNS, a remote web server" in text

    print("JETOS normative constitution: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
