#!/usr/bin/env python3
"""Boot a freshly built JetOS guest and stop when the guest qualifier passes."""
from __future__ import annotations

from pathlib import Path
import selectors
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
KERNEL = BUILD / "linux" / "arch" / "x86" / "boot" / "bzImage"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"
PASS_MARKER = "JETOS_GUEST_QUALIFICATION=PASS"
TIMEOUT_SECONDS = 300


def main() -> int:
    if not KERNEL.is_file():
        raise SystemExit(f"missing freshly built x86_64 kernel: {KERNEL}")
    if not INITRAMFS.is_file():
        raise SystemExit(f"missing freshly built Fat initramfs: {INITRAMFS}")

    command = [
        sys.executable,
        str(ROOT / "tools" / "build.py"),
        "vm",
        "--arch",
        "x86_64",
        "--kernel",
        str(KERNEL),
        "--initramfs",
        str(INITRAMFS),
    ]
    print("+", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + TIMEOUT_SECONDS
    passed = False
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            for key, _ in selector.select(timeout=1.0):
                line = key.fileobj.readline()
                if not line:
                    continue
                print(line, end="", flush=True)
                if PASS_MARKER in line:
                    passed = True
                    break
            if passed:
                break
    finally:
        selector.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

    if not passed:
        raise SystemExit(
            f"JetOS boot smoke did not observe {PASS_MARKER!r} within "
            f"{TIMEOUT_SECONDS}s; qemu returncode={process.returncode}"
        )
    print("JETOS_BOOT_SMOKE=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
