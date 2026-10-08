#!/usr/bin/env python3
"""One-time Gen2 source intake: acquire seeds, internalize, seal, then discard staging."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    print("JETOS Gen2 one-time source intake")
    print("1. Materializing the selected source seeds into temporary staging.")
    run([
        sys.executable,
        "tools/sources.py",
        "sync",
        "jetos-language",
        "linux",
    ])

    print("2. Copying/internalizing those files as JETOS Gen2 source and sealing them.")
    run([sys.executable, "tools/gen2.py", "intake"])
    run([sys.executable, "tools/gen2.py", "verify"])

    print("3. Removing the temporary source-repository staging tree.")
    if SOURCES.exists():
        shutil.rmtree(SOURCES)

    print("4. Re-verifying after staging removal.")
    run([sys.executable, "tools/gen2.py", "verify"])
    print("JETOS Gen2 intake complete. Normal Gen2 build/boot now uses only gen2/vendor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
