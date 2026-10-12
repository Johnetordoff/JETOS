#!/usr/bin/env python3
"""Build Fat or Skinny JETOS rootfs/initramfs images."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BUILD_TOOL = ROOT / "tools/build.py"
STDLIB_TOOL = ROOT / "tools/stdlib_qualify.py"
PROFILE_FAT = "fat"
PROFILE_SKINNY = "skinny"

SPEC = importlib.util.spec_from_file_location("jetos_build", BUILD_TOOL)
if SPEC is None or SPEC.loader is None:
    raise SystemExit(f"cannot load JETOS build tool: {BUILD_TOOL}")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def copy_linux_source(source: Path, rootfs: Path) -> Path:
    """Install every Linux working-tree file into Fat /usr/src/linux.

    Git checkout metadata is excluded because it is not part of the Linux
    source tree and would point outside the guest filesystem.
    """
    source = source.resolve()
    if not (source / "Makefile").is_file():
        raise SystemExit(f"not a complete Linux source tree: {source}")

    target = rootfs / "usr/src/linux"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )
    return target


def install_stdlib_qualification(
    rootfs: Path,
    mode: str | None = None,
) -> Path:
    """Install the Fat qualification tool and optionally arm first boot."""
    target = rootfs / "jetos/tools/stdlib_qualify.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STDLIB_TOOL, target)
    marker = rootfs / "jetos/stdlib-qualify"
    marker.unlink(missing_ok=True)
    if mode is not None:
        marker.write_text(mode + "\n", encoding="utf-8")
    return target


def package_rootfs(
    *,
    profile: str,
    rootfs: Path,
    output: Path,
    python: Path,
    stdlib: Path,
    linux_source: Path | None,
    stdlib_qualify: str | None,
) -> None:
    """Construct one profile without leaking Fat source/tests into Skinny."""
    if profile not in {PROFILE_FAT, PROFILE_SKINNY}:
        raise ValueError(f"unknown JETOS image profile: {profile!r}")

    if profile == PROFILE_FAT and linux_source is None:
        raise SystemExit("Fat packaging requires --linux-source")
    if profile == PROFILE_SKINNY and stdlib_qualify is not None:
        raise SystemExit(
            "Skinny packaging cannot arm the Fat stdlib qualification suite"
        )

    build.make_rootfs(rootfs, python, stdlib)

    if profile == PROFILE_FAT:
        assert linux_source is not None
        installed = copy_linux_source(linux_source, rootfs)
        install_stdlib_qualification(rootfs, stdlib_qualify)
        print(
            "Fat Linux source installed in guest: "
            f"{installed.relative_to(rootfs)}"
        )
        if stdlib_qualify:
            print(f"guest stdlib qualification armed: {stdlib_qualify}")
    else:
        # build.make_rootfs() recreates rootfs from scratch.  Do not add Linux
        # source, CPython source, Source Brain worktrees or development tests.
        # Skinny receives only the runtime assembled by the rootfs builder.
        print("Skinny profile: Source Brain trees and Fat qualification tools omitted")

    build.build_initramfs(rootfs, output)


def main() -> int:
    python, stdlib = build.defaults()
    parser = argparse.ArgumentParser(
        description="Package a Fat development or Skinny runtime JETOS image"
    )
    parser.add_argument(
        "--profile",
        choices=(PROFILE_FAT, PROFILE_SKINNY),
        default=PROFILE_FAT,
        help="Fat keeps source/qualification material; Skinny keeps runtime only",
    )
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=python)
    parser.add_argument("--stdlib", type=Path, default=stdlib)
    parser.add_argument("--linux-source", type=Path)
    parser.add_argument(
        "--stdlib-qualify",
        choices=("fast", "full"),
        help="Fat only: arm this image to run stdlib qualification during first boot",
    )
    args = parser.parse_args()

    package_rootfs(
        profile=args.profile,
        rootfs=args.rootfs,
        output=args.output,
        python=args.python,
        stdlib=args.stdlib,
        linux_source=args.linux_source,
        stdlib_qualify=args.stdlib_qualify,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
