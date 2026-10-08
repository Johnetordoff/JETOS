"""JETOS Gen2 first-stage userspace and JetOS Python PID-1 supervisor."""
from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import platform
import signal
import sys

from jetos import hardware, network, shell as jetos_shell, storage
from jetos.identity import UserIdentity, current_user
from jetos.interpreters import InterpreterSupervisor, plan_services, supported

libc = ctypes.CDLL(None, use_errno=True)
libc.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_char_p]
libc.mount.restype = ctypes.c_int


class RestartUserspace(Exception):
    """Raised in PID 1 when an authorized local Gen2 restart is requested."""


def _mount(source: str, target: str, filesystem: str) -> None:
    Path(target).mkdir(parents=True, exist_ok=True)
    result = libc.mount(source.encode(), target.encode(), filesystem.encode(), 0, None)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EBUSY:
        return
    if os.getpid() == 1:
        raise OSError(error, f"mount {filesystem} on {target} failed")
    print(
        f"JETOS dry-run: mount {filesystem} on {target} skipped: {os.strerror(error)}",
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
    session_user: UserIdentity,
) -> None:
    capabilities = snapshot.get("capabilities", {})
    present: list[str] = []
    if isinstance(capabilities, dict):
        present = [
            name for name, value in capabilities.items()
            if isinstance(value, dict) and value.get("present")
        ]

    print("JETOS Gen2 — John E Tordoff's Operating System", flush=True)
    print(f"pid: {os.getpid()} (JetOS Python supervisor)", flush=True)
    print(f"user: {session_user.describe()}", flush=True)
    print(f"kernel: {platform.release()}", flush=True)
    print(f"architecture: {platform.machine()}", flush=True)
    print(f"JetOS Python implementation: {sys.implementation.name}", flush=True)
    print(f"JetOS Python runtime: {platform.python_version()}", flush=True)
    print(f"isolated interpreters: {'yes' if supported() else 'no'}", flush=True)
    print(f"capabilities: {', '.join(sorted(present)) or 'none detected'}", flush=True)
    print("Dunicode: 0.2", flush=True)
    print("encoding: UTF-8", flush=True)
    print(
        "network policy: " + ("ON (explicit boot policy)" if network_status.enabled else "OFF by default"),
        flush=True,
    )
    print(
        "persistent storage encryption policy: "
        f"{'ON' if storage_policy.encryption_enabled else 'OFF'}",
        flush=True,
    )
    print("interface layer: Decaptor (separate; not required for Gen2 CLI)", flush=True)


def _start_services(snapshot: dict[str, object]) -> InterpreterSupervisor | None:
    if not supported():
        print("subinterpreters: unavailable in this JetOS Python build", flush=True)
        return None
    supervisor = InterpreterSupervisor()
    plans = plan_services(snapshot)
    handles = supervisor.start_plans(plans)
    print(
        f"subinterpreters: {len(handles)} capability services started under "
        f"main interpreter {supervisor.main_id}",
        flush=True,
    )
    return supervisor


def _run_shell(
    snapshot: dict[str, object],
    supervisor: InterpreterSupervisor | None,
    storage_policy: storage.StoragePolicy,
    network_status: network.NetworkStatus,
    session_user: UserIdentity,
) -> None:
    print("session: JETOS Gen2 command line", flush=True)
    print("JetOS Python remains available with the PYTHON command.", flush=True)
    print("", flush=True)
    namespace: dict[str, object] = {
        "user": session_user,
        "snapshot": snapshot,
        "hardware": hardware,
        "supervisor": supervisor,
        "storage_policy": storage_policy,
        "network_status": network_status,
    }
    jetos_shell.interact(namespace=namespace, user=session_user)


def _restart_handler(signum: int, frame: object) -> None:
    del signum, frame
    raise RestartUserspace()


def _restart_userspace() -> None:
    print("JETOS: restarting local Gen2 userspace", flush=True)
    os.execv("/usr/bin/python3", ["/usr/bin/python3", "/init"])


def main() -> None:
    mount_kernel_filesystems()
    # Gen2 uses the source baked into its sealed image.  No live remote/repository
    # lookup is part of normal boot.
    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")

    session_user = current_user()
    boot_storage_mode = os.environ.get("JETOS_BOOT_STORAGE_MODE")
    if boot_storage_mode is None:
        storage_policy = storage.policy_from_cmdline()
    else:
        storage_policy = storage.default_policy(
            encryption_enabled=storage.parse_encryption_mode(boot_storage_mode)
        )
    network_status = network.configure_from_cmdline()
    snapshot = hardware.discover()
    _print_boot_record(snapshot, storage_policy, network_status, session_user)
    supervisor = _start_services(snapshot)

    if os.getpid() == 1:
        signal.signal(signal.SIGHUP, _restart_handler)

    try:
        _run_shell(snapshot, supervisor, storage_policy, network_status, session_user)
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
