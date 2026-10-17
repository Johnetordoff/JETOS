"""JETOS first-stage userspace and PID-1 handoff to the JETOS language."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
import subprocess
import sys

from jetos.network import configure_loopback

GREEN_GATE_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"

libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_char_p]
libc.mount.restype = ctypes.c_int


def _mount(source: str, target: str, filesystem: str, options: str | None = None, mode: int = 0o755) -> None:
    Path(target).mkdir(mode=mode, parents=True, exist_ok=True)
    data = options.encode() if options else None
    result = libc.mount(source.encode(), target.encode(), filesystem.encode(), 0, data)
    if result == 0:
        return
    error = ctypes.get_errno()
    if os.getpid() == 1:
        raise OSError(error, f"mount {filesystem} on {target} failed")
    print(f"JETOS dry-run: mount {filesystem} on {target} skipped: {os.strerror(error)}", file=sys.stderr)


# The normal Linux early-userspace contract that CPython-derived JetLang and
# its standard library assume. Order matters: devpts and /dev/shm live inside
# the devtmpfs mounted on /dev.
KERNEL_FILESYSTEMS = (
    ("devtmpfs", "/dev", "devtmpfs", None, 0o755),
    ("proc", "/proc", "proc", None, 0o555),
    ("sysfs", "/sys", "sysfs", None, 0o555),
    # Unix98 PTYs: os.openpty, pty, tty, termios, subprocess pty users.
    ("devpts", "/dev/pts", "devpts", "gid=5,mode=620,ptmxmode=666", 0o755),
    # POSIX shared memory/semaphores: multiprocessing locks, shared_memory.
    ("tmpfs", "/dev/shm", "tmpfs", "mode=1777", 0o1777),
)


def mount_kernel_filesystems() -> None:
    for source, target, filesystem, options, mode in KERNEL_FILESYSTEMS:
        _mount(source, target, filesystem, options, mode)
    if os.getpid() == 1:
        # World-writable sticky /tmp, as tempfile and many POSIX callers expect.
        os.chmod("/tmp", 0o1777)


def bring_up_loopback() -> None:
    """Configure lo before any qualification so 127.0.0.1 is reachable."""
    try:
        configure_loopback()
    except (OSError, AssertionError) as exc:
        if os.getpid() == 1:
            raise
        print(f"JETOS dry-run: loopback configuration skipped: {exc}", file=sys.stderr)
        return
    print("network: loopback lo 127.0.0.1/8 UP", flush=True)


def run_armed_stdlib_qualification() -> bool:
    """Run the armed stdlib/CPython qualification before exposing the shell."""
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
    marker = Path("/jetos/guest-qualify")
    if not marker.is_file():
        return False
    mode = marker.read_text(encoding="utf-8").strip()
    if mode != "run":
        raise SystemExit(f"invalid guest qualification mode: {mode!r}")
    print("JETOS guest qualification: runtime/network", flush=True)
    result = subprocess.run([sys.executable, "/jetos/tools/guest_qualify.py"], check=False)
    state = "PASS" if result.returncode == 0 else "FAIL"
    print(f"JETOS_GUEST_QUALIFICATION={state}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return True


def main() -> None:
    mount_kernel_filesystems()
    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")
    print("JETOS 0.1 — John E Tordoff's Operating System", flush=True)
    print(f"pid: {os.getpid()}", flush=True)
    print(f"kernel: {platform.release()}", flush=True)
    print(f"architecture: {platform.machine()}", flush=True)
    print(f"language implementation: {sys.implementation.name}", flush=True)
    print(f"language runtime: {platform.python_version()}", flush=True)
    print("Dunicode: 0.2", flush=True)
    print("Unicode: supported", flush=True)
    print("encoding: UTF-8", flush=True)
    print("network: OFF (VM has no virtual NIC; loopback only)", flush=True)
    bring_up_loopback()
    stdlib_qualified = run_armed_stdlib_qualification()
    guest_qualified = run_armed_guest_qualification()
    if stdlib_qualified and guest_qualified:
        # This is the machine-readable Green Gate handoff point. It is emitted
        # only after the armed full stdlib/CPython and guest/runtime gates pass.
        print(GREEN_GATE_MARKER, flush=True)
    print("shell: JETOS language interpreter", flush=True)
    print("", flush=True)
    os.execv(sys.executable, [sys.executable, "-S", "-i"])


if __name__ == "__main__":
    main()
