"""Capability-oriented Linux hardware introspection for JETOS.

JETOS does not infer a device role from a product name.  It inspects the
kernel's observable hardware surfaces and records the evidence it can see.
The registry deliberately separates capability presence from current activity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import platform
from typing import Iterable


@dataclass(frozen=True)
class Capability:
    name: str
    present: bool
    active: bool
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _children(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir(), key=lambda item: item.name)
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return []


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return None


def _relative_names(paths: Iterable[Path]) -> tuple[str, ...]:
    return tuple(sorted(path.name for path in paths))


def _network(root: Path) -> tuple[Capability, Capability]:
    interfaces = [
        path
        for path in _children(root / "sys/class/net")
        if path.name != "lo"
    ]
    active = [
        path.name
        for path in interfaces
        if _read(path / "operstate") == "up"
    ]
    network_evidence = [path.name for path in interfaces]
    network_evidence.extend(f"active:{name}" for name in active)

    wireless = [
        path.name
        for path in interfaces
        if (path / "wireless").exists()
    ]
    radios = _children(root / "sys/class/ieee80211")
    wireless_evidence = sorted(set(wireless + [path.name for path in radios]))

    return (
        Capability(
            "network",
            present=bool(interfaces),
            active=bool(active),
            evidence=tuple(network_evidence),
        ),
        Capability(
            "wireless",
            present=bool(wireless_evidence),
            active=any(name in active for name in wireless),
            evidence=tuple(wireless_evidence),
        ),
    )


def _display(root: Path) -> Capability:
    connectors: list[str] = []
    connected: list[str] = []
    modes: list[str] = []
    for path in _children(root / "sys/class/drm"):
        status = _read(path / "status")
        if status is None:
            continue
        connectors.append(path.name)
        if status == "connected":
            connected.append(path.name)
            mode_text = _read(path / "modes") or ""
            for mode in mode_text.splitlines():
                if mode:
                    modes.append(f"{path.name}:{mode}")

    framebuffer = _children(root / "sys/class/graphics")
    evidence = [f"connector:{name}" for name in connectors]
    evidence.extend(f"connected:{name}" for name in connected)
    evidence.extend(f"mode:{mode}" for mode in modes)
    evidence.extend(f"framebuffer:{path.name}" for path in framebuffer)
    return Capability(
        "display",
        present=bool(connectors or framebuffer),
        active=bool(connected or framebuffer),
        evidence=tuple(evidence),
    )


def _simple_capability(
    root: Path,
    name: str,
    directory: str,
    *,
    prefix: str | None = None,
) -> Capability:
    paths = _children(root / directory)
    if prefix is not None:
        paths = [path for path in paths if path.name.startswith(prefix)]
    evidence = _relative_names(paths)
    return Capability(name, bool(paths), bool(paths), evidence)


def _storage(root: Path) -> Capability:
    ignored_prefixes = ("loop", "ram", "zram")
    devices = [
        path
        for path in _children(root / "sys/block")
        if not path.name.startswith(ignored_prefixes)
    ]
    evidence: list[str] = []
    for path in devices:
        size = _read(path / "size")
        evidence.append(path.name if size is None else f"{path.name}:sectors={size}")
    return Capability("storage", bool(devices), bool(devices), tuple(evidence))


def _battery(root: Path) -> Capability:
    batteries: list[Path] = []
    for path in _children(root / "sys/class/power_supply"):
        kind = _read(path / "type")
        if kind == "Battery" or path.name.startswith("BAT"):
            batteries.append(path)
    evidence: list[str] = []
    active = False
    for path in batteries:
        capacity = _read(path / "capacity")
        status = _read(path / "status")
        parts = [path.name]
        if capacity is not None:
            parts.append(f"{capacity}%")
        if status:
            parts.append(status)
            active = active or status.lower() not in {"unknown", "not charging"}
        evidence.append(":".join(parts))
    return Capability("battery", bool(batteries), active, tuple(evidence))


def _camera(root: Path) -> Capability:
    devices = sorted((root / "dev").glob("video*")) if (root / "dev").is_dir() else []
    return Capability("camera", bool(devices), bool(devices), _relative_names(devices))


def _bluetooth(root: Path) -> Capability:
    controllers = _children(root / "sys/class/bluetooth")
    evidence = [path.name for path in controllers]
    if not evidence:
        for path in _children(root / "sys/class/rfkill"):
            kind = _read(path / "type")
            if kind == "bluetooth":
                evidence.append(path.name)
    return Capability("bluetooth", bool(evidence), bool(evidence), tuple(evidence))


def _memory_bytes(root: Path) -> int | None:
    text = _read(root / "proc/meminfo")
    if not text:
        return None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            fields = line.split()
            if len(fields) >= 2 and fields[1].isdigit():
                return int(fields[1]) * 1024
    return None


def discover(root: Path | str = "/") -> dict[str, object]:
    """Return a JETOS capability snapshot from Linux kernel-visible evidence.

    ``root`` exists primarily so the detector can be tested against a synthetic
    filesystem tree. On a running JETOS system it is simply ``/``.
    """
    root_path = Path(root)
    network, wireless = _network(root_path)
    capabilities = [
        _display(root_path),
        network,
        wireless,
        _bluetooth(root_path),
        _simple_capability(root_path, "audio", "sys/class/sound"),
        _storage(root_path),
        _simple_capability(root_path, "input", "sys/class/input"),
        _camera(root_path),
        _battery(root_path),
        Capability(
            "virtualization",
            present=(root_path / "dev/kvm").exists(),
            active=(root_path / "dev/kvm").exists(),
            evidence=("/dev/kvm",) if (root_path / "dev/kvm").exists() else (),
        ),
        _simple_capability(root_path, "serial", "sys/class/tty", prefix="ttyS"),
    ]

    return {
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_bytes": _memory_bytes(root_path),
        "has_sysfs": (root_path / "sys").is_dir(),
        "has_procfs": (root_path / "proc").is_dir(),
        "has_device_tree": (root_path / "sys/firmware/devicetree/base").exists(),
        "has_acpi": (root_path / "sys/firmware/acpi").exists(),
        "capabilities": {
            capability.name: capability.as_dict()
            for capability in capabilities
        },
    }


def capability(snapshot: dict[str, object], name: str) -> dict[str, object]:
    capabilities = snapshot.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return {"name": name, "present": False, "active": False, "evidence": ()}
    value = capabilities.get(name)
    if isinstance(value, dict):
        return value
    return {"name": name, "present": False, "active": False, "evidence": ()}


def snapshot() -> dict[str, object]:
    """Compatibility alias for the original bootstrap API."""
    return discover()
