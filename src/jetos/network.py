"""JETOS network substrate: interface bring-up owned by the operating system."""
from __future__ import annotations

import fcntl
from pathlib import Path
import socket
import struct

SIOCGIFFLAGS, SIOCSIFFLAGS, SIOCSIFADDR, SIOCSIFNETMASK = 0x8913, 0x8914, 0x8916, 0x891C
IFF_UP = 0x1
LOOPBACK = b"lo"


def _ifreq(address: str | None = None) -> bytearray:
    request = bytearray(40)
    struct.pack_into("16s", request, 0, LOOPBACK)
    if address:
        struct.pack_into("H2x4s8x", request, 16, socket.AF_INET, socket.inet_aton(address))
    return request


def configure_loopback() -> None:
    """Give lo 127.0.0.1/8 and mark it UP, as any Linux early userspace does.

    Idempotent: reapplying the same address and flags to an up interface is a
    no-op, so later qualification stages may call it again to re-verify.
    """
    if not Path("/sys/class/net/lo").exists():
        raise AssertionError("loopback interface lo is missing")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        for code, address in ((SIOCSIFADDR, "127.0.0.1"), (SIOCSIFNETMASK, "255.0.0.0")):
            fcntl.ioctl(control.fileno(), code, _ifreq(address), True)
        request = _ifreq()
        fcntl.ioctl(control.fileno(), SIOCGIFFLAGS, request, True)
        struct.pack_into("H", request, 16, struct.unpack_from("H", request, 16)[0] | IFF_UP)
        fcntl.ioctl(control.fileno(), SIOCSIFFLAGS, request, True)
