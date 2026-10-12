#!/usr/bin/env python3
"""Build a JETOS rootfs/initramfs with the complete frozen Linux source tree."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BUILD_TOOL = ROOT / "tools/build.py"
STDLIB_TOOL = ROOT / "tools/stdlib_qualify.py"
OS_TOOL = ROOT / "tools/os_qualify.py"

SPEC = importlib.util.spec_from_file_location("jetos_build", BUILD_TOOL)
if SPEC is None or SPEC.loader is None:
    raise SystemExit(f"cannot load JETOS build tool: {BUILD_TOOL}")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def copy_linux_source(source: Path, rootfs: Path) -> Path:
    """Install every Linux working-tree file into /usr/src/linux.

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
    """Install language/OS qualification tools and optionally arm first boot."""
    tools = rootfs / "jetos/tools"
    tools.mkdir(parents=True, exist_ok=True)
    target = tools / "stdlib_qualify.py"
    shutil.copy2(STDLIB_TOOL, target)
    shutil.copy2(OS_TOOL, tools / "os_qualify.py")
    marker = rootfs / "jetos/stdlib-qualify"
    marker.unlink(missing_ok=True)
    if mode is not None:
        marker.write_text(mode + "\n", encoding="utf-8")
    return target


def main() -> int:
    python, stdlib = build.defaults()
    parser = argparse.ArgumentParser(
        description="Package JETOS with the complete frozen Linux source tree"
    )
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=python)
    parser.add_argument("--stdlib", type=Path, default=stdlib)
    parser.add_argument("--linux-source", type=Path, required=True)
    parser.add_argument(
        "--stdlib-qualify",
        choices=("fast", "full"),
        help="arm this image to run stdlib + Python/OS qualification during first boot",
    )
    args = parser.parse_args()

    build.make_rootfs(args.rootfs, args.python, args.stdlib)
    installed = copy_linux_source(args.linux_source, args.rootfs)
    install_stdlib_qualification(args.rootfs, args.stdlib_qualify)
    build.build_initramfs(args.rootfs, args.output)
    print(f"Linux source installed in guest: {installed.relative_to(args.rootfs)}")
    if args.stdlib_qualify:
        print(f"guest stdlib + OS qualification armed: {args.stdlib_qualify}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
