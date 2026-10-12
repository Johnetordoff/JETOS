#!/usr/bin/env python3
"""Reproducible JETOS development build and VM runner."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
VENDOR = ROOT / "vendor"
VENDOR_LINUX = VENDOR / "linux"
VENDOR_CPYTHON = VENDOR / "cpython"
LINUX_SOURCE = BUILD / "linux"
LANGUAGE_SOURCE = BUILD / "jetos-language-src"
LANGUAGE_BUILD = BUILD / "jetos-language-build"
LANGUAGE_PREFIX = BUILD / "jetos-language-install"
ROOTFS = BUILD / "rootfs"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"

LINUX_VERSION = "6.12.96"
LINUX_COMMIT = "6d15a1029d425b15c59463910ebdccc4afe760d6"
CPYTHON_COMMIT = "9d22a5334bd5273962adceeb697a1337e9a0ca21"


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


def vendor_head(source: Path) -> str:
    return run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture=True,
    ).stdout.strip()


def require_vendor(
    name: str,
    source: Path,
    expected_commit: str,
    required_file: str,
) -> None:
    if not (source / required_file).is_file():
        raise SystemExit(
            f"frozen {name} source is missing at {source}. "
            "JETOS will not download it during prepare/build/run. "
            "Acquire the repository with its pinned submodules before building."
        )
    actual = vendor_head(source)
    if actual != expected_commit:
        raise SystemExit(
            f"frozen {name} source mismatch: {actual}; "
            f"required {expected_commit}. JETOS will not fetch or repair it."
        )


def copy_vendor_source(
    source: Path,
    destination: Path,
    commit: str,
    required_file: str,
) -> None:
    marker = destination / ".jetos-vendor-base"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == commit
        and (destination / required_file).is_file()
    ):
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )
    marker.write_text(commit + "\n", encoding="utf-8")


def prepare_sources() -> None:
    """Prepare only from the frozen source checkouts already in this repo."""
    require_vendor("Linux", VENDOR_LINUX, LINUX_COMMIT, "Makefile")
    require_vendor(
        "CPython",
        VENDOR_CPYTHON,
        CPYTHON_COMMIT,
        "Python/sysmodule.c",
    )
    copy_vendor_source(
        VENDOR_LINUX,
        LINUX_SOURCE,
        LINUX_COMMIT,
        "Makefile",
    )
    copy_vendor_source(
        VENDOR_CPYTHON,
        LANGUAGE_SOURCE,
        CPYTHON_COMMIT,
        "Python/sysmodule.c",
    )
    run([
        sys.executable,
        "tools/language.py",
        "patch",
        str(LANGUAGE_SOURCE),
    ])


def find_language_runtime() -> tuple[Path, Path]:
    bindir = LANGUAGE_PREFIX / "bin"
    candidates = sorted(bindir.glob("python3.*")) if bindir.is_dir() else []
    candidates = [
        path
        for path in candidates
        if path.is_file() and "config" not in path.name
    ]
    if not candidates:
        raise SystemExit("JETOS language runtime was not installed")
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
        raise SystemExit(f"JETOS language stdlib not found: {stdlib}")
    return runtime, stdlib


def build_language() -> tuple[Path, Path]:
    bindir = LANGUAGE_PREFIX / "bin"
    runtime_candidates = list(bindir.glob("python3.*")) if bindir.exists() else []
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


def source_status(name: str, source: Path, commit: str, required: str) -> None:
    if not (source / required).is_file():
        print(f"{name}: missing from checkout")
        return
    try:
        head = vendor_head(source)
    except subprocess.CalledProcessError:
        print(f"{name}: present, commit unreadable")
        return
    state = "frozen" if head == commit else "WRONG REVISION"
    print(f"{name}: {state} {head}")


def status() -> None:
    print("source mode: frozen checkout; no prepare/build/run downloads")
    print(f"Linux {LINUX_VERSION}: {LINUX_COMMIT}")
    print(f"CPython ancestor: {CPYTHON_COMMIT}")
    source_status("vendor/linux", VENDOR_LINUX, LINUX_COMMIT, "Makefile")
    source_status(
        "vendor/cpython",
        VENDOR_CPYTHON,
        CPYTHON_COMMIT,
        "Python/sysmodule.c",
    )
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
