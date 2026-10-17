#!/usr/bin/env python3
"""Fast contracts for the ODROID HC1 JetOS qualification path."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_odroid_dev",
    ROOT / "tools/odroid_dev.py",
)
assert SPEC and SPEC.loader
odroid = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(odroid)


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0

    for alias in ("armv7l", "armv7", "armhf"):
        check(odroid.normalized_machine(alias) == "armv7", f"normalize {alias}")
        checks += 1
    check(odroid.normalized_machine("x86_64") == "x86_64", "preserve non-ARMv7 host")
    checks += 1

    check(
        odroid.kernel_make_prefix(machine="armv7l") == ["make", "ARCH=arm"],
        "native HC1 kernel build must use Linux ARCH=arm without a cross prefix",
    )
    checks += 1

    original_which = odroid.shutil.which
    original_exists = odroid.Path.exists
    try:
        odroid.shutil.which = lambda name: f"/usr/bin/{name}"
        cross = odroid.kernel_make_prefix(machine="x86_64")
        check(cross[:2] == ["make", "ARCH=arm"], "cross build keeps Linux ARCH=arm")
        check(
            "CROSS_COMPILE=arm-linux-gnueabihf-" in cross,
            "cross build selects hard-float ARM toolchain",
        )
        checks += 2

        odroid.Path.exists = (
            lambda self: False if str(self) == "/dev/kvm" else original_exists(self)
        )
        command = odroid.qemu_command(Path("zImage"), Path("initramfs.cpio.gz"), "1024M")
        check(command[0].endswith("qemu-system-arm"), "ODROID VM uses 32-bit ARM QEMU")
        check(command[command.index("-machine") + 1] == "virt", "ODROID VM uses ARM virt machine")
        check(command[command.index("-cpu") + 1] == "cortex-a15", "ODROID VM uses ARMv7 CPU")
        check(command[command.index("-accel") + 1] == "tcg", "portable fallback is TCG")
        check(
            command[command.index("-append") + 1]
            == "console=ttyAMA0 rdinit=/init panic=-1",
            "ODROID VM serial/PID1 boot contract",
        )
        checks += 5
    finally:
        odroid.shutil.which = original_which
        odroid.Path.exists = original_exists

    with tempfile.TemporaryDirectory() as temporary:
        config = Path(temporary) / ".config"
        config.write_text(
            "CONFIG_ARM=y\n"
            "# CONFIG_AEABI is not set\n"
            "CONFIG_64BIT=y\n",
            encoding="utf-8",
        )
        odroid.patch_kernel_config(config)
        values = odroid.build.read_kernel_config(config)
        for key, expected in odroid.ARMV7_KERNEL_CONFIG.items():
            check(values.get(key) == expected, f"ARMv7 kernel config {key}")
            checks += 1
        check(values.get("CONFIG_64BIT") == "y", "unowned kernel settings are preserved")
        checks += 1

    check(
        "CONFIG_64BIT" not in odroid.ARMV7_KERNEL_CONFIG,
        "ARMv7 qualification never requires a 64-bit kernel",
    )
    checks += 1

    print(f"JETOS ODROID HC1 contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
