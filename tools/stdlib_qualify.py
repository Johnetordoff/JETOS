#!/usr/bin/env python3
"""Qualify the complete JETOS/Python standard-library surface before OS reduction.

The language is the invariant.  This tool measures whether the current OS
substrate still supports the same Python standard-library modules and exposed
callables.  It deliberately does not blindly invoke arbitrary callables: some
stdlib functions terminate the process, replace it, fork it, mutate the host,
or perform external I/O.  Functional behavior is covered by explicit safe
capability probes and, for reduction qualification, CPython's own regression
suite via --full.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

NON_LINUX = frozenset(
    {
        "_msi",
        "_overlapped",
        "_scproxy",
        "_winapi",
        "msvcrt",
        "nt",
        "winreg",
        "winsound",
    }
)

IMPORT_CODE = r'''import importlib, sys
name = sys.argv[1]
if name == "antigravity":
    import webbrowser
    webbrowser.open = lambda *args, **kwargs: True
importlib.import_module(name)
'''

INVENTORY_CODE = r'''import importlib, inspect, json, sys
name = sys.argv[1]
if name == "antigravity":
    import webbrowser
    webbrowser.open = lambda *args, **kwargs: True
module = importlib.import_module(name)
items = []

def signature(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None

def add(path, obj, kind):
    items.append({"path": path, "kind": kind, "signature": signature(obj)})

for attr, obj in sorted(vars(module).items()):
    if not callable(obj):
        continue
    if inspect.isclass(obj):
        add(attr, obj, "class")
        try:
            members = vars(obj)
        except TypeError:
            members = {}
        for member_name, raw in sorted(members.items()):
            candidate = raw.__func__ if isinstance(raw, (staticmethod, classmethod)) else raw
            if callable(candidate):
                add(f"{attr}.{member_name}", candidate, "method")
    else:
        add(attr, obj, "builtin" if inspect.isbuiltin(obj) else "function")
print(json.dumps(items, sort_keys=True, separators=(",", ":")))
'''

PROBES = {
    "asyncio": (
        "import asyncio; "
        "assert asyncio.run(asyncio.sleep(0, result='jetos')) == 'jetos'"
    ),
    "compression": (
        "import bz2,lzma,zlib; d=b'jetos'; "
        "assert bz2.decompress(bz2.compress(d))==d; "
        "assert lzma.decompress(lzma.compress(d))==d; "
        "assert zlib.decompress(zlib.compress(d))==d"
    ),
    "ctypes": "import ctypes; assert ctypes.CDLL(None)",
    "curses": (
        "import curses,os; os.environ.setdefault('TERM','xterm'); "
        "curses.setupterm()"
    ),
    "dbm": (
        "import dbm,tempfile,pathlib; t=tempfile.TemporaryDirectory(); "
        "p=str(pathlib.Path(t.name)/'db'); d=dbm.open(p,'c'); "
        "d[b'x']=b'y'; assert d[b'x']==b'y'; d.close(); t.cleanup()"
    ),
    "filesystem": (
        "import pathlib,tempfile; t=tempfile.TemporaryDirectory(); "
        "p=pathlib.Path(t.name)/'x'; p.write_bytes(b'jetos'); "
        "assert p.read_bytes()==b'jetos'; p.rename(pathlib.Path(t.name)/'y'); "
        "t.cleanup()"
    ),
    "hashing": "import hashlib; assert hashlib.sha256(b'jetos').digest()",
    "json": (
        "import json; x={'jetos':[1,True,None]}; "
        "assert json.loads(json.dumps(x))==x"
    ),
    "mmap": (
        "import mmap; m=mmap.mmap(-1,4096); m[:5]=b'jetos'; "
        "assert m[:5]==b'jetos'; m.close()"
    ),
    "pty": "import os,pty; a,b=pty.openpty(); os.close(a); os.close(b)",
    "selectors": "import selectors; s=selectors.DefaultSelector(); s.close()",
    "socket": (
        "import socket; socket.getaddrinfo('localhost',0); "
        "a=socket.socket(); a.bind(('127.0.0.1',0)); a.close(); "
        "b=socket.socket(socket.AF_INET6); b.bind(('::1',0)); b.close()"
    ),
    "sqlite3": (
        "import sqlite3; c=sqlite3.connect(':memory:'); "
        "assert c.execute('select 1').fetchone()==(1,); c.close()"
    ),
    "ssl": "import ssl; assert ssl.OPENSSL_VERSION and ssl.create_default_context()",
    "subprocess": (
        "import subprocess,sys; "
        "subprocess.run([sys.executable,'-c','pass'],check=True)"
    ),
    "tcl": "import tkinter; assert tkinter.Tcl().eval('expr 1+1')=='2'",
    "threading": (
        "import threading; x=[]; t=threading.Thread(target=lambda:x.append(1)); "
        "t.start(); t.join(); assert x==[1]"
    ),
}

ONLINE = (
    "import urllib.request; "
    "r=urllib.request.urlopen('https://example.com',timeout=10); "
    "assert 200 <= r.status < 400"
)


def child(
    code: str,
    *args: str,
    timeout: int = 10,
) -> subprocess.CompletedProcess[str] | None:
    env = dict(os.environ, PYTHONNOUSERSITE="1")
    try:
        return subprocess.run(
            [sys.executable, "-I", "-c", code, *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return None


def detail(result: subprocess.CompletedProcess[str] | None) -> str:
    if result is None:
        return "timeout"
    text = (result.stderr or result.stdout).strip().splitlines()
    return text[-1] if text else ""


def ok(result: subprocess.CompletedProcess[str] | None) -> bool:
    return result is not None and result.returncode == 0


def inventory(name: str) -> tuple[bool, list[dict[str, Any]], str]:
    result = child(INVENTORY_CODE, name, timeout=15)
    if not ok(result):
        return False, [], detail(result)
    assert result is not None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return False, [], "inventory produced no JSON"
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        return False, [], f"inventory JSON error: {exc}"
    return True, value, ""


def surface(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return only the stable language/API surface used for comparisons."""
    return {
        name: entry.get("callables", [])
        for name, entry in sorted(manifest.get("modules", {}).items())
        if entry.get("import") == "PASS"
    }


def run_full_suite() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-I", "-m", "test", "-j1"],
        text=True,
    )
    return result.returncode == 0, f"exit {result.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify the JETOS/Python stdlib before reducing the OS substrate"
    )
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run CPython's full installed regression suite",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return nonzero for any applicable qualification failure",
    )
    args = parser.parse_args()

    modules = sorted(set(args.modules or sys.stdlib_module_names) - NON_LINUX)
    failures: list[str] = []
    manifest: dict[str, Any] = {
        "implementation": sys.implementation.name,
        "python": sys.version,
        "platform": sys.platform,
        "executable": sys.executable,
        "modules": {},
        "probes": {},
    }
    callable_total = 0

    for name in modules:
        imported = child(IMPORT_CODE, name)
        if not ok(imported):
            message = detail(imported)
            print(f"FAIL import {name}: {message}")
            manifest["modules"][name] = {
                "import": "FAIL",
                "detail": message,
                "callables": [],
            }
            failures.append(f"import {name}")
            continue

        good, callables, message = inventory(name)
        if not good:
            print(f"FAIL inventory {name}: {message}")
            manifest["modules"][name] = {
                "import": "PASS",
                "inventory": "FAIL",
                "detail": message,
                "callables": [],
            }
            failures.append(f"inventory {name}")
            continue

        callable_total += len(callables)
        manifest["modules"][name] = {
            "import": "PASS",
            "inventory": "PASS",
            "callables": callables,
        }
        print(f"PASS module {name}: {len(callables)} callable symbols")

    if not args.modules:
        probes = dict(PROBES)
        if args.online:
            probes["online-https"] = ONLINE
        for name, code in probes.items():
            result = child(code, timeout=20 if name == "online-https" else 10)
            passed = ok(result)
            message = detail(result)
            manifest["probes"][name] = "PASS" if passed else f"FAIL: {message}"
            print(f"{'PASS' if passed else 'FAIL'} capability {name}" + (f": {message}" if not passed else ""))
            if not passed:
                failures.append(f"capability {name}")

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if surface(baseline) != surface(manifest):
            print("FAIL language surface differs from baseline")
            failures.append("language surface baseline")
        else:
            print("PASS language surface matches baseline")

    if args.full:
        passed, message = run_full_suite()
        manifest["cpython_regression_suite"] = "PASS" if passed else f"FAIL: {message}"
        print(f"{'PASS' if passed else 'FAIL'} CPython regression suite: {message}")
        if not passed:
            failures.append("CPython regression suite")

    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"manifest: {args.manifest}")

    passed_modules = sum(
        entry.get("import") == "PASS" and entry.get("inventory") == "PASS"
        for entry in manifest["modules"].values()
    )
    print(
        "stdlib qualification: "
        f"{passed_modules}/{len(modules)} modules; "
        f"{callable_total} callable symbols inventoried; "
        f"{len(failures)} failures"
    )
    return int(args.strict and bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
