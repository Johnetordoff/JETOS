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
    Path(target).mkdir(parents=True, exist_ok=True)
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
        raise OSError(error, f"mount {filesystem} on {target} failed")

    print(
        "JETOS dry-run: "
        f"mount {filesystem} on {target} skipped: {os.strerror(error)}",
        file=sys.stderr,
    )


def mount_kernel_filesystems() -> None:
    _mount("devtmpfs", "/dev", "devtmpfs")
    _mount("proc", "/proc", "proc")
    _mount("sysfs", "/sys", "sysfs")


def _qualification_command(tool: str, manifest: str, mode: str) -> list[str]:
    command = [
        sys.executable,
        tool,
        "--strict",
        "--manifest",
        manifest,
    ]
    if mode == "full":
        command.append("--full")
    return command


def run_armed_qualification() -> bool:
    """Run language and OS gates only in an explicitly armed test image."""
    marker = Path("/jetos/stdlib-qualify")
    if not marker.is_file():
        return False

    mode = marker.read_text(encoding="utf-8").strip()
    if mode not in {"fast", "full"}:
        raise SystemExit(f"invalid qualification mode: {mode!r}")

    suites = (
        (
            "STDLIB",
            "/jetos/tools/stdlib_qualify.py",
            "/tmp/stdlib-surface.json",
        ),
        (
            "OS",
            "/jetos/tools/os_qualify.py",
            "/tmp/python-os-surface.json",
        ),
    )
    failed = False
    for label, tool, manifest in suites:
        print(f"JETOS {label.lower()} qualification: {mode}", flush=True)
        result = subprocess.run(
            _qualification_command(tool, manifest, mode),
            check=False,
        )
        state = "PASS" if result.returncode == 0 else "FAIL"
        print(f"JETOS_{label}_QUALIFICATION={state}", flush=True)
        failed = failed or result.returncode != 0

    overall = "FAIL" if failed else "PASS"
    print(f"JETOS_BASELINE_QUALIFICATION={overall}", flush=True)
    if failed:
        raise SystemExit(1)
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
    print("network: OFF (VM has no virtual NIC)", flush=True)

    if run_armed_qualification():
        # A qualification image is a one-shot test appliance. Exiting PID 1
        # intentionally terminates that VM after the result markers are emitted.
        raise SystemExit(0)

    print("shell: JETOS language interpreter", flush=True)
    print("", flush=True)
    os.execv(sys.executable, [sys.executable, "-S", "-i"])


if __name__ == "__main__":
    main()
