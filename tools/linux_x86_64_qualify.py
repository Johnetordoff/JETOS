#!/usr/bin/env python3
"""Build and qualify current-revision JetLang inside x86_64 JetOS.

Unlike a readiness probe, success requires the real JetOS guest console to emit
both stdlib and guest qualification PASS markers.  The build itself remains
owned by tools/dev.py; this module adds deterministic QEMU result capture for a
generic x86_64 Linux host without changing the M1/Docker entrypoint.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import platform
import selectors
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
CONSOLE_LOG = BUILD / "x86_64-guest-qualification.log"
STDLIB_PASS = "JETOS_STDLIB_QUALIFICATION=PASS"
STDLIB_FAIL = "JETOS_STDLIB_QUALIFICATION=FAIL"
GUEST_PASS = "JETOS_GUEST_QUALIFICATION=PASS"
GUEST_FAIL = "JETOS_GUEST_QUALIFICATION=FAIL"
FINAL_PASS = "JETOS_X86_64_JETLANG_STDLIB_ON_JETOS=PASS"


def load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"jetos_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load JetOS tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dev = load_tool("dev")
build = load_tool("build")


def require_host() -> None:
    if platform.system() != "Linux":
        raise SystemExit(f"x86_64 qualification requires Linux, got {platform.system()}")
    if dev.arch() != "x86_64":
        raise SystemExit(
            "x86_64 qualification requires an x86_64 Linux host; "
            f"got {platform.machine()}"
        )


def qemu_command(kernel: Path, initramfs: Path, memory: str) -> list[str]:
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise SystemExit("qemu-system-x86_64 is not installed")
    if memory == "auto":
        memory = build.initramfs_vm_memory(initramfs)
    accel = "kvm" if Path("/dev/kvm").exists() else "tcg"
    return [
        qemu,
        "-accel", accel,
        "-m", memory,
        "-kernel", str(kernel),
        "-initrd", str(initramfs),
        "-append", "console=ttyS0 rdinit=/init panic=-1",
        "-nic", "none",
        "-nographic",
        "-no-reboot",
    ]


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def qualify_guest(
    kernel: Path,
    initramfs: Path,
    *,
    memory: str = "auto",
    timeout: int = 4 * 60 * 60,
    log: Path = CONSOLE_LOG,
) -> None:
    command = qemu_command(kernel, initramfs, memory)
    log.parent.mkdir(parents=True, exist_ok=True)
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
    deadline = time.monotonic() + timeout
    stdlib_passed = False
    guest_passed = False
    try:
        with log.open("w", encoding="utf-8") as stream:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise SystemExit(
                        "x86_64 JetOS exited before qualification completed "
                        f"(status {process.returncode}); console: {log}"
                    )
                events = selector.select(timeout=1.0)
                if not events:
                    continue
                line = process.stdout.readline()
                if not line:
                    continue
                print(line, end="", flush=True)
                stream.write(line)
                stream.flush()
                if STDLIB_FAIL in line:
                    raise SystemExit(
                        f"JetLang stdlib qualification failed inside JetOS; console: {log}"
                    )
                if GUEST_FAIL in line:
                    raise SystemExit(
                        f"JetOS guest qualification failed; console: {log}"
                    )
                stdlib_passed |= STDLIB_PASS in line
                guest_passed |= GUEST_PASS in line
                if stdlib_passed and guest_passed:
                    print(FINAL_PASS, flush=True)
                    return
        raise SystemExit(
            "timed out before x86_64 JetOS completed stdlib + guest qualification; "
            f"console: {log}"
        )
    finally:
        selector.close()
        stop_process(process)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", default="auto")
    parser.add_argument("--timeout", type=int, default=4 * 60 * 60)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    require_host()
    runtime, kernel, initramfs = dev.build_all()
    print(f"x86_64 JetLang runtime: {runtime}")
    print(f"x86_64 JetOS kernel: {kernel}")
    print(f"x86_64 JetOS initramfs: {initramfs}")
    if not args.build_only:
        qualify_guest(
            kernel,
            initramfs,
            memory=args.memory,
            timeout=args.timeout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
