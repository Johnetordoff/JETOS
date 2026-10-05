#!/usr/bin/env python3
"""Build a compact JETOS runtime image from the existing Python-owned builder."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_build", ROOT / "tools/build.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

LEAN_REMOVE_NAMES = frozenset({
    "__pycache__",
    "ensurepip",
    "idlelib",
    "test",
    "tests",
    "turtledemo",
})


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def compact_stdlib(rootfs: Path, stdlib: Path) -> tuple[int, int]:
    target = rootfs / stdlib.resolve().relative_to("/")
    removed_files = 0
    removed_bytes = 0
    if not target.exists():
        return removed_files, removed_bytes

    doomed: list[Path] = []
    for path in target.rglob("*"):
        if path.name in LEAN_REMOVE_NAMES:
            doomed.append(path)
    for path in sorted(doomed, key=lambda value: len(value.parts), reverse=True):
        if not path.exists():
            continue
        if path.is_file() or path.is_symlink():
            try:
                removed_bytes += path.lstat().st_size
            except OSError:
                pass
            removed_files += 1
            remove_tree(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and not child.is_symlink():
                try:
                    removed_bytes += child.stat().st_size
                except OSError:
                    pass
                removed_files += 1
        remove_tree(path)
    return removed_files, removed_bytes


def tree_stats(root: Path) -> tuple[int, int]:
    files = 0
    bytes_total = 0
    if not root.exists():
        return files, bytes_total
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            files += 1
            try:
                bytes_total += path.stat().st_size
            except OSError:
                pass
    return files, bytes_total


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact JETOS rootfs/initramfs")
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--stdlib", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, default=ROOT / ".build/rootfs")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".build/jetos-initramfs.cpio.gz",
    )
    parser.add_argument("--profile", choices=("lean", "full"), default="lean")
    args = parser.parse_args()

    build.make_rootfs(args.rootfs, args.python, args.stdlib)
    before_files, before_bytes = tree_stats(args.rootfs)
    if args.profile == "lean":
        removed_files, removed_bytes = compact_stdlib(args.rootfs, args.stdlib)
        print(
            f"lean profile removed {removed_files} files / {removed_bytes} bytes "
            "of stdlib tests/demos/bootstrap caches"
        )
    after_files, after_bytes = tree_stats(args.rootfs)
    build.build_initramfs(args.rootfs, args.output)

    print(f"rootfs profile: {args.profile}")
    print(f"rootfs before: {before_files} files / {before_bytes} bytes")
    print(f"rootfs after:  {after_files} files / {after_bytes} bytes")
    print(f"initramfs:     {args.output.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
