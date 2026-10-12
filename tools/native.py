#!/usr/bin/env python3
"""Build JETOS-owned CPython C extensions without a third-party build stack."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native/jetos_native.c"


def runtime_config(python: Path | None = None) -> dict[str, str]:
    if python is None or python.resolve() == Path(sys.executable).resolve():
        return {
            "cc": str(sysconfig.get_config_var("CC") or "cc"),
            "include": str(sysconfig.get_path("include") or ""),
            "ext_suffix": str(sysconfig.get_config_var("EXT_SUFFIX") or ""),
            "platform": sys.platform,
        }
    program = (
        "import json,sys,sysconfig;"
        "print(json.dumps({'cc':sysconfig.get_config_var('CC') or 'cc',"
        "'include':sysconfig.get_path('include') or '',"
        "'ext_suffix':sysconfig.get_config_var('EXT_SUFFIX') or '',"
        "'platform':sys.platform}))"
    )
    result = subprocess.run(
        [str(python), "-c", program],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def build(output_dir: Path, python: Path | None = None) -> Path:
    config = runtime_config(python)
    include = config["include"]
    suffix = config["ext_suffix"]
    if not include:
        raise SystemExit("selected JETOS Language runtime has no C include directory")
    if not suffix:
        raise SystemExit("selected JETOS Language runtime has no extension suffix")
    if not SOURCE.is_file():
        raise SystemExit(f"native source missing: {SOURCE}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"_jetos_native{suffix}"
    cc = os.environ.get("CC") or config["cc"] or "cc"
    command = [
        *shlex.split(cc),
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
    if config["platform"] == "darwin":
        command.extend(["-undefined", "dynamic_lookup"])
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
        help="directory that receives _jetos_native for the selected CPython ABI",
    )
    parser.add_argument(
        "--python",
        type=Path,
        help="JETOS Language runtime whose ABI/sysconfig should be targeted",
    )
    args = parser.parse_args()
    build(args.output_dir, args.python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
