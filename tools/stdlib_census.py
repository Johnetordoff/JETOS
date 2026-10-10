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
    "dbm": "import dbm,tempfile; p=tempfile.mktemp(); d=dbm.open(p,'c'); d[b'x']=b'y'; assert d[b'x']==b'y'; d.close()",
    "hashing": "import hashlib; assert hashlib.sha256(b'jetos').digest()",
    "mmap": "import mmap; m=mmap.mmap(-1,4096); m[:5]=b'jetos'; assert m[:5]==b'jetos'; m.close()",
    "selectors": "import selectors; s=selectors.DefaultSelector(); s.close()",
    "socket": "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); s.close()",
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
        print(f"{'PASS' if ok else 'FAIL'} import {name}" + (f": {detail}" if detail else ""))
        if not ok:
            failures.append((f"import {name}", detail))

    probe_failures: list[tuple[str, str]] = []
    if not args.modules:
        for name, code in PROBES.items():
            ok, detail = check(code)
            print(f"{'PASS' if ok else 'FAIL'} capability {name}" + (f": {detail}" if detail else ""))
            if not ok:
                probe_failures.append((name, detail))
        if args.online:
            ok, detail = check(ONLINE, timeout=15)
            print(f"{'PASS' if ok else 'FAIL'} capability online-https" + (f": {detail}" if detail else ""))
            if not ok:
                probe_failures.append(("online-https", detail))

    total_failures = failures + probe_failures
    print(
        f"Python 3.14 stdlib census: {len(modules) - len(failures)}/{len(modules)} imports; "
        f"{len(PROBES) - len(probe_failures)}/{len(PROBES)} native probes"
    )
    return int(args.strict and bool(total_failures))


if __name__ == "__main__":
    raise SystemExit(main())
