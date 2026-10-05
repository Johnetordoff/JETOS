#!/usr/bin/env python3
"""Reproducible JETOS development build and VM runner.

Upstream source lives visibly under sources/. Compiled/generated artifacts live
under .build/. Fat Mode carries editable JETOS/JETOS Language source inside the
image; Skinny Mode is the stripped device/runtime personality.
"""
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

SOURCES = ROOT / "sources"
BUILD = ROOT / ".build"

LINUX_SOURCE = SOURCES / "linux"
LANGUAGE_SOURCE = SOURCES / "cpython"
LANGUAGE_BUILD = BUILD / "jetos-language-build"
LANGUAGE_PREFIX = BUILD / "jetos-language-install"
ROOTFS = BUILD / "rootfs"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"

LINUX_REPOSITORY = "https://github.com/gregkh/linux.git"
LINUX_VERSION = "6.12.96"
LINUX_COMMIT = "6d15a1029d425b15c59463910ebdccc4afe760d6"
CPYTHON_REPOSITORY = "https://github.com/python/cpython.git"
CPYTHON_VERSION = "3.14.8"
CPYTHON_COMMIT = "8e6e75d9102e39bed2a2b279203a396741180f12"


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def architecture() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(f"unsupported host architecture {machine!r}")


def prepare_sources() -> None:
    """Materialize the visible sources needed for a normal VM build."""
    run(
        [
            sys.executable,
            "tools/sources.py",
            "sync",
            "jetos-language",
            "linux",
        ]
    )


def runtime_paths() -> tuple[Path, Path]:
    candidates = [
        path
        for path in (LANGUAGE_PREFIX / "bin").glob("python3.*")
        if path.is_file() and "config" not in path.name
    ]
    if not candidates:
        raise SystemExit("JETOS Language runtime missing; build it first")
    runtime = sorted(candidates)[-1]
    stdlib = Path(
        run(
            [
                str(runtime),
                "-c",
                "import sysconfig; print(sysconfig.get_path('stdlib'))",
            ],
            capture=True,
        ).stdout.strip()
    )
    return runtime, stdlib


def build_language() -> tuple[Path, Path]:
    installed = LANGUAGE_PREFIX / "bin"
    if not installed.exists() or not list(installed.glob("python3.*")):
        run(
            [
                sys.executable,
                "tools/language.py",
                "build",
                str(LANGUAGE_SOURCE),
                "--build",
                str(LANGUAGE_BUILD),
                "--prefix",
                str(LANGUAGE_PREFIX),
            ]
        )
        run(
            [
                sys.executable,
                "tools/language.py",
                "smoke",
                "--build",
                str(LANGUAGE_BUILD),
            ]
        )
        run(
            [
                sys.executable,
                "tools/language.py",
                "install",
                "--build",
                str(LANGUAGE_BUILD),
            ]
        )
    return runtime_paths()


def kernel_image(target_architecture: str) -> Path:
    if target_architecture == "x86_64":
        return LINUX_SOURCE / "arch/x86/boot/bzImage"
    return LINUX_SOURCE / "arch/arm64/boot/Image"


def build_kernel(target_architecture: str) -> Path:
    image = kernel_image(target_architecture)
    if not image.exists():
        run(
            [
                sys.executable,
                "tools/build.py",
                "kernel",
                str(LINUX_SOURCE),
                "--arch",
                target_architecture,
            ]
        )
    return image


def tests() -> None:
    for script in (
        "test.py",
        "test_unicode.py",
        "test_language.py",
        "test_bootstrap.py",
        "test_desktop.py",
        "test_capabilities.py",
        "test_policy.py",
        "test_interpreters.py",
        "test_storage.py",
        "test_storage_modes.py",
    ):
        run([sys.executable, f"tools/{script}"])


def build_all(profile: str) -> tuple[Path, Path]:
    if platform.system() != "Linux":
        raise SystemExit("native build requires Linux; use `python jetos.py dev`")

    canonical_mode = mode.normalize(profile)
    tests()
    prepare_sources()
    runtime, stdlib = build_language()
    target_architecture = architecture()
    kernel = build_kernel(target_architecture)
    run(
        [
            sys.executable,
            "tools/image.py",
            "--python",
            str(runtime),
            "--stdlib",
            str(stdlib),
            "--rootfs",
            str(ROOTFS),
            "--output",
            str(INITRAMFS),
            "--profile",
            canonical_mode,
        ]
    )
    size_command = [sys.executable, "tools/size_report.py"]
    if canonical_mode == mode.SKINNY:
        size_command.append("--strict")
    run(size_command)
    return kernel, INITRAMFS


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and boot JETOS in a VM")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("build", "run"):
        command = sub.add_parser(name)
        command.add_argument(
            "--profile",
            choices=mode.CLI_CHOICES,
            default=mode.SKINNY,
            help="fat=developer/PC; skinny=device/runtime (full/lean are legacy aliases)",
        )
        command.add_argument("--encryption", choices=("on", "off"), default="on")
        command.add_argument(
            "--display",
            choices=("serial", "window", "vnc"),
            default="serial",
        )
        command.add_argument("--vnc-bind", default="127.0.0.1")

    sub.add_parser("prepare", help="materialize Linux + JETOS Language source")
    sub.add_parser("status", help="show pinned build inputs")
    args = parser.parse_args()

    if args.command == "prepare":
        prepare_sources()
        return 0

    if args.command == "status":
        print(f"Linux {LINUX_VERSION}: {LINUX_COMMIT}")
        print(f"Python {CPYTHON_VERSION}: {CPYTHON_COMMIT}")
        print(f"source root: {SOURCES}")
        print(f"build root: {BUILD}")
        print(f"architecture: {architecture()}")
        print(f"canonical modes: {', '.join(mode.MODES)}")
        return 0

    kernel, initramfs = build_all(args.profile)
    if args.command == "build":
        return 0

    os.execv(
        sys.executable,
        [
            sys.executable,
            "tools/vm.py",
            "--arch",
            architecture(),
            "--kernel",
            str(kernel),
            "--initramfs",
            str(initramfs),
            "--encryption",
            args.encryption,
            "--display",
            args.display,
            "--vnc-bind",
            args.vnc_bind,
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
