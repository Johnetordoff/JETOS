#!/usr/bin/env python3
"""Host prerequisite detection and Docker installation planning for JETOS."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess


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


def plan() -> list[list[str]]:
    """Install only the host boundary; build dependencies belong in Docker."""
    host = host_name()
    if host == "darwin":
        if not command_exists("brew"):
            raise SystemExit("Homebrew is required for automated macOS Docker setup")
        return [["brew", "install", "git"], ["brew", "install", "--cask", "docker"]]
    if host == "windows":
        if not command_exists("winget"):
            raise SystemExit("winget is required for automated Windows Docker setup")
        return [
            ["winget", "install", "--id", "Git.Git", "-e"],
            ["winget", "install", "--id", "Docker.DockerDesktop", "-e"],
        ]
    if host != "linux":
        raise SystemExit(f"unsupported development host: {platform.system()}")
    manager = linux_manager()
    if manager == "apt-get":
        return [prefix_admin(["apt-get", "update"]), prefix_admin(["apt-get", "install", "-y", "git", "docker.io"])]
    if manager == "dnf":
        return [prefix_admin(["dnf", "install", "-y", "git", "docker"])]
    if manager == "pacman":
        return [prefix_admin(["pacman", "-S", "--needed", "git", "docker"])]
    if manager == "zypper":
        return [prefix_admin(["zypper", "--non-interactive", "install", "git", "docker"])]
    raise SystemExit("no supported Linux package manager found")


def install(yes: bool) -> None:
    commands = plan()
    for command in commands:
        print("+", " ".join(command))
    if not yes:
        raise SystemExit("rerun with `--yes` to execute this installation plan")
    for command in commands:
        subprocess.run(command, check=True)
    if host_name() == "linux" and command_exists("systemctl"):
        subprocess.run(prefix_admin(["systemctl", "enable", "--now", "docker"]), check=False)
    print("Host boundary installed. Build/compiler/QEMU dependencies are supplied inside the JETOS Docker image.")


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS Docker host setup")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    installer = sub.add_parser("install")
    installer.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        for command in plan():
            print(" ".join(command))
        return 0
    if args.command == "install":
        install(args.yes)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
