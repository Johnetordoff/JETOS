#!/usr/bin/env python3
"""Qualify the JETOS userspace as an operating-system environment in Docker.

Docker isolates the JETOS userspace but shares the host Linux kernel.  This
script therefore tests the userspace/kernel contract honestly: JETOS owns the
container userspace under test, while Linux remains the imported kernel
substrate for Gen 2.
"""
from __future__ import annotations

import argparse
import json
import mmap
import os
from pathlib import Path
import platform
import selectors
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
from multiprocessing import shared_memory

EXPECTED_PYTHON = (3, 14, 8)

TOOL_CAPABILITIES = {
    "c_compiler": os.environ.get("CC", "cc"),
    "linker": "ld",
    "build_orchestrator": "make",
    "expression_calculator": "bc",
    "parser_generator": "bison",
    "lexer_generator": "flex",
    "kernel_debug_info_tool": "pahole",
    "package_config_query": "pkg-config",
    "x86_system_emulator": "qemu-system-x86_64",
    "arm_system_emulator": "qemu-system-arm",
    "system_call_tracer": "strace",
}


def command_identity(command: str) -> dict[str, str]:
    # CC may be a command line such as "ccache cc"; every executable in it must
    # exist, and the identity reported is that of the final (real) compiler.
    executables = [
        token for token in shlex.split(command)
        if not token.startswith("-") and "=" not in token
    ]
    if not executables:
        raise AssertionError(f"required capability executable not found: {command}")
    for executable in executables:
        path = shutil.which(executable)
        if path is None:
            raise AssertionError(f"required capability executable not found: {executable}")
    result = subprocess.run(
        [path, "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    first_line = (result.stdout or result.stderr).splitlines()
    return {
        "command": command,
        "path": path,
        "identity": first_line[0] if first_line else "version unavailable",
    }


def qualify_os_behavior(phase: str) -> dict[str, object]:
    if os.environ.get("JETOS_CONTAINER") != "1":
        raise AssertionError("JETOS_CONTAINER=1 is required for Docker qualification")
    if sys.version_info[:3] != EXPECTED_PYTHON:
        raise AssertionError(
            f"expected Python {EXPECTED_PYTHON}, got {sys.version_info[:3]}"
        )
    if platform.system() != "Linux":
        raise AssertionError(f"Docker JETOS Gen 2 requires Linux, got {platform.system()}")

    required_paths = (
        Path("/proc/self/status"),
        Path("/sys"),
        Path("/dev/null"),
        Path("/tmp"),
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise AssertionError("missing OS surfaces: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="jetos-os-") as directory:
        root = Path(directory)
        path = root / "file.bin"
        path.write_bytes(b"JETOS" + b"\0" * 4091)
        with path.open("r+b") as stream:
            with mmap.mmap(stream.fileno(), 0) as mapping:
                mapping[0:5] = b"jetos"
        if path.read_bytes()[:5] != b"jetos":
            raise AssertionError("filesystem/mmap round trip failed")

        link = root / "file-link"
        link.symlink_to(path.name)
        if link.resolve() != path:
            raise AssertionError("symlink resolution failed")

    left, right = socket.socketpair()
    try:
        left.sendall(b"j")
        selector = selectors.DefaultSelector()
        try:
            selector.register(right, selectors.EVENT_READ)
            if not selector.select(timeout=1.0):
                raise AssertionError("selector/socket readiness failed")
            if right.recv(1) != b"j":
                raise AssertionError("socketpair data round trip failed")
        finally:
            selector.close()
    finally:
        left.close()
        right.close()

    child = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        text=True,
        capture_output=True,
        check=True,
    )
    if not child.stdout.strip().isdigit():
        raise AssertionError("subprocess creation failed")

    region = shared_memory.SharedMemory(create=True, size=32)
    try:
        region.buf[:5] = b"JETOS"
        if bytes(region.buf[:5]) != b"JETOS":
            raise AssertionError("shared memory round trip failed")
    finally:
        region.close()
        region.unlink()

    if phase == "runtime" and os.getpid() != 1:
        raise AssertionError(
            f"runtime qualifier must be the container's PID 1; got PID {os.getpid()}"
        )

    return {
        "phase": phase,
        "userspace": "JETOS",
        "kernel_model": "shared host Linux kernel",
        "python": platform.python_version(),
        "machine": platform.machine(),
        "pid": os.getpid(),
        "filesystem": "pass",
        "mmap": "pass",
        "selectors": "pass",
        "unix_socketpair": "pass",
        "subprocess": "pass",
        "shared_memory": "pass",
    }


def qualify_toolchain() -> dict[str, dict[str, str]]:
    return {
        capability: command_identity(command)
        for capability, command in TOOL_CAPABILITIES.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("build", "runtime"), required=True)
    parser.add_argument("--require-toolchain", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {"os": qualify_os_behavior(args.phase)}
    if args.require_toolchain:
        report["capabilities"] = qualify_toolchain()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        os_report = report["os"]
        assert isinstance(os_report, dict)
        print(
            "JETOS Docker OS qualification: PASS "
            f"phase={args.phase} python={os_report['python']} "
            f"machine={os_report['machine']} kernel={os_report['kernel_model']}"
        )
        capabilities = report.get("capabilities")
        if isinstance(capabilities, dict):
            for name, detail in capabilities.items():
                assert isinstance(detail, dict)
                print(f"  {name}: {detail['identity']} ({detail['path']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
