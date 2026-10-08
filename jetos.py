#!/usr/bin/env python3
"""JETOS Gen2 development, inspection, and boot entry point."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from jetos import mode  # noqa: E402


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


def python_tool(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(ROOT / "tools" / name), *args])


def source_environment() -> dict[str, str]:
    env = os.environ.copy()
    source_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = source_path if not existing else source_path + os.pathsep + existing
    return env


def tests() -> None:
    for script in (
        "test.py", "test_unicode.py", "test_bootstrap.py", "test_capabilities.py",
        "test_desktop.py", "test_policy.py", "test_interpreters.py", "test_storage.py",
        "test_storage_modes.py", "test_runtime_image.py", "test_sources.py", "test_modes.py",
        "test_constitution.py", "test_console.py", "test_gen2.py",
    ):
        python_tool(script, [])


def docker_image() -> str:
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is not installed. Run `python jetos.py setup --plan` first.")
    run([docker, "build", "-t", "jetos:gen2-dev", "."])
    return docker


def docker_dev(*, build_only: bool, profile: str, encryption: str, display: str, vnc_port: int) -> None:
    docker = docker_image()
    command = [
        docker, "run", "--rm", "-it", "-v", f"{ROOT}:/jetos", "-w", "/jetos",
    ]
    if os.name == "posix" and Path("/dev/kvm").exists():
        command.extend(["--device", "/dev/kvm"])
    if display == "vnc":
        command.extend(["-p", f"127.0.0.1:{vnc_port}:5900"])
    command.extend([
        "jetos:gen2-dev", "python", "tools/dev.py", "build" if build_only else "run",
        "--profile", profile, "--encryption", encryption, "--display", display,
    ])
    if display == "vnc":
        command.extend(["--vnc-bind", "0.0.0.0"])
    raise SystemExit(subprocess.call(command, cwd=ROOT))


def boot_jetos(*, native: bool, build_only: bool, profile: str, encryption: str, display: str, vnc_port: int) -> None:
    canonical = mode.normalize(profile)
    print(
        f"JETOS Gen2 boot: mode={canonical} display={display} "
        f"backend={'native Linux build host' if native else 'portable bootstrap container/QEMU'}",
        flush=True,
    )
    if native:
        python_tool("dev.py", [
            "build" if build_only else "run", "--profile", canonical,
            "--encryption", encryption, "--display", display,
        ])
        return
    docker_dev(
        build_only=build_only,
        profile=canonical,
        encryption=encryption,
        display=display,
        vnc_port=vnc_port,
    )


def print_all_text() -> None:
    git = shutil.which("git")
    if not git:
        raise SystemExit("git is required to enumerate tracked JETOS text")
    result = subprocess.run([git, "ls-files"], cwd=ROOT, check=True, text=True, capture_output=True)
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
        "print('isolated interpreters:', supported()); [print(p) for p in plans]; "
    )
    if run_services:
        code += (
            "s=InterpreterSupervisor(); s.start_plans(plans); print('running:', s.services); "
            "[print(name, s.request(name, ('ping',))) for name in s.services]; s.close_all();"
        )
    return subprocess.call([sys.executable, "-c", code], cwd=ROOT, env=source_environment())


def print_modes() -> None:
    print("""JETOS Gen2

One-time generation intake
  python jetos.py gen2 bootstrap

Verify / inspect the sealed generation
  python jetos.py gen2 verify
  python jetos.py gen2 status
  python jetos.py gen2 census

Boot the real Gen2 command-line operating system
  python jetos.py run

The normal Gen2 build uses only sealed local `gen2/vendor/jetos-python` and
`gen2/vendor/jetos-kernel` source. Missing source is an error; build/boot does not
fetch or freshness-check external releases.

Fat Mode carries JETOS, JetOS Python, and JETOS kernel source for development and
introspection. Skinny Mode strips development payload for target images.

JetOS Python is available from the running JETOS command shell with `PYTHON`.
Graphical/interface work belongs to Decaptor and is not required for the CLI boot.
""")


def add_boot_arguments(parser: argparse.ArgumentParser, *, default_profile: str) -> None:
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--profile", choices=mode.CLI_CHOICES, default=default_profile)
    parser.add_argument("--encryption", choices=("on", "off"), default="on")
    parser.add_argument("--display", choices=("serial", "window", "vnc"), default="serial")
    parser.add_argument("--vnc-port", type=int, default=5901)


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS Gen2: bootstrap once, then build/boot from sealed local source")
    sub = parser.add_subparsers(dest="command", required=True)

    run_command = sub.add_parser("run", aliases=["boot"], help="build and boot JETOS Gen2 to its command shell")
    add_boot_arguments(run_command, default_profile=mode.FAT)
    dev = sub.add_parser("dev", help="lower-level Gen2 build/boot controls")
    add_boot_arguments(dev, default_profile=mode.SKINNY)

    gen2 = sub.add_parser("gen2", help="bootstrap/verify/inspect the frozen Gen2 source generation")
    gen2_sub = gen2.add_subparsers(dest="gen2_command", required=True)
    gen2_sub.add_parser("bootstrap", help="one-time pull-in, internalize, seal, and discard staging")
    gen2_sub.add_parser("verify")
    gen2_sub.add_parser("status")
    gen2_sub.add_parser("census")

    sub.add_parser("doctor", help="check bootstrap/development host prerequisites")
    setup = sub.add_parser("setup", help="plan or install host prerequisites")
    setup.add_argument("--plan", action="store_true")
    setup.add_argument("--install", action="store_true")
    setup.add_argument("--yes", action="store_true")
    sub.add_parser("test", help="run JETOS structural/unit tests")
    sub.add_parser("text", help="print every tracked UTF-8 JETOS-owned file")
    sub.add_parser("modes", help="show Gen2 intake/run/profile model")

    interpreters = sub.add_parser("interpreters")
    interpreters.add_argument("--per-device", action="store_true")
    interpreters.add_argument("--run", action="store_true")

    storage_parser = sub.add_parser("storage")
    storage_parser.add_argument("paths", nargs="*", default=["/", "/boot", "/tmp"])
    storage_parser.add_argument("--strict", action="store_true")
    storage_parser.add_argument("--encryption", choices=("on", "off"), default="on")
    storage_parser.add_argument("--override", action="append", default=[])
    storage_parser.add_argument("--config")

    size = sub.add_parser("size")
    size.add_argument("--strict", action="store_true")
    size.add_argument("--rootfs-budget-mib", type=float, default=128.0)
    size.add_argument("--initramfs-budget-mib", type=float, default=48.0)

    args = parser.parse_args()
    if args.command in {"run", "boot", "dev"}:
        boot_jetos(
            native=args.native, build_only=args.build_only, profile=args.profile,
            encryption=args.encryption, display=args.display, vnc_port=args.vnc_port,
        )
    elif args.command == "gen2":
        if args.gen2_command == "bootstrap":
            return python_tool("bootstrap_gen2.py", []).returncode
        return python_tool("gen2.py", [args.gen2_command]).returncode
    elif args.command == "doctor":
        python_tool("host.py", ["doctor"])
    elif args.command == "setup":
        forwarded = ["install" if args.install else "plan"]
        if args.yes:
            forwarded.append("--yes")
        python_tool("host.py", forwarded)
    elif args.command == "test":
        tests()
    elif args.command == "text":
        print_all_text()
    elif args.command == "modes":
        print_modes()
    elif args.command == "interpreters":
        return interpreter_diagnostics(args.per_device, args.run)
    elif args.command == "storage":
        forwarded = [*args.paths, "--encryption", args.encryption]
        for value in args.override:
            forwarded.extend(["--override", value])
        if args.config:
            forwarded.extend(["--config", args.config])
        if args.strict:
            forwarded.append("--strict")
        return run([sys.executable, str(ROOT / "tools/storage_status.py"), *forwarded], check=False).returncode
    elif args.command == "size":
        forwarded = [
            "--rootfs-budget-mib", str(args.rootfs_budget_mib),
            "--initramfs-budget-mib", str(args.initramfs_budget_mib),
        ]
        if args.strict:
            forwarded.append("--strict")
        return run([sys.executable, str(ROOT / "tools/size_report.py"), *forwarded], check=False).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
