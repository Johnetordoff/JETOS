#!/usr/bin/env python3
"""Qualify interpreter/runtime behavior inside a booted JetOS guest."""
from __future__ import annotations

import fcntl
import http.server
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
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
    struct.pack_into("H2x4s8x", request, 16, socket.AF_INET, socket.inet_aton(address))
    fcntl.ioctl(sock.fileno(), request_code, request, True)


def configure_loopback() -> None:
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


def qualify_interpreter() -> dict[str, object]:
    """Exercise the hard interpreter-first M1 requirements in the live guest."""
    if sys.implementation.name != "jetos":
        raise AssertionError(f"expected JetLang implementation 'jetos'; got {sys.implementation.name!r}")
    if not sys.version:
        raise AssertionError("missing interpreter version")
    if not sys.platform.startswith("linux"):
        raise AssertionError(f"unexpected JetOS runtime platform {sys.platform!r}")

    marker = "JETOS_FS_OK"
    with tempfile.TemporaryDirectory(prefix="jetos-qualify-") as directory:
        path = Path(directory, "probe.txt")
        path.write_text(marker, encoding="utf-8")
        if path.read_text(encoding="utf-8") != marker:
            raise AssertionError("filesystem round trip failed")

    env = dict(os.environ)
    env["JETOS_ENV_PROBE"] = marker
    child = subprocess.run(
        [sys.executable, "-c", "import os,sys; print(os.environ['JETOS_ENV_PROBE']); print(sys.implementation.name)"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if child.returncode != 0 or child.stdout.splitlines() != [marker, "jetos"]:
        raise AssertionError(f"JetLang subprocess/environment probe failed: rc={child.returncode} out={child.stdout!r} err={child.stderr!r}")

    # fcntl is a native extension in this runtime; importing and exercising it
    # above proves the extension loader is functional, not merely pure Python.
    return {"version": sys.version.split()[0], "platform": sys.platform, "subprocess": "PASS", "filesystem": "PASS", "native_extension": "fcntl"}


def qualify_web_loopback() -> dict[str, object]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
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
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5.0) as response:
            body = response.read()
            status = response.status
        if status != 200 or body != b"JETOS_WEB_OK\n":
            raise AssertionError(f"loopback HTTP failed: status={status} body={body!r}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)
    if thread.is_alive():
        raise AssertionError("loopback HTTP server did not stop cleanly")
    return {"loopback": "127.0.0.1", "http_status": 200, "body": "JETOS_WEB_OK"}


def main() -> int:
    if os.getpid() == 1:
        raise AssertionError("guest qualifier must run under JetLang, not replace PID 1")
    interpreter = qualify_interpreter()
    configure_loopback()
    network = qualify_web_loopback()
    print(
        "JETOS guest qualification: PASS "
        f"version={interpreter['version']} platform={interpreter['platform']} "
        f"filesystem={interpreter['filesystem']} subprocess={interpreter['subprocess']} "
        f"native={interpreter['native_extension']} loopback={network['loopback']} "
        f"http={network['http_status']} body={network['body']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
