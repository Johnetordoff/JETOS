#!/usr/bin/env python3
"""Contract tests for the ODROID HC1 readiness probe."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("odroid_qualify", ROOT / "tools/odroid_qualify.py")
assert SPEC and SPEC.loader
odroid = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(odroid)


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0
    check(odroid.TARGET == "armv7l", "HC1 target remains explicit 32-bit ARM")
    checks += 1
    check(odroid.REQUIRED_TOOLS["cross_c_compiler"] == "arm-linux-gnueabihf-gcc", "hard-float ARM cross compiler")
    checks += 1
    check(odroid.REQUIRED_TOOLS["system_emulator"] == "qemu-system-arm", "ARM system emulator")
    checks += 1

    original_which = odroid.shutil.which
    original_probe = odroid.repository_armv7_support
    try:
        odroid.shutil.which = lambda executable: f"/usr/bin/{executable}"
        odroid.repository_armv7_support = lambda: (True, "test")
        report = odroid.collect()
        check(report["cross_build_ready"] is True, "all prerequisites produce ready state")
        checks += 1

        odroid.shutil.which = lambda executable: None if executable == "qemu-system-arm" else f"/usr/bin/{executable}"
        report = odroid.collect()
        check(report["cross_build_ready"] is False, "missing emulator blocks readiness")
        checks += 1
        check(report["physical_boot_verified"] is False, "probe never fabricates physical boot evidence")
        checks += 1
    finally:
        odroid.shutil.which = original_which
        odroid.repository_armv7_support = original_probe

    print(f"ODROID HC1 qualification contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
