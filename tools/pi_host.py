#!/usr/bin/env python3
"""Host-side wrapper that builds a Raspberry Pi image in ARM64 Docker."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import mode  # noqa: E402

BUILD = ROOT / ".build"


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a flashable Raspberry Pi JETOS image")
    parser.add_argument("--model", choices=("pi4", "pi5"), default="pi4")
    parser.add_argument(
        "--profile",
        choices=(mode.SKINNY, "lean"),
        default=mode.SKINNY,
        help="Raspberry Pi is currently a Skinny device target; lean is the legacy alias",
    )
    parser.add_argument("--network", choices=("on", "off"), default="off")
    parser.add_argument("--size-mib", type=int, default=1024)
    args = parser.parse_args()

    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is required for the portable ARM64 Pi image build")

    canonical_mode = mode.normalize(args.profile)
    if canonical_mode != mode.SKINNY:
        raise SystemExit("Raspberry Pi image path currently supports Skinny Mode only")

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
            # Keep ARM64 compiler/runtime artifacts isolated from an x86-64 host build.
            "-v",
            "jetos_pi_language_build:/jetos/.build/jetos-language-build",
            "-v",
            "jetos_pi_language_install:/jetos/.build/jetos-language-install",
            "-w",
            "/jetos",
            "jetos:pi",
            "python",
            "tools/pi.py",
            "build",
            "--model",
            args.model,
            "--profile",
            "lean",
            "--network",
            args.network,
            "--size-mib",
            str(args.size_mib),
        ]
    )
    output = BUILD / f"jetos-{args.model}.img"
    print(f"\nJETOS image ready for flashing: {output}")
    print("JETOS mode: skinny")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
