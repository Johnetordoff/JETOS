#!/usr/bin/env python3
"""Policy/structure tests for JETOS user-attributed consoles and easy boot."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import console  # noqa: E402
from jetos.identity import UserIdentity, current_user  # noqa: E402


def main() -> int:
    alice = UserIdentity("alice", 1000, 1000, "test")
    assert console.primary_prompt(alice) == "alice@jetos> "
    assert console.continuation_prompt(alice) == "alice@jetos...> "

    actual = current_user()
    assert actual.name
    assert console.primary_prompt(actual).startswith(actual.name + "@jetos>")

    init = (ROOT / "src/jetos/init.py").read_text(encoding="utf-8")
    assert "jetos_console.interact" in init
    assert '"user": session_user' in init

    desktop = (ROOT / "src/jetos/desktop.py").read_text(encoding="utf-8")
    assert "prompt_label" in desktop
    assert "jetos_console.primary_prompt(session_user)" in desktop
    assert 'state = {"prompt": "jetos> "}' not in desktop

    entry = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert '"run",' in entry
    assert 'aliases=["boot"]' in entry
    assert "default_profile=mode.FAT" in entry
    assert "actual JETOS VM" in entry

    contract = (ROOT / "TERMINAL_AND_RUN.txt").read_text(encoding="utf-8")
    for phrase in (
        "Every interactive JETOS command-entry surface MUST visibly identify the user",
        "<user>@jetos>",
        "effective operating-system/JETOS",
        "python jetos.py run",
        "actual JETOS VM/kernel/userspace boot path",
        "MUST NOT silently partition",
    ):
        assert phrase in contract

    print("JETOS user-attributed console and easy-run contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
