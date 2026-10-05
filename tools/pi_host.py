#!/usr/bin/env python3
"""Host-side wrapper that builds a Raspberry Pi image in ARM64 Docker."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a flashable Raspberry Pi JETOS image")
    parser.add_argument("--model", choices=("pi4", "pi5"), default="pi4")
    parser.add_argument("--profile", choices=("lean", "full"), default="lean")
    parser.add_argument("--network", choices=("on", "off"), default="off")
    parser.add_argument("--size-mib", type=int, default=1024)
    args = parser.parse_args()

    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is required for the portable ARM64 Pi image build")

    BUILD.mkdir(parents=True, exist_ok=True)
    run([docker, "build", "--platform", "linux/arm64", "-t", "jetos:pi", "."])
    run(
        [
            docker,
            "run",
            "--rm",
            "--platform",
            "linux/arm64",
            "-v",
            f"{ROOT}:/jetos",
            "-w",
            "/jetos",
            "jetos:pi",
            "python",
            "tools/pi.py",
            "build",
            "--model",
            args.model,
            "--profile",
            args.profile,
            "--network",
            args.network,
            "--size-mib",
            str(args.size_mib),
        ]
    )
    output = BUILD / f"jetos-{args.model}.img"
    print(f"\nJETOS image ready for flashing: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
