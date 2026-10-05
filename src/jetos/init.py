"""JETOS first-stage userspace and main-interpreter OS supervisor."""
from __future__ import annotations

import code
import ctypes
import errno
import os
from pathlib import Path
import platform
import signal
import sys

from jetos import hardware, network, storage
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


class RestartUserspace(Exception):
    """Raised in PID 1 when a validated live-source update requests restart."""


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
    if error == errno.EBUSY:
        return
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


def _print_boot_record(
    snapshot: dict[str, object],
    storage_policy: storage.StoragePolicy,
    network_status: network.NetworkStatus,
) -> None:
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
    print(
        "network policy: "
        + ("ON (explicit boot policy)" if network_status.enabled else "OFF by default"),
        flush=True,
    )
    if network_status.enabled:
        resolver = ", ".join(network_status.nameservers) or "not supplied by kernel DHCP"
        print(f"network resolver: {resolver}", flush=True)
    print(
        "persistent storage encryption policy: "
        f"{'ON' if storage_policy.encryption_enabled else 'OFF'}",
        flush=True,
    )
    repo = os.environ.get("JETOS_REPO")
    if repo:
        print(f"live source repository: {repo}", flush=True)


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
    storage_policy: storage.StoragePolicy,
    network_status: network.NetworkStatus,
) -> None:
    print("session: JETOS Language diagnostic console", flush=True)
    print(
        "objects: snapshot, hardware, supervisor, storage_policy, network_status",
        flush=True,
    )
    print("", flush=True)
    namespace = {
        "snapshot": snapshot,
        "hardware": hardware,
        "supervisor": supervisor,
        "storage_policy": storage_policy,
        "network_status": network_status,
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
    if not _display_available():
        print(
            "desktop: unavailable (no local display server/backend yet)",
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


def _restart_handler(signum: int, frame: object) -> None:
    del signum, frame
    raise RestartUserspace()


def _restart_userspace() -> None:
    print("JETOS: restarting userspace from live Git source", flush=True)
    os.execv("/usr/bin/python3", ["/usr/bin/python3", "/init"])


def main() -> None:
    mount_kernel_filesystems()

    live_repo = os.environ.get("JETOS_REPO")
    if live_repo and (Path(live_repo) / "src").is_dir():
        os.environ["PYTHONPATH"] = f"{live_repo}/src:/jetos/src"
    else:
        os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")

    storage_policy = storage.policy_from_cmdline()
    network_status = network.configure_from_cmdline()
    snapshot = hardware.discover()
    _print_boot_record(snapshot, storage_policy, network_status)
    supervisor = _start_services(snapshot)

    if os.getpid() == 1:
        signal.signal(signal.SIGHUP, _restart_handler)

    try:
        target = os.environ.get("JETOS_BOOT_TARGET", "desktop").lower()
        if target == "desktop":
            _run_desktop()
        _run_console(snapshot, supervisor, storage_policy, network_status)
    except RestartUserspace:
        if supervisor is not None:
            supervisor.close_all()
            supervisor = None
        _restart_userspace()
    finally:
        if supervisor is not None:
            supervisor.close_all()


if __name__ == "__main__":
    main()
