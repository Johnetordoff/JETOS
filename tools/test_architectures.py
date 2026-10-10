#!/usr/bin/env python3
"""Fast architecture-contract tests for JetOS."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_build",
    ROOT / "tools/build.py",
)
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0

    aliases = {
        "x86_64": "x86_64",
        "AMD64": "x86_64",
        "aarch64": "arm64",
        "ARM64": "arm64",
    }
    for raw, expected in aliases.items():
        check(build.normalize_arch(raw) == expected, f"normalize {raw}")
        checks += 1

    try:
        build.normalize_arch("armv7l")
    except SystemExit:
        checks += 1
    else:
        raise AssertionError("unsupported architecture must fail closed")

    x86 = build.kernel_requirements("x86_64")
    arm = build.kernel_requirements("arm64")
    check(x86["CONFIG_64BIT"] == arm["CONFIG_64BIT"] == "y", "shared 64-bit baseline")
    check(x86["CONFIG_X86_64"] == "y", "x86 kernel identity")
    check(arm["CONFIG_ARM64"] == "y", "arm64 kernel identity")
    check("CONFIG_ARM64" not in x86, "arm64 setting isolated from x86")
    check("CONFIG_X86_64" not in arm, "x86 setting isolated from arm64")
    checks += 5

    source = Path("/kernel")
    check(
        build.kernel_image(source, "x86_64") == source / "arch/x86/boot/bzImage",
        "x86 kernel image path",
    )
    check(
        build.kernel_image(source, "arm64") == source / "arch/arm64/boot/Image",
        "arm64 kernel image path",
    )
    checks += 2

    original_which = build.shutil.which
    original_execvp = build.os.execvp
    original_exists = build.Path.exists
    captured: list[list[str]] = []

    try:
        build.shutil.which = lambda name: f"/usr/bin/{name}"
        build.Path.exists = lambda self: False if str(self) == "/dev/kvm" else original_exists(self)
        build.os.execvp = lambda executable, argv: captured.append(argv)

        build.qemu_boot(Path("kernel"), Path("initrd"), "128M", "x86_64")
        check(captured[-1][0].endswith("qemu-system-x86_64"), "x86 QEMU executable")
        check("console=ttyS0 rdinit=/init panic=-1" in captured[-1], "x86 serial console")

        build.qemu_boot(Path("kernel"), Path("initrd"), "128M", "arm64")
        check(captured[-1][0].endswith("qemu-system-aarch64"), "arm64 QEMU executable")
        check("console=ttyAMA0 rdinit=/init panic=-1" in captured[-1], "arm64 serial console")
        check("virt" in captured[-1], "arm64 QEMU virt machine")
        checks += 5
    finally:
        build.shutil.which = original_which
        build.os.execvp = original_execvp
        build.Path.exists = original_exists

    print(f"JETOS architecture contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
