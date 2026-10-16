#!/usr/bin/env python3
"""One-command entry point for developing and booting JETOS."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DOCKER_TEST_IMAGE = "jetos:fat-test"
DOCKER_DEV_IMAGE = "jetos:dev"
DOCKER_DEV_BUILD_VOLUME = "jetos-dev-build"
TEST_TARGET = "test"
DEV_TARGET = "dev"
SOURCE_MARKERS = {
    "source/linux": "Makefile",
    "source/cpython": "Python/sysmodule.c",
}


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


def python_tool(name: str, args: list[str]) -> None:
    run([sys.executable, str(ROOT / "tools" / name), *args])


def tests() -> None:
    for script in (
        "test.py", "test_unicode.py", "test_language.py", "test_bootstrap.py",
        "test_behind_a_log.py",
    ):
        python_tool(script, [])


def missing_source_trees() -> list[str]:
    return [tree for tree, marker in SOURCE_MARKERS.items() if not (ROOT / tree / marker).is_file()]


def ensure_dev_sources() -> None:
    """Ensure the recorded source trees exist before building JETOS."""
    missing = missing_source_trees()
    if not missing:
        return
    if (ROOT / ".gitmodules").is_file():
        git = shutil.which("git")
        if not git:
            raise SystemExit("JETOS transitional source preparation requires Git")
        run([git, "submodule", "update", "--init", "--recursive", "source/linux", "source/cpython"])
        missing = missing_source_trees()
        if not missing:
            return
    raise SystemExit(
        "JETOS source trees are missing: " + ", ".join(missing)
        + ". Complete/vendored source is required before kernel and JetLang builds."
    )


def apple_silicon_docker_platform():
    machine = platform.machine().lower()
    if sys.platform == "darwin" and machine in {"arm64", "aarch64"}:
        return "linux/arm64"
    return None


def require_docker() -> str:
    """Check Docker only for explicitly requested optional Docker harness commands."""
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit(
            "The optional JETOS Docker harness requires Docker. JetOS itself has no Docker or distribution-base runtime dependency."
        )
    probe = subprocess.run(
        [docker, "info", "--format", "{{.ServerVersion}}"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip() or "no diagnostic output"
        raise SystemExit("Docker harness requested but Docker is unreachable: " + detail)
    print(f"Docker daemon: {probe.stdout.strip()}")
    return docker


def docker_bootstrap_image() -> str:
    """Return caller-supplied external tooling image; JetOS chooses no distro."""
    image = os.environ.get("JETOS_BOOTSTRAP_IMAGE", "").strip()
    if not image:
        raise SystemExit(
            "Optional Docker harness requires JETOS_BOOTSTRAP_IMAGE to name an external image that already provides python3, git, cc, make, ld, ccache, QEMU, and strace. JetOS deliberately supplies no Debian/Gentoo/default distribution image."
        )
    return image


def docker_test() -> None:
    docker = require_docker()
    bootstrap = docker_bootstrap_image()
    docker_platform = apple_silicon_docker_platform()
    build_command = [docker, "build", "--pull", "--build-arg", f"JETOS_BOOTSTRAP_IMAGE={bootstrap}"]
    if docker_platform:
        build_command.extend(["--platform", docker_platform])
    build_command.extend(["--target", TEST_TARGET, "--tag", DOCKER_TEST_IMAGE, "."])
    run(build_command)
    run_command = [docker, "run", "--rm"]
    if docker_platform:
        run_command.extend(["--platform", docker_platform])
    run_command.append(DOCKER_TEST_IMAGE)
    run(run_command)


def docker_dev(build_only: bool) -> None:
    docker = require_docker()
    bootstrap = docker_bootstrap_image()
    docker_platform = apple_silicon_docker_platform()
    build_command = [docker, "build", "--pull", "--build-arg", f"JETOS_BOOTSTRAP_IMAGE={bootstrap}"]
    if docker_platform:
        build_command.extend(["--platform", docker_platform])
    build_command.extend(["--target", DEV_TARGET, "--tag", DOCKER_DEV_IMAGE, "."])
    run(build_command)
    command = [docker, "run", "--rm"]
    if docker_platform:
        command.extend(["--platform", docker_platform])
    if sys.stdin.isatty() and sys.stdout.isatty():
        command.append("-it")
    command.extend([
        "-v", f"{ROOT}:/jetos",
        "-v", f"{DOCKER_DEV_BUILD_VOLUME}:/jetos/.build",
        "-w", "/jetos",
    ])
    print(f"JETOS Docker build workspace: {DOCKER_DEV_BUILD_VOLUME} -> /jetos/.build", flush=True)
    if os.name == "posix" and Path("/dev/kvm").exists():
        command.extend(["--device", "/dev/kvm"])
    command.extend([DOCKER_DEV_IMAGE, "python3", "tools/dev.py", "build" if build_only else "run"])
    os.execvp(docker, command)


def print_all_text() -> None:
    git = shutil.which("git")
    if not git:
        raise SystemExit("git is required to enumerate repository text")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS development, build, and VM entry point")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check the optional Docker harness")
    setup = sub.add_parser("setup", help="plan or install optional host tooling")
    setup.add_argument("--plan", action="store_true")
    setup.add_argument("--install", action="store_true")
    setup.add_argument("--yes", action="store_true")
    sub.add_parser("test", help="run repository tests on the current host")
    sub.add_parser("docker-test", help="run optional container qualification using a caller-supplied bootstrap image")
    dev = sub.add_parser("dev", help="build/boot through the optional Docker/QEMU harness")
    dev.add_argument("--build-only", action="store_true")
    work_server = sub.add_parser("work-server", help="run the persistent self-hosted JETOS build/test/improvement server")
    work_server.add_argument("--host", default="127.0.0.1")
    work_server.add_argument("--port", type=int, default=8787)
    work_cycle = sub.add_parser("work-cycle", help="run one isolated JETOS Work Server qualification/improvement cycle")
    work_cycle.add_argument("--improve", action="store_true")
    work_cycle.add_argument("--push", action="store_true")
    sub.add_parser("text", help="print every tracked UTF-8 text file in JETOS")
    args = parser.parse_args()

    if args.command == "doctor":
        require_docker()
        docker_bootstrap_image()
        print("JETOS optional Docker harness: PASS")
    elif args.command == "setup":
        mode = "install" if args.install else "plan"
        forwarded = [mode]
        if args.yes:
            forwarded.append("--yes")
        python_tool("host.py", forwarded)
    elif args.command == "test":
        tests()
    elif args.command == "docker-test":
        docker_test()
    elif args.command == "dev":
        ensure_dev_sources()
        docker_dev(args.build_only)
    elif args.command == "work-server":
        python_tool("work_server.py", ["serve", "--host", args.host, "--port", str(args.port)])
    elif args.command == "work-cycle":
        forwarded = ["run-cycle"]
        if args.improve:
            forwarded.append("--improve")
        if args.push:
            forwarded.append("--push")
        python_tool("work_server.py", forwarded)
    elif args.command == "text":
        print_all_text()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
