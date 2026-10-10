#!/usr/bin/env python3
"""Run minimal Hello World with verified JetOS Python inside Docker."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "jetos:gen2-dev"


def inside_container() -> int:
    if not (ROOT / "gen2/vendor").exists():
        subprocess.run([sys.executable, "tools/bootstrap_gen2.py"], cwd=ROOT, check=True)

    from tools import dev

    dev.verify_gen2()
    runtime, _ = dev.build_jetos_python()
    subprocess.run([
        str(runtime),
        "-c",
        (
            "import sys; "
            "assert sys.implementation.name == 'jetos'; "
            "assert sys.jetos_python_generation == 'Gen2'"
        ),
    ], cwd=ROOT, check=True)
    subprocess.run([str(runtime), "examples/hello.py"], cwd=ROOT, check=True)
    return 0


def main() -> int:
    if "--inside" in sys.argv:
        return inside_container()

    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is not installed")
    subprocess.run([docker, "build", "-t", IMAGE, "."], cwd=ROOT, check=True)
    return subprocess.call([
        docker, "run", "--rm", "-v", f"{ROOT}:/jetos", "-w", "/jetos",
        IMAGE, "python", "tools/docker_hello.py", "--inside",
    ], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
