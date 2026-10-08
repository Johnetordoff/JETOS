#!/usr/bin/env python3
"""Build and boot JETOS Gen2 from its sealed local source tree only."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import mode  # noqa: E402

GEN2 = ROOT / "gen2" / "vendor"
BUILD = ROOT / ".build"
JETOS_KERNEL_SOURCE = GEN2 / "jetos-kernel"
JETOS_PYTHON_SOURCE = GEN2 / "jetos-python"
JETOS_PYTHON_BUILD = BUILD / "jetos-python-build"
JETOS_PYTHON_PREFIX = BUILD / "jetos-python-install"
ROOTFS = BUILD / "rootfs"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"


def run(args: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=cwd or ROOT, check=True, text=True, capture_output=capture)


def architecture() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(f"unsupported host architecture {machine!r}")


def verify_gen2() -> None:
    """Refuse network/source fallback: a Gen2 boot requires a sealed local tree."""
    run([sys.executable, "tools/gen2.py", "verify"])


def runtime_paths() -> tuple[Path, Path]:
    candidates = [
        path for path in (JETOS_PYTHON_PREFIX / "bin").glob("python3.*")
        if path.is_file() and "config" not in path.name
    ]
    if not candidates:
        raise SystemExit("JetOS Python runtime missing; build it first")
    runtime = sorted(candidates)[-1]
    stdlib = Path(run(
        [str(runtime), "-c", "import sysconfig; print(sysconfig.get_path('stdlib'))"],
        capture=True,
    ).stdout.strip())
    return runtime, stdlib


def build_jetos_python() -> tuple[Path, Path]:
    installed = JETOS_PYTHON_PREFIX / "bin"
    if not installed.exists() or not list(installed.glob("python3.*")):
        # language.py is JETOS-owned transformation/build orchestration.  Its input
        # is the frozen JetOS Python tree; it performs no source fetch here.
        run([
            sys.executable, "tools/language.py", "patch", str(JETOS_PYTHON_SOURCE),
        ])
        run([
            sys.executable, "tools/language.py", "build", str(JETOS_PYTHON_SOURCE),
            "--build", str(JETOS_PYTHON_BUILD), "--prefix", str(JETOS_PYTHON_PREFIX),
        ])
        run([
            sys.executable, "tools/language.py", "smoke", "--build", str(JETOS_PYTHON_BUILD),
        ])
        run([
            sys.executable, "tools/language.py", "install", "--build", str(JETOS_PYTHON_BUILD),
        ])
    return runtime_paths()


def kernel_image(target_architecture: str) -> Path:
    if target_architecture == "x86_64":
        return JETOS_KERNEL_SOURCE / "arch/x86/boot/bzImage"
    return JETOS_KERNEL_SOURCE / "arch/arm64/boot/Image"


def build_kernel(target_architecture: str) -> Path:
    image = kernel_image(target_architecture)
    if not image.exists():
        run([
            sys.executable, "tools/build.py", "kernel", str(JETOS_KERNEL_SOURCE),
            "--arch", target_architecture,
        ])
    return image


def tests() -> None:
    for script in (
        "test.py", "test_unicode.py", "test_language.py", "test_bootstrap.py",
        "test_desktop.py", "test_capabilities.py", "test_policy.py",
        "test_interpreters.py", "test_storage.py", "test_storage_modes.py",
        "test_sources.py", "test_modes.py", "test_constitution.py", "test_console.py",
    ):
        run([sys.executable, f"tools/{script}"])


def build_all(profile: str) -> tuple[Path, Path]:
    if platform.system() != "Linux":
        raise SystemExit("native Gen2 build requires Linux; use the portable container path")
    canonical_mode = mode.normalize(profile)
    verify_gen2()
    tests()
    runtime, stdlib = build_jetos_python()
    target_architecture = architecture()
    kernel = build_kernel(target_architecture)
    run([
        sys.executable, "tools/image.py",
        "--python", str(runtime), "--stdlib", str(stdlib),
        "--rootfs", str(ROOTFS), "--output", str(INITRAMFS),
        "--profile", canonical_mode,
    ])
    size_command = [sys.executable, "tools/size_report.py"]
    if canonical_mode == mode.SKINNY:
        size_command.append("--strict")
    run(size_command)
    return kernel, INITRAMFS


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/boot JETOS Gen2")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "run"):
        command = sub.add_parser(name)
        command.add_argument("--profile", choices=mode.CLI_CHOICES, default=mode.SKINNY)
        command.add_argument("--encryption", choices=("on", "off"), default="on")
        command.add_argument("--display", choices=("serial", "window", "vnc"), default="serial")
        command.add_argument("--vnc-bind", default="127.0.0.1")
    sub.add_parser("verify", help="verify sealed Gen2 source and exit")
    sub.add_parser("status", help="show local Gen2 build inputs")
    args = parser.parse_args()

    if args.command == "verify":
        verify_gen2()
        return 0
    if args.command == "status":
        print("generation: Gen2")
        print(f"JetOS Python source: {JETOS_PYTHON_SOURCE}")
        print(f"JETOS kernel source: {JETOS_KERNEL_SOURCE}")
        print(f"build root: {BUILD}")
        print(f"architecture: {architecture()}")
        verify_gen2()
        return 0

    kernel, initramfs = build_all(args.profile)
    if args.command == "build":
        return 0
    os.execv(sys.executable, [
        sys.executable, "tools/vm.py",
        "--arch", architecture(),
        "--kernel", str(kernel),
        "--initramfs", str(initramfs),
        "--encryption", args.encryption,
        "--display", args.display,
        "--vnc-bind", args.vnc_bind,
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
