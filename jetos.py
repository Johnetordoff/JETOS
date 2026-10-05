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


def python_tool(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(ROOT / "tools" / name), *args])


def source_environment() -> dict[str, str]:
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing else source_path + os.pathsep + existing
    )
    return environment


def tests() -> None:
    for script in (
        "test.py",
        "test_unicode.py",
        "test_language.py",
        "test_bootstrap.py",
        "test_capabilities.py",
        "test_desktop.py",
        "test_policy.py",
        "test_interpreters.py",
        "test_storage.py",
        "test_storage_modes.py",
    ):
        python_tool(script, [])


def docker_image() -> str:
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit(
            "Docker is not installed. Run `python jetos.py setup --plan` first."
        )
    run([docker, "build", "-t", "jetos:dev", "."])
    return docker


def docker_dev(
    *,
    build_only: bool,
    profile: str,
    encryption: str,
    display: str,
    vnc_port: int,
) -> None:
    docker = docker_image()
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
    if display == "vnc":
        command.extend(["-p", f"127.0.0.1:{vnc_port}:5900"])
    command.extend(
        [
            "jetos:dev",
            "python",
            "tools/dev.py",
            "build" if build_only else "run",
            "--profile",
            profile,
            "--encryption",
            encryption,
            "--display",
            display,
        ]
    )
    if display == "vnc":
        command.extend(["--vnc-bind", "0.0.0.0"])
        print(f"QEMU VNC will be published at localhost:{vnc_port}", flush=True)
    raise SystemExit(subprocess.call(command, cwd=ROOT))


def docker_gui(geometry: str, port: int) -> None:
    docker = docker_image()
    print(f"Open a VNC viewer at localhost:{port}", flush=True)
    command = [
        docker,
        "run",
        "--rm",
        "-it",
        "-p",
        f"127.0.0.1:{port}:5900",
        "-v",
        f"{ROOT}:/jetos",
        "-w",
        "/jetos",
        "jetos:dev",
        "python",
        "tools/gui_server.py",
        "--geometry",
        geometry,
        "--port",
        "5900",
    ]
    raise SystemExit(subprocess.call(command, cwd=ROOT))


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


def interpreter_diagnostics(per_device: bool, run_services: bool) -> int:
    code = (
        "from jetos import hardware; "
        "from jetos.interpreters import InterpreterSupervisor, plan_services, supported; "
        "snapshot=hardware.discover(); "
        f"plans=plan_services(snapshot, per_device={per_device!r}); "
        "print('isolated interpreters:', supported()); "
        "[print(p) for p in plans]; "
    )
    if run_services:
        code += (
            "s=InterpreterSupervisor(); "
            "s.start_plans(plans); "
            "print('running:', s.services); "
            "[print(name, s.request(name, ('ping',))) for name in s.services]; "
            "s.close_all();"
        )
    return subprocess.call(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=source_environment(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS development/test entry point")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check host development prerequisites")
    setup = sub.add_parser("setup", help="plan or install host prerequisites")
    setup.add_argument("--plan", action="store_true")
    setup.add_argument("--install", action="store_true")
    setup.add_argument("--yes", action="store_true")

    sub.add_parser("test", help="run JETOS repository tests")
    sub.add_parser("language-check", help="check latest-stable Python pin")
    sub.add_parser("text", help="print every tracked UTF-8 JETOS file")

    interpreters = sub.add_parser("interpreters", help="show/run service interpreters")
    interpreters.add_argument("--per-device", action="store_true")
    interpreters.add_argument("--run", action="store_true")

    gui = sub.add_parser("gui", help="run Tkinter desktop directly on this host")
    gui.add_argument("--geometry")
    gui.add_argument("--fullscreen", action="store_true")
    gui.add_argument("--no-splash", action="store_true")

    gui_docker = sub.add_parser(
        "gui-docker",
        help="run the real Tk desktop in Docker and expose it over localhost VNC",
    )
    gui_docker.add_argument("--geometry", default="640x480")
    gui_docker.add_argument("--port", type=int, default=5900)

    storage = sub.add_parser("storage", help="inspect global/scoped storage policy")
    storage.add_argument("paths", nargs="*", default=["/", "/boot", "/tmp"])
    storage.add_argument("--strict", action="store_true")
    storage.add_argument("--encryption", choices=("on", "off"), default="on")
    storage.add_argument("--override", action="append", default=[])
    storage.add_argument("--config")

    dev = sub.add_parser("dev", help="build/boot the real JETOS VM")
    dev.add_argument("--build-only", action="store_true")
    dev.add_argument("--native", action="store_true")
    dev.add_argument("--profile", choices=("lean", "full"), default="lean")
    dev.add_argument("--encryption", choices=("on", "off"), default="on")
    dev.add_argument("--display", choices=("serial", "window", "vnc"), default="serial")
    dev.add_argument("--vnc-port", type=int, default=5901)

    size = sub.add_parser("size", help="measure/enforce JETOS image-size budgets")
    size.add_argument("--strict", action="store_true")
    size.add_argument("--rootfs-budget-mib", type=float, default=128.0)
    size.add_argument("--initramfs-budget-mib", type=float, default=48.0)

    args = parser.parse_args()

    if args.command == "doctor":
        python_tool("host.py", ["doctor"])
    elif args.command == "setup":
        forwarded = ["install" if args.install else "plan"]
        if args.yes:
            forwarded.append("--yes")
        python_tool("host.py", forwarded)
    elif args.command == "test":
        tests()
    elif args.command == "language-check":
        python_tool("python_release.py", ["check"])
    elif args.command == "text":
        print_all_text()
    elif args.command == "interpreters":
        return interpreter_diagnostics(args.per_device, args.run)
    elif args.command == "gui":
        command = [sys.executable, "-m", "jetos.desktop"]
        if args.geometry:
            command.extend(["--geometry", args.geometry])
        if args.fullscreen:
            command.append("--fullscreen")
        if args.no_splash:
            command.append("--no-splash")
        return subprocess.call(command, cwd=ROOT, env=source_environment())
    elif args.command == "gui-docker":
        docker_gui(args.geometry, args.port)
    elif args.command == "storage":
        forwarded = [*args.paths, "--encryption", args.encryption]
        for value in args.override:
            forwarded.extend(["--override", value])
        if args.config:
            forwarded.extend(["--config", args.config])
        if args.strict:
            forwarded.append("--strict")
        return run(
            [sys.executable, str(ROOT / "tools/storage_status.py"), *forwarded],
            check=False,
        ).returncode
    elif args.command == "dev":
        if args.native:
            forwarded = [
                "build" if args.build_only else "run",
                "--profile",
                args.profile,
                "--encryption",
                args.encryption,
                "--display",
                args.display,
            ]
            python_tool("dev.py", forwarded)
        else:
            docker_dev(
                build_only=args.build_only,
                profile=args.profile,
                encryption=args.encryption,
                display=args.display,
                vnc_port=args.vnc_port,
            )
    elif args.command == "size":
        forwarded = [
            "--rootfs-budget-mib",
            str(args.rootfs_budget_mib),
            "--initramfs-budget-mib",
            str(args.initramfs_budget_mib),
        ]
        if args.strict:
            forwarded.append("--strict")
        return run(
            [sys.executable, str(ROOT / "tools/size_report.py"), *forwarded],
            check=False,
        ).returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
