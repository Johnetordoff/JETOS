"""JETOS first-stage userspace and PID-1 handoff to the JETOS language."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
import subprocess
import sys


libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
]
libc.mount.restype = ctypes.c_int


def _mount(
    source: str,
    target: str,
    filesystem: str,
) -> None:
    Path(target).mkdir(
        parents=True,
        exist_ok=True,
    )
    result = libc.mount(
        source.encode(),
        target.encode(),
        filesystem.encode(),
        0,
        None,
    )
    if result == 0:
        return

    error = ctypes.get_errno()
    if os.getpid() == 1:
        raise OSError(
            error,
            f"mount {filesystem} "
            f"on {target} failed",
        )

    print(
        "JETOS dry-run: "
        f"mount {filesystem} "
        f"on {target} skipped: "
        f"{os.strerror(error)}",
        file=sys.stderr,
    )


def mount_kernel_filesystems() -> None:
    _mount(
        "devtmpfs",
        "/dev",
        "devtmpfs",
    )
    _mount(
        "proc",
        "/proc",
        "proc",
    )
    _mount(
        "sysfs",
        "/sys",
        "sysfs",
    )


def run_armed_stdlib_qualification() -> bool:
    """Run the stdlib gate only in an explicitly armed qualification image."""
    marker = Path("/jetos/stdlib-qualify")
    if not marker.is_file():
        return False

    mode = marker.read_text(encoding="utf-8").strip()
    if mode not in {"fast", "full"}:
        raise SystemExit(f"invalid stdlib qualification mode: {mode!r}")

    command = [
        sys.executable,
        "/jetos/tools/stdlib_qualify.py",
        "--strict",
        "--manifest",
        "/tmp/stdlib-surface.json",
    ]
    if mode == "full":
        command.append("--full")

    print(f"JETOS stdlib qualification: {mode}", flush=True)
    result = subprocess.run(command, check=False)
    state = "PASS" if result.returncode == 0 else "FAIL"
    print(f"JETOS_STDLIB_QUALIFICATION={state}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return True


def run_armed_guest_qualification() -> bool:
    """Run same-runtime guest networking/web qualification when armed."""
    marker = Path("/jetos/guest-qualify")
    if not marker.is_file():
        return False
    mode = marker.read_text(encoding="utf-8").strip()
    if mode != "run":
        raise SystemExit(f"invalid guest qualification mode: {mode!r}")

    print("JETOS guest qualification: runtime/network", flush=True)
    result = subprocess.run(
        [sys.executable, "/jetos/tools/guest_qualify.py"],
        check=False,
    )
    state = "PASS" if result.returncode == 0 else "FAIL"
    print(f"JETOS_GUEST_QUALIFICATION={state}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return True


def main() -> None:
    mount_kernel_filesystems()

    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = (
        "/jetos/startup.py"
    )
    os.environ.setdefault(
        "LANG",
        "C.UTF-8",
    )
    os.environ.setdefault(
        "LC_ALL",
        "C.UTF-8",
    )

    print(
        "JETOS 0.1 — "
        "John E Tordoff's Operating System",
        flush=True,
    )
    print(
        f"pid: {os.getpid()}",
        flush=True,
    )
    print(
        f"kernel: {platform.release()}",
        flush=True,
    )
    print(
        f"architecture: {platform.machine()}",
        flush=True,
    )
    print(
        "language implementation: "
        f"{sys.implementation.name}",
        flush=True,
    )
    print(
        "language runtime: "
        f"{platform.python_version()}",
        flush=True,
    )
    print(
        "Dunicode: 0.2",
        flush=True,
    )
    print(
        "Unicode: supported",
        flush=True,
    )
    print(
        "encoding: UTF-8",
        flush=True,
    )
    print(
        "network: OFF "
        "(VM has no virtual NIC; loopback may be qualified locally)",
        flush=True,
    )

    run_armed_stdlib_qualification()
    run_armed_guest_qualification()

    print(
        "shell: JETOS language interpreter",
        flush=True,
    )
    print("", flush=True)

    os.execv(
        sys.executable,
        [
            sys.executable,
            "-S",
            "-i",
        ],
    )


if __name__ == "__main__":
    main()
