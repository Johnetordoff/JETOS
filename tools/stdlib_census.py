#!/usr/bin/env python3
"""Measure Python 3.14 standard-library capability on the current OS substrate."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

TARGET = (3, 14)
GENTOO_NA = frozenset({"_msi", "_overlapped", "_scproxy", "_winapi", "msvcrt", "nt", "winreg", "winsound"})
IMPORT = (
    "import importlib,sys; "
    "name=sys.argv[1]; "
    "exec(\"import webbrowser; webbrowser.open=lambda *a,**k: True\" if name=='antigravity' else ''); "
    "importlib.import_module(name)"
)
PROBES = {
    "compression": "import bz2,lzma,zlib; d=b'jetos'; assert bz2.decompress(bz2.compress(d))==d and lzma.decompress(lzma.compress(d))==d and zlib.decompress(zlib.compress(d))==d",
    "ctypes": "import ctypes; assert ctypes.CDLL(None)",
    "curses": "import curses,os; os.environ.setdefault('TERM','xterm'); curses.setupterm()",
    "dbm": "import dbm,tempfile,pathlib; t=tempfile.TemporaryDirectory(); p=str(pathlib.Path(t.name)/'db'); d=dbm.open(p,'c'); d[b'x']=b'y'; assert d[b'x']==b'y'; d.close(); t.cleanup()",
    "hashing": "import hashlib; assert hashlib.sha256(b'jetos').digest()",
    "mmap": "import mmap; m=mmap.mmap(-1,4096); m[:5]=b'jetos'; assert m[:5]==b'jetos'; m.close()",
    "pty": "import os,pty; a,b=pty.openpty(); os.close(a); os.close(b)",
    "selectors": "import selectors; s=selectors.DefaultSelector(); s.close()",
    "socket": "import socket; assert socket.has_ipv6; socket.getaddrinfo('localhost',0); a=socket.socket(); a.bind(('127.0.0.1',0)); a.close(); b=socket.socket(socket.AF_INET6); b.bind(('::1',0)); b.close()",
    "sqlite3": "import sqlite3; c=sqlite3.connect(':memory:'); assert c.execute('select 1').fetchone()==(1,); c.close()",
    "ssl": "import ssl; assert ssl.OPENSSL_VERSION and ssl.create_default_context()",
    "subprocess": "import subprocess,sys; subprocess.run([sys.executable,'-c','pass'],check=True)",
    "tcl": "import tkinter; assert tkinter.Tcl().eval('expr 1+1')=='2'",
}
ONLINE = "import urllib.request; r=urllib.request.urlopen('https://example.com',timeout=10); assert 200 <= r.status < 400"


def check(code: str, *args: str, timeout: int = 10) -> tuple[bool, str]:
    env = dict(os.environ, PYTHONNOUSERSITE="1")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code, *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    text = (result.stderr or result.stdout).strip().splitlines()
    return result.returncode == 0, (text[-1] if text else "")


def show(kind: str, name: str, ok: bool, detail: str) -> None:
    suffix = f": {detail}" if not ok and detail else ""
    print(f"{'PASS' if ok else 'FAIL'} {kind} {name}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Python 3.14 stdlib against its OS substrate")
    parser.add_argument("--online", action="store_true", help="also require DNS/TLS/HTTPS Internet access")
    parser.add_argument("--strict", action="store_true", help="exit nonzero for any applicable failure")
    parser.add_argument("--module", action="append", dest="modules", help="audit only this module (repeatable)")
    args = parser.parse_args()

    if sys.version_info[:2] != TARGET:
        raise SystemExit(f"expected Python 3.14, got {sys.version.split()[0]}")

    modules = sorted(set(args.modules or sys.stdlib_module_names) - GENTOO_NA)
    failures: list[tuple[str, str]] = []
    for name in modules:
        ok, detail = check(IMPORT, name)
        show("import", name, ok, detail)
        if not ok:
            failures.append((f"import {name}", detail))

    probe_total = probe_passed = 0
    probe_failures: list[tuple[str, str]] = []
    if not args.modules:
        probes = dict(PROBES)
        if args.online:
            probes["online-https"] = ONLINE
        for name, code in probes.items():
            probe_total += 1
            ok, detail = check(code, timeout=15 if name == "online-https" else 10)
            show("capability", name, ok, detail)
            if ok:
                probe_passed += 1
            else:
                probe_failures.append((name, detail))

    total_failures = failures + probe_failures
    print(
        f"Python 3.14 stdlib census: {len(modules) - len(failures)}/{len(modules)} imports; "
        f"{probe_passed}/{probe_total} capability probes"
    )
    return int(args.strict and bool(total_failures))


if __name__ == "__main__":
    raise SystemExit(main())
