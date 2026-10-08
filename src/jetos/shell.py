"""JETOS Gen2 command shell: small, direct, Python-owned, and GUI-independent."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
from typing import Callable

from jetos.identity import UserIdentity, current_user


class ShellExit(Exception):
    pass


def prompt(user: UserIdentity | None = None) -> str:
    identity = user or current_user()
    return f"{identity.label}@jetos:{Path.cwd()}> "


def _path(argument: str | None) -> Path:
    return Path(argument or ".").expanduser()


def _dir(args: list[str]) -> None:
    target = _path(args[0] if args else None)
    if target.is_file():
        print(target)
        return
    for path in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        marker = "<DIR>" if path.is_dir() else f"{path.stat().st_size:>12}"
        print(f"{marker:>12}  {path.name}")


def _cd(args: list[str]) -> None:
    if not args:
        print(Path.cwd())
        return
    os.chdir(_path(args[0]))


def _pwd(args: list[str]) -> None:
    del args
    print(Path.cwd())


def _type(args: list[str]) -> None:
    if not args:
        print("TYPE requires a file path")
        return
    path = _path(args[0])
    try:
        sys.stdout.write(path.read_text(encoding="utf-8"))
        if path.stat().st_size and not path.read_bytes().endswith(b"\n"):
            print()
    except UnicodeDecodeError:
        print(f"{path}: binary/non-UTF-8 file")


def _run(args: list[str]) -> None:
    if not args:
        print("RUN requires a program path or executable name")
        return
    completed = subprocess.run(args, check=False)
    if completed.returncode:
        print(f"program exited with status {completed.returncode}")


def _python(args: list[str], namespace: dict[str, object], user: UserIdentity) -> None:
    from jetos import console

    if args:
        subprocess.run([sys.executable, *args], check=False)
        return
    print("Entering JetOS Python. Use exit() or Ctrl-D to return to the JETOS shell.")
    console.interact(
        namespace=namespace,
        user=user,
        banner="JetOS Python interactive environment",
        exitmsg="Returning to JETOS command shell",
    )


def _system(args: list[str], namespace: dict[str, object]) -> None:
    del args
    snapshot = namespace.get("snapshot")
    print("JETOS Gen2")
    print(f"kernel: {platform.release()}")
    print(f"architecture: {platform.machine()}")
    print(f"JetOS Python: {platform.python_version()} ({sys.implementation.name})")
    if isinstance(snapshot, dict):
        capabilities = snapshot.get("capabilities")
        if isinstance(capabilities, dict):
            present = sorted(
                name for name, value in capabilities.items()
                if isinstance(value, dict) and value.get("present")
            )
            print("capabilities: " + (", ".join(present) if present else "none detected"))


def _help(args: list[str]) -> None:
    del args
    print("""JETOS Gen2 commands
  DIR [path] / LS [path]   list files and directories
  CD [path]                change/show current directory
  PWD                      show current directory
  TYPE file / CAT file     display a UTF-8 text file
  RUN program [args...]    launch a program directly
  PYTHON [args...]         enter JetOS Python, or run JetOS Python arguments
  SYSTEM                   show operating-system/runtime information
  CLEAR / CLS              clear the terminal
  HELP                     show this help
  EXIT                     leave the shell (ignored when JETOS is PID 1)

A path to an executable may also be entered directly as a convenience.
Graphical interfaces are provided separately by Decaptor and are not required here.""")


def _clear(args: list[str]) -> None:
    del args
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def execute(line: str, *, namespace: dict[str, object], user: UserIdentity) -> None:
    try:
        words = shlex.split(line)
    except ValueError as exc:
        print(f"parse error: {exc}")
        return
    if not words:
        return
    command = words[0].upper()
    args = words[1:]
    simple: dict[str, Callable[[list[str]], None]] = {
        "DIR": _dir,
        "LS": _dir,
        "CD": _cd,
        "PWD": _pwd,
        "TYPE": _type,
        "CAT": _type,
        "RUN": _run,
        "HELP": _help,
        "?": _help,
        "CLEAR": _clear,
        "CLS": _clear,
    }
    try:
        if command in simple:
            simple[command](args)
        elif command == "PYTHON":
            _python(args, namespace, user)
        elif command == "SYSTEM":
            _system(args, namespace)
        elif command in {"EXIT", "QUIT"}:
            raise ShellExit()
        else:
            candidate = Path(words[0]).expanduser()
            if candidate.exists() and candidate.is_file() and os.access(candidate, os.X_OK):
                _run([str(candidate), *args])
            else:
                print(f"Unknown command: {words[0]}. Type HELP.")
    except (OSError, ValueError) as exc:
        print(f"{type(exc).__name__}: {exc}")


def interact(*, namespace: dict[str, object], user: UserIdentity | None = None) -> None:
    identity = user or current_user()
    namespace.setdefault("user", identity)
    print("JETOS Gen2 command shell. Type HELP for commands.")
    while True:
        try:
            line = input(prompt(identity))
            execute(line, namespace=namespace, user=identity)
        except EOFError:
            print()
            if os.getpid() == 1:
                print("JETOS PID 1 remains active. Type HELP for commands.")
                continue
            return
        except KeyboardInterrupt:
            print("^C")
        except ShellExit:
            if os.getpid() == 1:
                print("JETOS PID 1 cannot exit; use a power/reboot control when available.")
                continue
            return
