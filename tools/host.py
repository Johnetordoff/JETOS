#!/usr/bin/env python3
"""Host prerequisite detection and development-environment installation."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys


LINUX_NATIVE_COMMANDS = (
    "git",
    "gcc",
    "make",
    "ld",
    "as",
    "ar",
    "objcopy",
    "bc",
    "bison",
    "flex",
    "pahole",
    "pkg-config",
)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def host_name() -> str:
    return platform.system().lower()


def linux_manager() -> str | None:
    for manager in ("apt-get", "dnf", "pacman", "zypper"):
        if command_exists(manager):
            return manager
    return None


def prefix_admin(command: list[str]) -> list[str]:
    if os.name != "posix" or os.geteuid() == 0:
        return command
    sudo = shutil.which("sudo")
    if not sudo:
        raise SystemExit("administrator privileges are required and sudo is unavailable")
    return [sudo, *command]


def plan(*, include_docker: bool = True) -> list[list[str]]:
    host = host_name()
    if host == "darwin":
        if not command_exists("brew"):
            raise SystemExit(
                "Homebrew is required for the automated macOS setup. "
                "Install Homebrew from its official site, then rerun this command."
            )
        commands = [["brew", "install", "git", "qemu"]]
        if include_docker:
            commands.append(["brew", "install", "--cask", "docker"])
        return commands

    if host == "windows":
        if not command_exists("winget"):
            raise SystemExit("winget is required for the automated Windows setup")
        commands = [["winget", "install", "--id", "Git.Git", "-e"]]
        if include_docker:
            commands.append(["winget", "install", "--id", "Docker.DockerDesktop", "-e"])
        return commands

    if host != "linux":
        raise SystemExit(f"unsupported development host: {platform.system()}")

    manager = linux_manager()
    docker_packages: list[str] = []
    if include_docker:
        docker_packages = ["docker.io"] if manager == "apt-get" else ["docker"]

    if manager == "apt-get":
        packages = [
            "git", *docker_packages, "qemu-system-x86", "qemu-system-arm",
            "gcc", "make", "binutils", "libc6-dev", "bc", "bison", "flex",
            "libssl-dev", "libelf-dev", "dwarves", "pkg-config", "libffi-dev",
            "zlib1g-dev", "libbz2-dev", "libreadline-dev", "libsqlite3-dev",
            "liblzma-dev", "uuid-dev", "xz-utils",
        ]
        return [
            prefix_admin(["apt-get", "update"]),
            prefix_admin(["apt-get", "install", "-y", *packages]),
        ]
    if manager == "dnf":
        packages = [
            "git", *docker_packages, "qemu-system-x86", "qemu-system-aarch64",
            "gcc", "make", "binutils", "bc", "bison", "flex", "openssl-devel",
            "elfutils-libelf-devel", "dwarves", "pkgconf-pkg-config", "libffi-devel",
            "zlib-devel", "bzip2-devel", "readline-devel", "sqlite-devel",
            "xz-devel", "libuuid-devel",
        ]
        return [prefix_admin(["dnf", "install", "-y", *packages])]
    if manager == "pacman":
        packages = [
            "git", *docker_packages, "qemu-system-x86", "qemu-system-aarch64",
            "base-devel", "bc", "bison", "flex", "openssl", "libelf", "pahole",
            "pkgconf", "libffi", "zlib", "bzip2", "readline", "sqlite", "xz",
            "util-linux",
        ]
        return [prefix_admin(["pacman", "-S", "--needed", *packages])]
    if manager == "zypper":
        packages = [
            "git", *docker_packages, "qemu-x86", "qemu-arm", "gcc", "make", "binutils",
            "bc", "bison", "flex", "libopenssl-devel", "libelf-devel", "dwarves",
            "pkg-config", "libffi-devel", "zlib-devel", "libbz2-devel",
            "readline-devel", "sqlite3-devel", "xz-devel", "libuuid-devel",
        ]
        return [prefix_admin(["zypper", "--non-interactive", "install", *packages])]

    raise SystemExit("no supported Linux package manager found")


def doctor(*, native: bool = False) -> int:
    host = platform.system()
    machine = platform.machine()
    print(f"host: {host} {machine}")
    print(f"python: {sys.version.split()[0]} ({sys.executable})")

    if native:
        if host != "Linux":
            print("native development mode requires Linux")
            return 1
        commands = list(LINUX_NATIVE_COMMANDS)
        commands.append(
            "qemu-system-aarch64"
            if machine.lower() in {"aarch64", "arm64"}
            else "qemu-system-x86_64"
        )
        print("development mode: native Linux builder + QEMU guest")
    else:
        commands = ["git", "docker"]
        print("development mode: Docker-hosted Linux builder + QEMU guest")

    missing = []
    for command in commands:
        found = shutil.which(command)
        print(f"{command}: {found or 'MISSING'}")
        if not found:
            missing.append(command)

    if missing:
        print("missing prerequisites:", ", ".join(missing))
        if native and host == "Linux":
            print("remediation: python3 jetos.py setup --install --yes --native")
        return 1

    print("JETOS host prerequisites: PASS")
    return 0


def install(yes: bool, *, include_docker: bool = True) -> None:
    commands = plan(include_docker=include_docker)
    for command in commands:
        print("+", " ".join(command))
    if not yes:
        raise SystemExit("rerun with `--yes` to execute this installation plan")
    for command in commands:
        subprocess.run(command, check=True)
    if include_docker and host_name() == "linux" and command_exists("systemctl"):
        subprocess.run(
            prefix_admin(["systemctl", "enable", "--now", "docker"]),
            check=False,
        )
    if include_docker:
        print(
            "Host prerequisites installed. Docker Desktop may still need to be "
            "opened once on macOS/Windows."
        )
    else:
        print("Native Linux build prerequisites installed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS host setup")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--native", action="store_true")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--native", action="store_true")
    installer = sub.add_parser("install")
    installer.add_argument("--yes", action="store_true")
    installer.add_argument("--native", action="store_true")
    args = parser.parse_args()

    if args.command == "doctor":
        return doctor(native=args.native)
    if args.command == "plan":
        for command in plan(include_docker=not args.native):
            print(" ".join(command))
        return 0
    if args.command == "install":
        install(args.yes, include_docker=not args.native)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
