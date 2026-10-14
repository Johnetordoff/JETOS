#!/usr/bin/env python3
"""Build and boot a Fat JETOS image that qualifies stdlib inside the guest OS."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
DEV_TOOL = ROOT / "tools/dev.py"

SPEC = importlib.util.spec_from_file_location("jetos_dev", DEV_TOOL)
if SPEC is None or SPEC.loader is None:
    raise SystemExit(f"cannot load JETOS dev tool: {DEV_TOOL}")
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)

QUALIFY_ROOTFS = dev.BUILD / "stdlib-qualify-rootfs"
QUALIFY_INITRAMFS = dev.BUILD / "jetos-stdlib-qualify.cpio.gz"


def build(mode: str) -> tuple[Path, Path]:
    if platform.system() != "Linux":
        raise SystemExit(
            "guest stdlib qualification requires the Linux JETOS build environment; "
            "use the normal Docker development path on macOS/Windows"
        )

    dev.tests()
    dev.prepare_sources()
    runtime, stdlib = dev.build_language()
    dev.qualify_stdlib(runtime)
    target_arch = dev.arch()
    kernel = dev.build_kernel(target_arch)
    dev.run([
        sys.executable,
        "tools/package.py",
        "--profile",
        "fat",
        "--rootfs",
        str(QUALIFY_ROOTFS),
        "--output",
        str(QUALIFY_INITRAMFS),
        "--python",
        str(runtime),
        "--stdlib",
        str(stdlib),
        "--linux-source",
        str(dev.SOURCE_LINUX),
        "--stdlib-qualify",
        mode,
    ])
    return kernel, QUALIFY_INITRAMFS


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Boot Fat JETOS and qualify its Python stdlib against the JETOS OS"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="run CPython's installed regression suite after the fast guest checks",
    )
    args = parser.parse_args()
    mode = "full" if args.full else "fast"
    kernel, initramfs = build(mode)
    print(f"booting guest stdlib qualification: {mode}", flush=True)
    dev.boot(kernel, initramfs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
