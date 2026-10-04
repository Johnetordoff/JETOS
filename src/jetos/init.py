"""JETOS first-stage userspace and PID-1 handoff to the JETOS language."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
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
        "(VM has no virtual NIC)",
        flush=True,
    )
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
