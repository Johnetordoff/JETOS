#!/usr/bin/env python3
"""Launch the real arm64 Green Gate from an Apple-Silicon Mac.

Docker (a Linux/arm64 container) is only the build harness: it runs the
repository tests and builds the fresh JetLang, JetOS kernel and Fat image.
The guest then boots on the Mac itself with QEMU + Hypervisor.framework
(``--boot host``, the default when the host QEMU offers HVF). M1 cannot give
Docker Desktop's Linux VM nested KVM, so booting inside the container would
fall back to TCG emulation and be bounded by the Docker VM's memory.
``--boot container`` keeps the previous all-in-container path.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "jetos:m1-green"
PLATFORM = "linux/arm64"
GATE = "tools/m1_green_gate.py"


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def host_hvf_qemu() -> str | None:
    """Return the host qemu-system-aarch64 if it offers Hypervisor.framework."""
    qemu = shutil.which("qemu-system-aarch64")
    if qemu is None:
        return None
    try:
        result = subprocess.run(
            [qemu, "-accel", "help"], check=False, text=True, capture_output=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if not any(line.strip() == "hvf" for line in result.stdout.splitlines()):
        return None
    return qemu


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-timeout", type=int, default=10800)
    parser.add_argument("--boot-timeout", type=int, default=10800)
    parser.add_argument("--evidence", default=".build/m1-green-gate.json")
    parser.add_argument(
        "--boot",
        choices=("auto", "host", "container"),
        default="auto",
        help="where the guest boots: host = native QEMU/HVF on this Mac (auto picks it when available)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="with --boot host, reboot the artifacts the last build stage verified",
    )
    args = parser.parse_args()

    if platform.system() != "Darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
        raise SystemExit("M1 Green launcher requires an Apple-Silicon macOS host")

    qemu = host_hvf_qemu()
    boot = args.boot
    if boot == "auto":
        boot = "host" if qemu else "container"
        if qemu is None:
            print(
                "host qemu-system-aarch64 with HVF not found; booting inside the "
                "container under TCG (install QEMU on the Mac for native speed)",
                flush=True,
            )
    if boot == "host" and qemu is None:
        raise SystemExit("--boot host needs qemu-system-aarch64 with the hvf accelerator on this Mac")
    if args.skip_build and boot != "host":
        raise SystemExit("--skip-build only applies to --boot host")

    gate_args = [
        "--build-timeout", str(args.build_timeout),
        "--boot-timeout", str(args.boot_timeout),
        "--evidence", args.evidence,
    ]

    if not args.skip_build:
        docker = shutil.which("docker")
        if not docker:
            raise SystemExit("M1 Green launcher requires Docker for the Linux/arm64 build stage")
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
            "python3", GATE,
            "--stage", "build" if boot == "host" else "all",
            *gate_args,
        ])

    if boot == "host":
        # Same bind-mounted .build tree: the boot stage re-hashes the kernel
        # and initramfs and refuses anything but the recorded revision/build.
        run([sys.executable, GATE, "--stage", "boot", *gate_args])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
