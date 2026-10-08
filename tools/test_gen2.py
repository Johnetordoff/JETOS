#!/usr/bin/env python3
"""Structural guards for the JETOS Gen2 frozen-source/CLI contract."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    gen2 = (ROOT / "GEN2.txt").read_text(encoding="utf-8")
    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    manager = (ROOT / "tools/gen2.py").read_text(encoding="utf-8")
    init = (ROOT / "src/jetos/init.py").read_text(encoding="utf-8")
    shell = (ROOT / "src/jetos/shell.py").read_text(encoding="utf-8")

    require("JetOS Python" in gen2, "Gen2 must name the runtime JetOS Python")
    require("C++ is migration debt" in gen2, "Gen2 must make C++ migration debt")
    require("Decaptor" in gen2, "Gen2 must preserve the separate Decaptor UI boundary")
    require("command-line-first" in gen2.lower(), "Gen2 must be command-line-first")

    require('GEN2 = ROOT / "gen2" / "vendor"' in dev, "Gen2 build must use local frozen source")
    require("tools/sources.py" not in dev, "Gen2 build must not invoke source materialization")
    require("github.com" not in dev, "Gen2 build must not carry a live remote source URL")
    require("verify_gen2()" in dev, "Gen2 build must verify the sealed source tree")

    require('"jetos-python"' in manager, "Gen2 intake must produce JetOS Python source")
    require('"jetos-kernel"' in manager, "Gen2 intake must produce JETOS kernel source")
    require("sha256" in manager, "Gen2 source must be hash sealed")
    require('".git"' in manager, "Gen2 intake must explicitly strip source VCS metadata")

    require("jetos_shell.interact" in init, "PID 1 must enter the JETOS command shell")
    require("_run_desktop" not in init, "Decaptor/desktop must not be required for Gen2 CLI boot")
    require("JETOS_REPO" not in init, "Gen2 boot must not select a live Git source tree")

    for command in ("DIR", "CD", "PWD", "TYPE", "RUN", "PYTHON", "SYSTEM", "HELP"):
        require(f'"{command}"' in shell, f"JETOS shell is missing {command}")

    print("JETOS Gen2 policy/CLI guards: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
