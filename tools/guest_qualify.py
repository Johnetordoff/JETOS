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
    if not Path("/sys/class/net/lo").exists():
        raise AssertionError("loopback interface lo is missing")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        for code, address in ((SIOCSIFADDR, "127.0.0.1"), (SIOCSIFNETMASK, "255.0.0.0")):
            request = _ifreq(address)
            fcntl.ioctl(control.fileno(), code, request, True)
        request = _ifreq()
        fcntl.ioctl(control.fileno(), SIOCGIFFLAGS, request, True)
        struct.pack_into("H", request, 16, struct.unpack_from("H", request, 16)[0] | IFF_UP)
        fcntl.ioctl(control.fileno(), SIOCSIFFLAGS, request, True)


def qualify_interpreter() -> tuple[str, str]:
    if sys.implementation.name != "jetos":
        raise AssertionError(f"expected JetLang implementation 'jetos'; got {sys.implementation.name!r}")
    if not sys.version or not sys.platform.startswith("linux"):
        raise AssertionError(f"unexpected JetOS runtime {sys.version!r} on {sys.platform!r}")

    marker = "JETOS_FS_OK"
    with tempfile.TemporaryDirectory(prefix="jetos-qualify-") as directory:
        path = Path(directory, "probe.txt")
        path.write_text(marker, encoding="utf-8")
        if path.read_text(encoding="utf-8") != marker:
            raise AssertionError("filesystem round trip failed")

    env = {**os.environ, "JETOS_ENV_PROBE": marker}
    child = subprocess.run(
        [sys.executable, "-c", "import os,sys; print(os.environ['JETOS_ENV_PROBE']); print(sys.implementation.name)"],
        capture_output=True, text=True, env=env,
    )
    if child.returncode or child.stdout.splitlines() != [marker, "jetos"]:
        raise AssertionError(f"JetLang subprocess/environment probe failed: {child.returncode=} {child.stdout=!r} {child.stderr=!r}")
    return sys.version.split()[0], sys.platform


def qualify_web_loopback() -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = b"JETOS_WEB_OK\n"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/", timeout=5.0) as response:
            body, status = response.read(), response.status
        if (status, body) != (200, b"JETOS_WEB_OK\n"):
            raise AssertionError(f"loopback HTTP failed: status={status} body={body!r}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)
    if thread.is_alive():
        raise AssertionError("loopback HTTP server did not stop cleanly")


def main() -> int:
    if os.getpid() == 1:
        raise AssertionError("guest qualifier must run under JetLang, not replace PID 1")
    version, platform_name = qualify_interpreter()
    configure_loopback()
    qualify_web_loopback()
    print(
        "JETOS guest qualification: PASS "
        f"version={version} platform={platform_name} filesystem=PASS subprocess=PASS "
        "native=fcntl loopback=127.0.0.1 http=200 body=JETOS_WEB_OK",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
