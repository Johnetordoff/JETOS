"""JETOS desktop application registry derived from machine capabilities."""
from __future__ import annotations

from dataclasses import dataclass

from jetos import hardware


@dataclass(frozen=True)
class AppSpec:
    key: str
    title: str
    capability: str | None = None


ALWAYS = (
    AppSpec("terminal", "Terminal"),
    AppSpec("system", "System"),
)

CAPABILITY_APPS = (
    AppSpec("display", "Display", "display"),
    AppSpec("network", "Network", "network"),
    AppSpec("wireless", "Wireless", "wireless"),
    AppSpec("bluetooth", "Bluetooth", "bluetooth"),
    AppSpec("storage", "Storage", "storage"),
    AppSpec("audio", "Audio", "audio"),
    AppSpec("input", "Input", "input"),
    AppSpec("camera", "Camera", "camera"),
    AppSpec("power", "Power", "battery"),
    AppSpec("virtualization", "Virtualization", "virtualization"),
    AppSpec("serial", "Serial", "serial"),
)


def available(snapshot: dict[str, object] | None = None) -> tuple[AppSpec, ...]:
    """Return applications that make sense for the detected machine.

    Terminal and System are always present. Hardware-specific applications are
    shown only when Linux exposes evidence for their capability.
    """
    current = snapshot if snapshot is not None else hardware.discover()
    result = list(ALWAYS)
    for app in CAPABILITY_APPS:
        assert app.capability is not None
        if bool(hardware.capability(current, app.capability).get("present")):
            result.append(app)
    return tuple(result)


def capability_details(
    app: AppSpec,
    snapshot: dict[str, object],
) -> dict[str, object]:
    if app.capability is None:
        return {}
    return hardware.capability(snapshot, app.capability)
