"""JETOS first-stage userspace and PID-1 session launcher."""
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


def _print_boot_record() -> None:
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


def _run_console() -> None:
    print(
        "session: JETOS Language console",
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


def _display_available() -> bool:
    if sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        return True
    return bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
    )


def _run_desktop() -> bool:
    """Run the standard-library GUI desktop if the display boundary exists."""
    if not _display_available():
        print(
            "desktop: unavailable "
            "(no guest display server/backend yet)",
            flush=True,
        )
        return False

    try:
        from jetos import desktop
    except Exception as error:
        print(
            f"desktop: unavailable ({error})",
            flush=True,
        )
        return False

    print(
        "session: JETOS Tkinter desktop",
        flush=True,
    )
    print("", flush=True)

    try:
        desktop.run(fullscreen=True)
    except Exception as error:
        print(
            f"desktop exited with error: {error}",
            file=sys.stderr,
            flush=True,
        )
        return False

    # Closing the desktop drops into the diagnostic language console rather
    # than killing PID 1.
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

    _print_boot_record()

    target = os.environ.get(
        "JETOS_BOOT_TARGET",
        "desktop",
    ).lower()

    if target == "desktop":
        _run_desktop()

    _run_console()


if __name__ == "__main__":
    main()
