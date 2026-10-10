#!/usr/bin/env python3
"""Build/run a minimal Hello World under JetOS Python inside Docker."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "jetos:gen2-dev"
VENDOR = ROOT / "gen2" / "vendor"
PYTHON_SOURCE = VENDOR / "jetos-python"
BUILD = ROOT / ".build" / "jetos-python-build"
PREFIX = ROOT / ".build" / "jetos-python-install"
HELLO = ROOT / "examples" / "hello.py"


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


def verify_or_bootstrap_gen2() -> None:
    verify = [sys.executable, "tools/gen2.py", "verify"]
    if run(verify, check=False).returncode == 0:
        return
    if VENDOR.exists():
        raise SystemExit(
            "Gen2 source exists but failed verification; inspect it instead of overwriting it."
        )
    run([sys.executable, "tools/bootstrap_gen2.py"])
    run(verify)


def runtime() -> Path:
    bindir = PREFIX / "bin"
    candidates = sorted(
        path
        for path in bindir.glob("python3.*")
        if path.is_file() and "config" not in path.name
    ) if bindir.exists() else []
    if candidates:
        return candidates[-1]

    run([
        sys.executable,
        "tools/jetos_python.py",
        "build",
        str(PYTHON_SOURCE),
        "--build",
        str(BUILD),
        "--prefix",
        str(PREFIX),
    ])
    run([
        sys.executable,
        "tools/jetos_python.py",
        "smoke",
        "--build",
        str(BUILD),
    ])
    run([
        sys.executable,
        "tools/jetos_python.py",
        "install",
        "--build",
        str(BUILD),
    ])
    return runtime()


def inside_container() -> int:
    verify_or_bootstrap_gen2()
    jetos_python = runtime()
    run([
        str(jetos_python),
        "-c",
        (
            "import sys; "
            "assert sys.implementation.name == 'jetos'; "
            "assert sys.jetos_python_generation == 'Gen2'"
        ),
    ])
    run([str(jetos_python), str(HELLO)])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run examples/hello.py with verified JetOS Python inside Docker"
    )
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inside:
        return inside_container()

    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is not installed")
    run([docker, "build", "-t", IMAGE, "."])
    return subprocess.call([
        docker,
        "run",
        "--rm",
        "-v",
        f"{ROOT}:/jetos",
        "-w",
        "/jetos",
        IMAGE,
        "python",
        "tools/docker_hello.py",
        "--inside",
    ], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
