#!/usr/bin/env python3
"""Static contract checks for the canonical Apple-Silicon development path."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"M1 contract failure in {path}: missing {missing!r}")


def main() -> int:
    require(
        "jetos.py",
        'return "linux/arm64"',
        'build_command.extend(["--platform", docker_platform])',
        'run_command.extend(["--platform", docker_platform])',
        '"python3", "tools/dev.py", "build" if build_only else "run"',
    )
    require(
        "Dockerfile",
        "qemu-system-arm",
        "command -v qemu-system-aarch64",
    )
    require(
        "tools/dev.py",
        'return "arm64"',
        '"arch/arm64/boot/Image"',
        'tools/stdlib_qualify.py',
        '"--profile", "fat"',
        '"--stdlib-qualify", "full"',
        'tools/build.py", "vm"',
    )
    require(
        "tools/build.py",
        '"arm64"',
        'qemu-system-aarch64',
        '"ttyAMA0"',
        '"virt"',
        '"-cpu"',
        '"max"',
    )
    require(
        "src/jetos/startup.py",
        '"jetos> "',
        'def qualify(',
    )
    require(
        "tools/guest_qualify.py",
        'sys.implementation.name != "jetos"',
        'tempfile.TemporaryDirectory',
        'subprocess.run',
        'JETOS_ENV_PROBE',
        'configure_loopback()',
        'ThreadingHTTPServer',
        'urllib.request.urlopen',
    )
    require(
        "src/jetos/network.py",
        'fcntl.ioctl',
    )
    require(
        "tools/stdlib_qualify.py",
        '"-m","test"',
    )
    print("M1 canonical-path contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
