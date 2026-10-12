#!/usr/bin/env python3
"""Reproducible JETOS Fat development build and VM runner."""
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
SOURCE_BRAIN = ROOT / "source-brain"
SOURCE_BRAIN_LINUX = SOURCE_BRAIN / "linux"
SOURCE_BRAIN_CPYTHON = SOURCE_BRAIN / "cpython"
LINUX_SOURCE = BUILD / "linux"
LANGUAGE_SOURCE = BUILD / "jetos-language-src"
LANGUAGE_BUILD = BUILD / "jetos-language-build"
LANGUAGE_PREFIX = BUILD / "jetos-language-install"
ROOTFS = BUILD / "rootfs"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"
STDLIB_MANIFEST = BUILD / "stdlib-surface.json"

LINUX_VERSION = "6.12.96"
LINUX_COMMIT = "6d15a1029d425b15c59463910ebdccc4afe760d6"
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


def source_head(source: Path) -> str:
    return run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture=True,
    ).stdout.strip()


def require_source_brain(
    name: str,
    source: Path,
    expected_commit: str,
    required_file: str,
) -> None:
    if not (source / required_file).is_file():
        raise SystemExit(
            f"Source Brain {name} source is missing at {source}. "
            "JETOS will not download it during prepare/build/run. "
            "Acquire the repository with its pinned Source Brain submodules before building."
        )
    actual = source_head(source)
    if actual != expected_commit:
        raise SystemExit(
            f"Source Brain {name} source mismatch: {actual}; "
            f"required {expected_commit}. JETOS will not silently build an unrecorded revision."
        )


def copy_source_brain(
    source: Path,
    destination: Path,
    commit: str,
    required_file: str,
) -> None:
    marker = destination / ".jetos-source-brain-base"
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
    """Prepare only from the exact Source Brain revisions recorded by JETOS."""
    require_source_brain("Linux", SOURCE_BRAIN_LINUX, LINUX_COMMIT, "Makefile")
    require_source_brain(
        "CPython",
        SOURCE_BRAIN_CPYTHON,
        CPYTHON_COMMIT,
        "Python/sysmodule.c",
    )
    copy_source_brain(
        SOURCE_BRAIN_LINUX,
        LINUX_SOURCE,
        LINUX_COMMIT,
        "Makefile",
    )
    copy_source_brain(
        SOURCE_BRAIN_CPYTHON,
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


def qualify_stdlib(runtime: Path) -> None:
    """Prove the language surface before doing any Linux build work."""
    run([
        str(runtime),
        "tools/stdlib_qualify.py",
        "--strict",
        "--manifest",
        str(STDLIB_MANIFEST),
    ])


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
    """Build the Fat development initramfs from exact Source Brain input."""
    run([
        sys.executable,
        "tools/package.py",
        "--profile",
        "fat",
        "--rootfs",
        str(ROOTFS),
        "--output",
        str(INITRAMFS),
        "--python",
        str(runtime),
        "--stdlib",
        str(stdlib),
        "--linux-source",
        str(SOURCE_BRAIN_LINUX),
    ])


def tests() -> None:
    for script in (
        "test.py",
        "test_unicode.py",
        "test_language.py",
        "test_bootstrap.py",
        "test_stdlib_qualify.py",
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
    qualify_stdlib(runtime)
    target_arch = arch()
    kernel = build_kernel(target_arch)
    build_initramfs(runtime, stdlib)
    print("\nJETOS Fat development artifacts")
    print(f"  architecture: {target_arch}")
    print(f"  language:     JETOS on Python {CPYTHON_VERSION}")
    print(f"  runtime:      {runtime}")
    print(f"  stdlib:       {STDLIB_MANIFEST}")
    print(f"  kernel:       {kernel} ({kernel.stat().st_size} bytes)")
    print(f"  Linux source: source-brain/linux @ {LINUX_COMMIT}")
    print(f"  CPython src:  source-brain/cpython @ {CPYTHON_COMMIT}")
    print("  guest source: /usr/src/linux (Fat profile only)")
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
        head = source_head(source)
    except subprocess.CalledProcessError:
        print(f"{name}: present, commit unreadable")
        return
    state = "recorded" if head == commit else "WRONG REVISION"
    print(f"{name}: {state} {head}")


def status() -> None:
    print("source mode: Source Brain; no prepare/build/run downloads")
    print(f"Linux {LINUX_VERSION}: {LINUX_COMMIT}")
    print("Fat source policy: exact Source Brain tree is the build input")
    print("Skinny source policy: complete Linux/CPython source trees are omitted")
    print("reduction policy: preserve the complete qualifying JETOS/Python stdlib surface")
    print(f"CPython {CPYTHON_VERSION} ancestor: {CPYTHON_COMMIT}")
    source_status("source-brain/linux", SOURCE_BRAIN_LINUX, LINUX_COMMIT, "Makefile")
    source_status(
        "source-brain/cpython",
        SOURCE_BRAIN_CPYTHON,
        CPYTHON_COMMIT,
        "Python/sysmodule.c",
    )
    print(f"target architecture: {arch()}")
    for path in (
        LANGUAGE_SOURCE,
        LANGUAGE_BUILD,
        LANGUAGE_PREFIX,
        STDLIB_MANIFEST,
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
        description="JETOS reproducible Fat development environment"
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
