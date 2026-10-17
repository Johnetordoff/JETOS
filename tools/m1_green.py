#!/usr/bin/env python3
"""Launch the real arm64 Green Gate from an Apple-Silicon Mac via Docker."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "jetos:m1-green"
PLATFORM = "linux/arm64"


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-timeout", type=int, default=10800)
    parser.add_argument("--boot-timeout", type=int, default=10800)
    parser.add_argument("--evidence", default=".build/m1-green-gate.json")
    args = parser.parse_args()

    if platform.system() != "Darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
        raise SystemExit("M1 Green launcher requires an Apple-Silicon macOS host")
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("M1 Green launcher requires Docker")
    bootstrap = os.environ.get("JETOS_BOOTSTRAP_IMAGE", "").strip()
    if not bootstrap:
        raise SystemExit("set JETOS_BOOTSTRAP_IMAGE to the prepared arm64 Linux tooling image")

    run([
        docker, "build",
        "--platform", PLATFORM,
        "--build-arg", f"JETOS_BOOTSTRAP_IMAGE={bootstrap}",
        "--target", "dev",
        "--tag", IMAGE,
        ".",
    ])
    run([
        docker, "run", "--rm",
        "--platform", PLATFORM,
        "-v", f"{ROOT}:/jetos",
        "-w", "/jetos",
        IMAGE,
        "python3", "tools/m1_green_gate.py",
        "--build-timeout", str(args.build_timeout),
        "--boot-timeout", str(args.boot_timeout),
        "--evidence", args.evidence,
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
