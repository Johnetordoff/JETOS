#!/usr/bin/env python3
"""One-command entry point for developing and booting JETOS."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


def python_tool(name: str, args: list[str]) -> None:
    run([sys.executable, str(ROOT / "tools" / name), *args])


def tests() -> None:
    for script in ("test.py", "test_unicode.py", "test_language.py", "test_bootstrap.py"):
        python_tool(script, [])


def docker_dev(build_only: bool) -> None:
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit(
            "Docker is not installed. Run `python jetos.py setup --plan` "
            "or `python jetos.py setup --install`."
        )
    run([docker, "build", "-t", "jetos:dev", "."])
    command = [
        docker,
        "run",
        "--rm",
        "-it",
        "-v",
        f"{ROOT}:/jetos",
        "-w",
        "/jetos",
    ]
    if os.name == "posix" and Path("/dev/kvm").exists():
        command.extend(["--device", "/dev/kvm"])
    command.extend([
        "jetos:dev",
        "python",
        "tools/dev.py",
        "build" if build_only else "run",
    ])
    os.execvp(docker, command)


def print_all_text() -> None:
    git = shutil.which("git")
    if not git:
        raise SystemExit("git is required to enumerate repository text")
    result = subprocess.run(
        [git, "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    for relative in result.stdout.splitlines():
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        print(f"\n===== {relative} =====\n")
        print(text, end="" if text.endswith("\n") else "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JETOS development, build, and VM entry point"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check host development prerequisites")

    setup = sub.add_parser("setup", help="plan or install host prerequisites")
    setup.add_argument("--plan", action="store_true")
    setup.add_argument("--install", action="store_true")
    setup.add_argument("--yes", action="store_true")

    sub.add_parser("test", help="run repository tests")

    dev = sub.add_parser(
        "dev",
        help="build and boot JETOS in its portable Docker/QEMU development environment",
    )
    dev.add_argument("--build-only", action="store_true")
    dev.add_argument(
        "--native",
        action="store_true",
        help="run build/QEMU directly on a Linux development host instead of Docker",
    )

    workbot = sub.add_parser(
        "workbot",
        help="start the local JETOS build/test/improvement server",
    )
    workbot.add_argument("--host", default="127.0.0.1")
    workbot.add_argument("--port", type=int, default=8787)
    workbot.add_argument(
        "--interval",
        type=int,
        default=0,
        help="enqueue a full work cycle every N seconds while idle; 0 disables",
    )

    sub.add_parser("text", help="print every tracked UTF-8 text file in JETOS")

    args = parser.parse_args()

    if args.command == "doctor":
        python_tool("host.py", ["doctor"])
    elif args.command == "setup":
        mode = "install" if args.install else "plan"
        forwarded = [mode]
        if args.yes:
            forwarded.append("--yes")
        python_tool("host.py", forwarded)
    elif args.command == "test":
        tests()
    elif args.command == "dev":
        if args.native:
            python_tool("dev.py", ["build" if args.build_only else "run"])
        else:
            docker_dev(args.build_only)
    elif args.command == "workbot":
        python_tool(
            "workbot.py",
            [
                "serve",
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--interval",
                str(args.interval),
            ],
        )
    elif args.command == "text":
        print_all_text()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
