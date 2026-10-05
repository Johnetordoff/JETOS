#!/usr/bin/env python3
"""Build JETOS Fat or Skinny runtime images."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import mode  # noqa: E402

SPEC = importlib.util.spec_from_file_location("jetos_build", ROOT / "tools/build.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

SKINNY_REMOVE_NAMES = frozenset({
    "__pycache__",
    "ensurepip",
    "idlelib",
    "test",
    "tests",
    "turtledemo",
})
FAT_SOURCE_IGNORE = frozenset({
    ".build",
    ".git",
    ".venv",
    "__pycache__",
    "sources",
})


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def compact_stdlib(rootfs: Path, stdlib: Path) -> tuple[int, int]:
    """Remove development-only standard-library payload for Skinny Mode."""
    target = rootfs / stdlib.resolve().relative_to("/")
    removed_files = 0
    removed_bytes = 0
    if not target.exists():
        return removed_files, removed_bytes

    doomed: list[Path] = []
    for path in target.rglob("*"):
        if path.name in SKINNY_REMOVE_NAMES:
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


def _ignore_fat_source(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in FAT_SOURCE_IGNORE or name.endswith(".pyc")}


def copy_fat_sources(rootfs: Path) -> tuple[Path, Path]:
    """Carry editable JETOS and JETOS Language source inside Fat Mode."""
    language_source = ROOT / "sources" / "cpython"
    if not language_source.is_dir():
        raise SystemExit(
            "Fat Mode requires materialized JETOS Language source. "
            "Run `python jetos.py sources sync jetos-language` first."
        )

    source_root = rootfs / "usr" / "src"
    jetos_target = source_root / "jetos"
    language_target = source_root / "jetos-language"
    remove_tree(jetos_target)
    remove_tree(language_target)
    source_root.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ROOT,
        jetos_target,
        ignore=_ignore_fat_source,
        symlinks=True,
    )
    shutil.copytree(
        language_source,
        language_target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        symlinks=True,
    )
    return jetos_target, language_target


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
    parser = argparse.ArgumentParser(description="Build a JETOS Fat/ Skinny rootfs/initramfs")
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--stdlib", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, default=ROOT / ".build/rootfs")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".build/jetos-initramfs.cpio.gz",
    )
    parser.add_argument(
        "--profile",
        choices=mode.CLI_CHOICES,
        default=mode.SKINNY,
        help="fat=developer/PC image; skinny=device/runtime image (full/lean are legacy aliases)",
    )
    args = parser.parse_args()
    canonical_mode = mode.normalize(args.profile)

    build.make_rootfs(args.rootfs, args.python, args.stdlib)
    before_files, before_bytes = tree_stats(args.rootfs)

    if canonical_mode == mode.SKINNY:
        removed_files, removed_bytes = compact_stdlib(args.rootfs, args.stdlib)
        print(
            f"Skinny Mode removed {removed_files} files / {removed_bytes} bytes "
            "of standard-library tests/demos/bootstrap caches"
        )
    else:
        jetos_source, language_source = copy_fat_sources(args.rootfs)
        print(f"Fat Mode JETOS source: {jetos_source}")
        print(f"Fat Mode JETOS Language source: {language_source}")

    after_files, after_bytes = tree_stats(args.rootfs)
    build.build_initramfs(args.rootfs, args.output)

    print(f"JETOS mode:      {canonical_mode}")
    if args.profile != canonical_mode:
        print(f"legacy alias:    {args.profile} -> {canonical_mode}")
    print(f"rootfs before:   {before_files} files / {before_bytes} bytes")
    print(f"rootfs after:    {after_files} files / {after_bytes} bytes")
    print(f"initramfs:       {args.output.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
