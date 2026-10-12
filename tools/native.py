#!/usr/bin/env python3
"""Build JETOS-owned CPython C extensions without a third-party build stack."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native/jetos_native.c"


def compiler() -> list[str]:
    value = os.environ.get("CC") or sysconfig.get_config_var("CC") or "cc"
    return shlex.split(value)


def extension_name() -> str:
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not suffix:
        raise SystemExit("current JETOS Language runtime has no extension suffix")
    return f"_jetos_native{suffix}"


def build(output_dir: Path) -> Path:
    include = sysconfig.get_path("include")
    if not include:
        raise SystemExit("current JETOS Language runtime has no C include directory")
    if not SOURCE.is_file():
        raise SystemExit(f"native source missing: {SOURCE}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / extension_name()
    command = [
        *compiler(),
        "-O3",
        "-std=c11",
        "-fPIC",
        "-Wall",
        "-Wextra",
        "-I",
        include,
        str(SOURCE),
        "-shared",
        "-o",
        str(output),
    ]
    if sys.platform == "darwin":
        command[1:1] = ["-undefined", "dynamic_lookup"]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)
    print(f"JETOS native extension: {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="build the target-native JETOS C extension")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "src/jetos",
        help="directory that receives _jetos_native for the current CPython ABI",
    )
    args = parser.parse_args()
    build(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
