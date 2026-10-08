#!/usr/bin/env python3
"""Build and verify JetOS Python from the sealed Gen2 source tree."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=cwd, check=True, text=True)


def require_source(source: Path) -> None:
    required = [source / "Python/sysmodule.c", source / "Include/jetos.h", source / "configure"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("not a complete JetOS Python source tree; missing: " + ", ".join(missing))
    text = (source / "Python/sysmodule.c").read_text(encoding="utf-8")
    if '#define NAME "jetos"' not in text:
        raise SystemExit("JetOS Python source identity is not installed")


def build(source: Path, build_dir: Path, prefix: Path, jobs: int) -> None:
    require_source(source)
    build_dir.mkdir(parents=True, exist_ok=True)
    run([
        str((source / "configure").resolve()),
        f"--prefix={prefix.resolve()}",
        "--with-ensurepip=no",
    ], cwd=build_dir)
    run(["make", f"-j{jobs}"], cwd=build_dir)


def smoke(build_dir: Path) -> None:
    executable = build_dir / "python"
    if not executable.exists():
        raise SystemExit(f"JetOS Python executable not found: {executable}")
    code = (
        "import sys; "
        "assert sys.implementation.name == 'jetos'; "
        "assert not hasattr(sys, 'jetos_python_base_version'); "
        "print('JetOS Python:', sys.version); "
        "print('implementation:', sys.implementation.name)"
    )
    run([str(executable), "-c", code])


def install(build_dir: Path) -> None:
    if not (build_dir / "Makefile").exists():
        raise SystemExit(f"JetOS Python build tree not found: {build_dir}")
    run(["make", "install"], cwd=build_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sealed JetOS Python")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("source", type=Path)
    build_parser.add_argument("--build", type=Path, required=True)
    build_parser.add_argument("--prefix", type=Path, required=True)
    build_parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    smoke_parser = sub.add_parser("smoke")
    smoke_parser.add_argument("--build", type=Path, required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args.source, args.build, args.prefix, args.jobs)
    elif args.command == "smoke":
        smoke(args.build)
    elif args.command == "install":
        install(args.build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
