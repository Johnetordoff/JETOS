"""Startup file for the first JETOS JetLang shell."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from jetos import dunicode


def qualify() -> int:
    """Run the qualification armed in this Fat image from the live JetLang shell."""
    marker = Path("/jetos/stdlib-qualify")
    if not marker.is_file():
        print("No stdlib qualification is armed in this image.")
        return 0
    mode = marker.read_text(encoding="utf-8").strip()
    if mode not in {"fast", "full"}:
        raise RuntimeError(f"invalid stdlib qualification mode: {mode!r}")
    command = [
        sys.executable,
        "/jetos/tools/stdlib_qualify.py",
        "--strict",
        "--manifest",
        "/tmp/stdlib-surface.json",
    ]
    if mode == "full":
        command.append("--full")
    print(f"JETOS stdlib qualification from interactive JetLang: {mode}", flush=True)
    result = subprocess.run(command, check=False)
    state = "PASS" if result.returncode == 0 else "FAIL"
    print(f"JETOS_STDLIB_QUALIFICATION={state}", flush=True)
    return result.returncode


sys.ps1 = "jetos> "
sys.ps2 = ".....> "
print("JetLang is JETOS's first shell. `dunicode` is preloaded.")
if Path("/jetos/stdlib-qualify").is_file():
    print("Run qualify() from this prompt for the armed stdlib/CPython regression suite.")
