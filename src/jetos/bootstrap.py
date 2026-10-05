"""Tiny JETOS bootstrap boundary for mounting kernel filesystems and live state."""
from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import sys
import time

libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
]
libc.mount.restype = ctypes.c_int


def _mount(source: str, target: str, filesystem: str) -> bool:
    Path(target).mkdir(parents=True, exist_ok=True)
    result = libc.mount(
        source.encode(),
        target.encode(),
        filesystem.encode(),
        0,
        None,
    )
    if result == 0:
        return True
    error = ctypes.get_errno()
    if error == errno.EBUSY:
        return True
    return False


def mount_kernel_filesystems() -> None:
    _mount("devtmpfs", "/dev", "devtmpfs")
    _mount("proc", "/proc", "proc")
    _mount("sysfs", "/sys", "sysfs")


def _cmdline_value(name: str) -> str | None:
    try:
        fields = Path("/proc/cmdline").read_text(encoding="utf-8").split()
    except OSError:
        return None
    prefix = name + "="
    for field in fields:
        if field.startswith(prefix):
            return field[len(prefix):]
    return None


def state_candidates() -> tuple[str, ...]:
    explicit = _cmdline_value("jetos.state")
    defaults = (
        "/dev/mmcblk0p2",
        "/dev/mmcblk1p2",
        "/dev/nvme0n1p2",
        "/dev/sda2",
    )
    if explicit:
        return (explicit, *tuple(value for value in defaults if value != explicit))
    return defaults


def mount_state(timeout_seconds: float = 5.0) -> Path | None:
    target = Path("/state")
    target.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    while True:
        for device in state_candidates():
            if Path(device).exists() and _mount(device, str(target), "ext4"):
                return target
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def main() -> None:
    mount_kernel_filesystems()
    state = mount_state()
    repo = (state / "jetos") if state is not None else None
    if repo is not None and (repo / "src").is_dir():
        sys.path.insert(0, str(repo / "src"))
        os.environ["JETOS_REPO"] = str(repo)
        os.environ["JETOS_STATE"] = str(state)
    else:
        sys.path.insert(0, "/jetos/src")
        os.environ.setdefault("JETOS_REPO", "/jetos")
    from jetos.init import main as jetos_main
    jetos_main()


if __name__ == "__main__":
    main()
