"""Minimal first-boot network policy for JETOS."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NetworkStatus:
    enabled: bool
    resolver_configured: bool
    nameservers: tuple[str, ...]


def _cmdline() -> tuple[str, ...]:
    try:
        return tuple(Path("/proc/cmdline").read_text(encoding="utf-8").split())
    except OSError:
        return ()


def enabled_from_cmdline() -> bool:
    values = {
        field.split("=", 1)[1].lower()
        for field in _cmdline()
        if field.startswith("jetos.network=") and "=" in field
    }
    return bool(values & {"1", "on", "true", "yes"})


def kernel_dhcp_nameservers() -> tuple[str, ...]:
    path = Path("/proc/net/pnp")
    if not path.exists():
        return ()
    found: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ()
    for raw in lines:
        fields = raw.split()
        if len(fields) >= 2 and fields[0].lower() == "nameserver":
            value = fields[1]
            if value not in found and value != "0.0.0.0":
                found.append(value)
    return tuple(found)


def configure_resolver(nameservers: tuple[str, ...]) -> bool:
    if not nameservers:
        return False
    etc = Path("/etc")
    etc.mkdir(parents=True, exist_ok=True)
    resolver = etc / "resolv.conf"
    resolver.write_text(
        "".join(f"nameserver {value}\n" for value in nameservers),
        encoding="utf-8",
    )
    return True


def configure_from_cmdline() -> NetworkStatus:
    if not enabled_from_cmdline():
        return NetworkStatus(False, False, ())
    nameservers = kernel_dhcp_nameservers()
    configured = configure_resolver(nameservers)
    return NetworkStatus(True, configured, nameservers)
