"""JETOS first-stage userspace and main-interpreter OS supervisor."""
from __future__ import annotations

import code
import ctypes
import os
from pathlib import Path
import platform
import sys

from jetos import hardware
from jetos.interpreters import InterpreterSupervisor, plan_services, supported


libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
]
libc.mount.restype = ctypes.c_int


def _mount(source: str, target: str, filesystem: str) -> None:
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
        f"JETOS dry-run: mount {filesystem} on {target} skipped: "
        f"{os.strerror(error)}",
        file=sys.stderr,
    )


def mount_kernel_filesystems() -> None:
    _mount("devtmpfs", "/dev", "devtmpfs")
    _mount("proc", "/proc", "proc")
    _mount("sysfs", "/sys", "sysfs")


def _print_boot_record(snapshot: dict[str, object]) -> None:
    capabilities = snapshot.get("capabilities", {})
    present = []
    if isinstance(capabilities, dict):
        present = [
            name
            for name, value in capabilities.items()
            if isinstance(value, dict) and value.get("present")
        ]

    print("JETOS 0.1 — John E Tordoff's Operating System", flush=True)
    print(f"pid: {os.getpid()} (main JETOS supervisor interpreter)", flush=True)
    print(f"kernel: {platform.release()}", flush=True)
    print(f"architecture: {platform.machine()}", flush=True)
    print(f"language implementation: {sys.implementation.name}", flush=True)
    print(f"language runtime: {platform.python_version()}", flush=True)
    print(
        "stable Python base: "
        f"{getattr(sys, 'jetos_python_base_version', platform.python_version())}",
        flush=True,
    )
    print(f"isolated interpreters: {'yes' if supported() else 'no'}", flush=True)
    print(f"capabilities: {', '.join(sorted(present)) or 'none detected'}", flush=True)
    print("Dunicode: 0.2", flush=True)
    print("Unicode: supported", flush=True)
    print("encoding: UTF-8", flush=True)
    print("network policy: OFF by default", flush=True)


def _start_services(
    snapshot: dict[str, object],
) -> InterpreterSupervisor | None:
    if not supported():
        print(
            "subinterpreters: unavailable in bootstrap runtime; "
            "JETOS Language 3.14+ enables them",
            flush=True,
        )
        return None

    supervisor = InterpreterSupervisor()
    plans = plan_services(snapshot)
    handles = supervisor.start_plans(plans)
    print(
        f"subinterpreters: {len(handles)} capability services started "
        f"under main interpreter {supervisor.main_id}",
        flush=True,
    )
    return supervisor


def _run_console(
    snapshot: dict[str, object],
    supervisor: InterpreterSupervisor | None,
) -> None:
    print("session: JETOS Language diagnostic console", flush=True)
    print("objects: snapshot, hardware, supervisor", flush=True)
    print("", flush=True)
    namespace = {
        "snapshot": snapshot,
        "hardware": hardware,
        "supervisor": supervisor,
    }
    code.interact(
        banner="JETOS Language console",
        local=namespace,
        exitmsg="Leaving JETOS Language console",
    )


def _display_available() -> bool:
    if sys.platform in {"win32", "darwin"}:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _run_desktop() -> bool:
    """Run the standard-library GUI desktop if the display boundary exists."""
    if not _display_available():
        print(
            "desktop: unavailable (no guest display server/backend yet)",
            flush=True,
        )
        return False

    try:
        from jetos import desktop
    except Exception as error:
        print(f"desktop: unavailable ({error})", flush=True)
        return False

    print("session: JETOS Tkinter desktop", flush=True)
    print("", flush=True)

    try:
        desktop.run(fullscreen=True)
    except Exception as error:
        print(f"desktop exited with error: {error}", file=sys.stderr, flush=True)
        return False
    return True


def main() -> None:
    mount_kernel_filesystems()

    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")

    snapshot = hardware.discover()
    _print_boot_record(snapshot)
    supervisor = _start_services(snapshot)

    try:
        target = os.environ.get("JETOS_BOOT_TARGET", "desktop").lower()
        if target == "desktop":
            _run_desktop()
        _run_console(snapshot, supervisor)
    finally:
        if supervisor is not None:
            supervisor.close_all()


if __name__ == "__main__":
    main()
