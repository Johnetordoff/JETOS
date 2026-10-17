#!/usr/bin/env python3
"""Fast tests for the stdlib qualification instrument."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/stdlib_qualify.py"


def run(*args: str) -> None:
    subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        baseline = temp / "baseline.json"
        candidate = temp / "candidate.json"

        run("--module", "math", "--manifest", str(baseline), "--strict")
        data = json.loads(baseline.read_text(encoding="utf-8"))
        math_entry = data["modules"]["math"]
        assert math_entry["import"] == "PASS"
        assert math_entry["inventory"] == "PASS"
        paths = {item["path"] for item in math_entry["callables"]}
        assert "sqrt" in paths
        assert "sin" in paths

        run(
            "--module",
            "math",
            "--manifest",
            str(candidate),
            "--baseline",
            str(baseline),
            "--strict",
        )
        assert candidate.is_file()

        # These modules exposed signature-introspection exceptions in the
        # Python 3.14.8 JetLang build even though their imports were healthy.
        # Inventory metadata is best-effort and must not fail qualification.
        run("--module", "doctest", "--strict")
        run("--module", "select", "--strict")
        run("--module", "curses", "--strict")

        tool_text = TOOL.read_text(encoding="utf-8")
        assert '"_ios_support"' in tool_text
        assert '"_wmi"' in tool_text
        assert "except Exception:" in tool_text
        # A long full-suite run must expose the last test reached before a
        # hang/stop on M1, x86_64, or ARMv7 rather than buffering until exit.
        assert "subprocess.Popen(" in tool_text
        assert "stderr=subprocess.STDOUT" in tool_text
        assert 'print(line,end="",flush=True)' in tool_text
        assert 'output="".join(lines)' in tool_text

    print("JETOS stdlib qualification tooling: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
