#!/usr/bin/env python3
"""Policy/structure tests for JETOS Gen2 user-attributed command shell."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import console, shell  # noqa: E402
from jetos.identity import UserIdentity, current_user  # noqa: E402


def main() -> int:
    alice = UserIdentity("alice", 1000, 1000, "test")
    assert console.primary_prompt(alice) == "alice@jetos> "
    assert console.continuation_prompt(alice) == "alice@jetos...> "
    assert shell.prompt(alice).startswith("alice@jetos:")

    actual = current_user()
    assert actual.name
    assert shell.prompt(actual).startswith(actual.name + "@jetos:")

    init = (ROOT / "src/jetos/init.py").read_text(encoding="utf-8")
    assert "jetos_shell.interact" in init
    assert '"user": session_user' in init
    assert "_run_desktop" not in init

    shell_source = (ROOT / "src/jetos/shell.py").read_text(encoding="utf-8")
    for command in ("DIR", "CD", "TYPE", "RUN", "PYTHON", "SYSTEM", "HELP"):
        assert f'"{command}"' in shell_source
    assert "Decaptor" in shell_source

    entry = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert '"run",' in entry
    assert 'aliases=["boot"]' in entry

    print("JETOS Gen2 user-attributed command shell contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
