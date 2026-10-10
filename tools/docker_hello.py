#!/usr/bin/env python3
"""Run minimal Hello World with verified JetOS Python inside Docker."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "jetos:gen2-dev"
VENDOR = ROOT / "gen2/vendor"
BUILD = ROOT / ".build/jetos-python-build"
PREFIX = ROOT / ".build/jetos-python-install"


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def runtime() -> Path:
    bindir = PREFIX / "bin"
    candidates = sorted(
        path for path in bindir.glob("python3.*")
        if path.is_file() and "config" not in path.name
    ) if bindir.exists() else []
    if candidates:
        return candidates[-1]

    run([
        sys.executable, "tools/jetos_python.py", "build", str(VENDOR / "jetos-python"),
        "--build", str(BUILD), "--prefix", str(PREFIX),
    ])
    run([sys.executable, "tools/jetos_python.py", "smoke", "--build", str(BUILD)])
    run([sys.executable, "tools/jetos_python.py", "install", "--build", str(BUILD)])
    return runtime()


def inside_container() -> int:
    if not VENDOR.exists():
        run([sys.executable, "tools/bootstrap_gen2.py"])
    run([sys.executable, "tools/gen2.py", "verify"])
    jetos_python = runtime()
    run([
        str(jetos_python), "-c",
        "import sys; assert sys.implementation.name == 'jetos'; "
        "assert sys.jetos_python_generation == 'Gen2'",
    ])
    run([str(jetos_python), "examples/hello.py"])
    return 0


def main() -> int:
    if "--inside" in sys.argv:
        return inside_container()

    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is not installed")
    run([docker, "build", "-t", IMAGE, "."])
    return subprocess.call([
        docker, "run", "--rm", "-v", f"{ROOT}:/jetos", "-w", "/jetos",
        IMAGE, "python", "tools/docker_hello.py", "--inside",
    ], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
