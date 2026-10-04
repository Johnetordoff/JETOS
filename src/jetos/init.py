"""JETOS first-stage userspace.

The kernel executes this module through /init. The first-stage process prints a
small boot record and then replaces itself with the CPython interactive
interpreter. Because exec() is used, CPython remains PID 1.
"""
from __future__ import annotations

import os
import platform
import sys


def main() -> None:
    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")

    print("JETOS 0.1 — John E Tordoff's Operating System", flush=True)
    print(f"kernel: {platform.release()}", flush=True)
    print(f"architecture: {platform.machine()}", flush=True)
    print(f"python: {platform.python_version()}", flush=True)
    print("Dunicode: 0.2", flush=True)
    print("Unicode: supported", flush=True)
    print("encoding: UTF-8", flush=True)
    print("shell: CPython", flush=True)
    print("", flush=True)

    # Replace JETOS init with CPython itself. In a real kernel boot this keeps
    # the Python interpreter as PID 1 instead of spawning a secondary shell.
    os.execv(sys.executable, [sys.executable, "-S", "-i"])


if __name__ == "__main__":
    main()
