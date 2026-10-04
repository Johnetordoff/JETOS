#!/usr/bin/env python3
"""Reproducible JETOS development build and VM runner."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
LINUX_SOURCE = BUILD / "linux"
LANGUAGE_SOURCE = BUILD / "jetos-language-src"
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


def arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(
        f"JETOS dev VM does not yet support host architecture {machine!r}"
    )


def ensure_checkout(
    url: str,
    commit: str,
    destination: Path,
    branch: str | None = None,
) -> None:
    if destination.exists():
        head = run(
            ["git", "rev-parse", "HEAD"],
            cwd=destination,
            capture=True,
        ).stdout.strip()
        if head == commit:
            return
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=destination,
            text=True,
        )
        if ancestor.returncode == 0:
            return
        raise SystemExit(
            f"{destination} exists at {head}, but pinned base {commit} is "
            "not an ancestor; remove it or inspect it before continuing"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "init", str(destination)])
    run(["git", "remote", "add", "origin", url], cwd=destination)
    run(["git", "fetch", "--depth", "1", "origin", commit], cwd=destination)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)
    if branch:
        run(["git", "switch", "-c", branch], cwd=destination)


def prepare_sources() -> None:
    ensure_checkout(LINUX_REPOSITORY, LINUX_COMMIT, LINUX_SOURCE)
    ensure_checkout(
        CPYTHON_REPOSITORY,
        CPYTHON_COMMIT,
        LANGUAGE_SOURCE,
        "jetos-language",
    )
    run([
        sys.executable,
        "tools/language.py",
        "patch",
        str(LANGUAGE_SOURCE),
    ])
    status = run(
        ["git", "status", "--porcelain"],
        cwd=LANGUAGE_SOURCE,
        capture=True,
    ).stdout
    if status.strip():
        run(
            ["git", "add", "Include/jetos.h", "Python/sysmodule.c"],
            cwd=LANGUAGE_SOURCE,
        )
        run([
            "git",
            "-c",
            "user.name=JETOS Bootstrap",
            "-c",
            "user.email=jetos@localhost",
            "commit",
            "-m",
            f"Start JETOS Language from Python {CPYTHON_VERSION}",
        ], cwd=LANGUAGE_SOURCE)


def find_language_runtime() -> tuple[Path, Path]:
    bindir = LANGUAGE_PREFIX / "bin"
    candidates = sorted(bindir.glob("python3.*")) if bindir.is_dir() else []
    candidates = [
        path
        for path in candidates
        if path.is_file() and "config" not in path.name
    ]
    if not candidates:
        raise SystemExit("JETOS Language runtime was not installed")
    runtime = candidates[-1]
    stdlib_result = run(
        [
            str(runtime),
            "-c",
            "import sysconfig; print(sysconfig.get_path('stdlib'))",
        ],
        capture=True,
    )
    stdlib = Path(stdlib_result.stdout.strip())
    if not stdlib.is_dir():
        raise SystemExit(f"JETOS Language stdlib not found: {stdlib}")
    return runtime, stdlib


def build_language() -> tuple[Path, Path]:
    bindir = LANGUAGE_PREFIX / "bin"
    runtime_candidates = (
        [
            path for path in bindir.glob("python3.*")
            if path.is_file() and "config" not in path.name
        ]
        if bindir.exists()
        else []
    )
    if not runtime_candidates:
        run([
            sys.executable,
            "tools/language.py",
            "build",
            str(LANGUAGE_SOURCE),
            "--build",
            str(LANGUAGE_BUILD),
            "--prefix",
            str(LANGUAGE_PREFIX),
        ])
        run([
            sys.executable,
            "tools/language.py",
            "smoke",
            "--build",
            str(LANGUAGE_BUILD),
        ])
        run([
            sys.executable,
            "tools/language.py",
            "install",
            "--build",
            str(LANGUAGE_BUILD),
        ])
    runtime, stdlib = find_language_runtime()
    run([
        str(runtime),
        "-c",
        (
            "import sys; "
            "assert sys.implementation.name == 'jetos'; "
            f"assert sys.version_info[:3] == (3, 14, 8); "
            "assert sys.version_info.releaselevel == 'final'; "
            "assert sys.implementation.supports_isolated_interpreters; "
            "print(sys.implementation)"
        ),
    ])
    return runtime, stdlib


def kernel_image(target_arch: str) -> Path:
    if target_arch == "x86_64":
        return LINUX_SOURCE / "arch/x86/boot/bzImage"
    return LINUX_SOURCE / "arch/arm64/boot/Image"


def build_kernel(target_arch: str) -> Path:
    image = kernel_image(target_arch)
    if not image.exists():
        run([
            sys.executable,
            "tools/build.py",
            "kernel",
            str(LINUX_SOURCE),
            "--arch",
            target_arch,
        ])
    if not image.exists():
        raise SystemExit(f"kernel build did not produce {image}")
    return image


def build_initramfs(runtime: Path, stdlib: Path) -> None:
    run([
        sys.executable,
        "tools/build.py",
        "initramfs",
        "--rootfs",
        str(ROOTFS),
        "--output",
        str(INITRAMFS),
        "--python",
        str(runtime),
        "--stdlib",
        str(stdlib),
    ])


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
    ):
        run([sys.executable, f"tools/{script}"])


def build_all() -> tuple[Path, Path, Path]:
    if platform.system() != "Linux":
        raise SystemExit(
            "native JETOS development currently requires Linux; "
            "use `python jetos.py dev` to run the Linux development "
            "environment in Docker"
        )
    tests()
    prepare_sources()
    runtime, stdlib = build_language()
    target_arch = arch()
    kernel = build_kernel(target_arch)
    build_initramfs(runtime, stdlib)
    print("\nJETOS development artifacts")
    print(f"  architecture: {target_arch}")
    print(f"  language:     {runtime}")
    print(f"  Python base:  {CPYTHON_VERSION} stable")
    print(f"  kernel:       {kernel} ({kernel.stat().st_size} bytes)")
    print(f"  initramfs:    {INITRAMFS} ({INITRAMFS.stat().st_size} bytes)")
    return runtime, kernel, INITRAMFS


def boot(kernel: Path, initramfs: Path) -> None:
    run_args = [
        sys.executable,
        "tools/build.py",
        "vm",
        "--arch",
        arch(),
        "--kernel",
        str(kernel),
        "--initramfs",
        str(initramfs),
    ]
    os.execv(sys.executable, run_args)


def status() -> None:
    print(f"Linux {LINUX_VERSION}: {LINUX_COMMIT}")
    print(f"Python stable base {CPYTHON_VERSION}: {CPYTHON_COMMIT}")
    print(f"target architecture: {arch()}")
    for path in (
        LANGUAGE_SOURCE,
        LANGUAGE_BUILD,
        LANGUAGE_PREFIX,
        LINUX_SOURCE,
        ROOTFS,
        INITRAMFS,
    ):
        print(
            f"{path.relative_to(ROOT)}: "
            f"{'present' if path.exists() else 'missing'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JETOS reproducible development environment"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("prepare")
    sub.add_parser("build")
    sub.add_parser("run")
    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "prepare":
        prepare_sources()
    elif args.command == "build":
        build_all()
    elif args.command == "run":
        _, kernel, initramfs = build_all()
        boot(kernel, initramfs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
