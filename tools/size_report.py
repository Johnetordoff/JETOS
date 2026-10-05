#!/usr/bin/env python3
"""Measure JETOS runtime image size and enforce bootstrap budgets."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTFS = ROOT / ".build/rootfs"
DEFAULT_INITRAMFS = ROOT / ".build/jetos-initramfs.cpio.gz"


def tree_stats(root: Path) -> tuple[int, int, list[tuple[int, Path]]]:
    files = 0
    total = 0
    largest: list[tuple[int, Path]] = []
    if not root.exists():
        return files, total, largest
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        files += 1
        total += size
        largest.append((size, path))
    largest.sort(reverse=True, key=lambda item: item[0])
    return files, total, largest


def mib(value: int) -> float:
    return value / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS image-size report")
    parser.add_argument("--rootfs", type=Path, default=DEFAULT_ROOTFS)
    parser.add_argument("--initramfs", type=Path, default=DEFAULT_INITRAMFS)
    parser.add_argument("--rootfs-budget-mib", type=float, default=128.0)
    parser.add_argument("--initramfs-budget-mib", type=float, default=48.0)
    parser.add_argument("--largest", type=int, default=15)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    files, root_bytes, largest = tree_stats(args.rootfs)
    init_bytes = args.initramfs.stat().st_size if args.initramfs.exists() else 0

    print(f"rootfs:    {root_bytes} bytes ({mib(root_bytes):.2f} MiB), {files} files")
    print(f"initramfs: {init_bytes} bytes ({mib(init_bytes):.2f} MiB)")
    print(f"bootstrap budgets: rootfs <= {args.rootfs_budget_mib:.1f} MiB; initramfs <= {args.initramfs_budget_mib:.1f} MiB")
    print("largest rootfs files:")
    for size, path in largest[: max(0, args.largest)]:
        try:
            relative = path.relative_to(args.rootfs)
        except ValueError:
            relative = path
        print(f"  {mib(size):8.2f} MiB  {relative}")

    failures: list[str] = []
    if root_bytes > args.rootfs_budget_mib * 1024 * 1024:
        failures.append("rootfs budget exceeded")
    if init_bytes > args.initramfs_budget_mib * 1024 * 1024:
        failures.append("initramfs budget exceeded")
    if args.strict and not args.rootfs.exists():
        failures.append("rootfs missing")
    if args.strict and not args.initramfs.exists():
        failures.append("initramfs missing")

    if failures:
        print("SIZE CHECK: FAIL: " + "; ".join(failures))
        return 1
    print("SIZE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
