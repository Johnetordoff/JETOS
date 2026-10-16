#!/usr/bin/env python3
"""Report JetOS ODROID HC1 build readiness without claiming a hardware boot.

The HC1 is a 32-bit ARM target.  This probe deliberately separates host,
cross-build, emulator, and repository architecture support so an x86_64
workstation can make useful progress without pretending that it booted the
physical board.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = "armv7l"
REQUIRED_TOOLS = {
    "cross_c_compiler": "arm-linux-gnueabihf-gcc",
    "cross_binutils": "arm-linux-gnueabihf-ld",
    "system_emulator": "qemu-system-arm",
}


def repository_armv7_support() -> tuple[bool, str]:
    """Inspect the canonical architecture normalizer instead of guessing."""
    build = (ROOT / "tools/build.py").read_text(encoding="utf-8")
    aliases = ("armv7l", "armv7", "armhf")
    supported = any(f'"{alias}"' in build for alias in aliases)
    return supported, (
        "tools/build.py names a 32-bit ARM alias"
        if supported
        else "tools/build.py does not yet name armv7/armhf; canonical build is not ODROID-HC1-ready"
    )


def collect() -> dict[str, object]:
    tools = {role: shutil.which(executable) for role, executable in REQUIRED_TOOLS.items()}
    repo_supported, repo_detail = repository_armv7_support()
    return {
        "target": TARGET,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "repository": {
            "armv7_supported": repo_supported,
            "detail": repo_detail,
        },
        "tools": tools,
        "cross_build_ready": repo_supported and all(tools.values()),
        "physical_boot_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="fail unless repository ARMv7 support and the cross-build toolchain are present",
    )
    args = parser.parse_args(argv)
    report = collect()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("JetOS ODROID HC1 readiness")
        print(f"  target: {report['target']}")
        host = report["host"]
        assert isinstance(host, dict)
        print(f"  host: {host['system']} {host['machine']}")
        repository = report["repository"]
        assert isinstance(repository, dict)
        print(f"  repository ARMv7 support: {'PASS' if repository['armv7_supported'] else 'BLOCKED'}")
        print(f"    {repository['detail']}")
        tools = report["tools"]
        assert isinstance(tools, dict)
        for role, executable in REQUIRED_TOOLS.items():
            print(f"  {role}: {tools[role] or 'MISSING'} ({executable})")
        print(f"  cross-build readiness: {'PASS' if report['cross_build_ready'] else 'BLOCKED'}")
        print("  physical ODROID boot: NOT VERIFIED by this probe")
    return 0 if (not args.require_ready or report["cross_build_ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
