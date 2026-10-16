#!/usr/bin/env python3
"""Qualify networking/runtime behavior inside a booted JetOS guest."""
from __future__ import annotations

import fcntl
import http.server
import os
from pathlib import Path
import socket
import struct
import sys
import threading
import urllib.request

SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
SIOCSIFADDR = 0x8916
SIOCSIFNETMASK = 0x891C
IFF_UP = 0x1
IFREQ_SIZE = 40
LOOPBACK = b"lo"


def _ifreq() -> bytearray:
    request = bytearray(IFREQ_SIZE)
    struct.pack_into("16s", request, 0, LOOPBACK)
    return request


def _set_ipv4(sock: socket.socket, request_code: int, address: str) -> None:
    request = _ifreq()
    struct.pack_into(
        "H2x4s8x",
        request,
        16,
        socket.AF_INET,
        socket.inet_aton(address),
    )
    fcntl.ioctl(sock.fileno(), request_code, request, True)


def configure_loopback() -> None:
    """Bring Linux loopback up without depending on iproute2/BusyBox."""
    if not Path("/sys/class/net/lo").exists():
        raise AssertionError("loopback interface lo is missing")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        _set_ipv4(control, SIOCSIFADDR, "127.0.0.1")
        _set_ipv4(control, SIOCSIFNETMASK, "255.0.0.0")

        request = _ifreq()
        fcntl.ioctl(control.fileno(), SIOCGIFFLAGS, request, True)
        flags = struct.unpack_from("H", request, 16)[0]
        struct.pack_into("H", request, 16, flags | IFF_UP)
        fcntl.ioctl(control.fileno(), SIOCSIFFLAGS, request, True)


def qualify_web_loopback() -> dict[str, object]:
    """Serve one HTTP response and fetch it through JetLang's own stdlib."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            body = b"JETOS_WEB_OK\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/",
            timeout=5.0,
        ) as response:
            body = response.read()
            status = response.status
        if status != 200:
            raise AssertionError(f"loopback HTTP returned status {status}")
        if body != b"JETOS_WEB_OK\n":
            raise AssertionError(f"loopback HTTP returned unexpected body {body!r}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)

    if thread.is_alive():
        raise AssertionError("loopback HTTP server did not stop cleanly")

    return {
        "loopback": "127.0.0.1",
        "http_status": 200,
        "body": "JETOS_WEB_OK",
    }


def main() -> int:
    if os.getpid() == 1:
        raise AssertionError("guest qualifier must run under JetLang, not replace PID 1")
    if sys.implementation.name != "jetos":
        raise AssertionError(
            f"guest qualifier requires JetLang implementation 'jetos'; got {sys.implementation.name!r}"
        )

    configure_loopback()
    report = qualify_web_loopback()
    print(
        "JETOS guest qualification: PASS "
        f"loopback={report['loopback']} "
        f"http={report['http_status']} "
        f"body={report['body']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
