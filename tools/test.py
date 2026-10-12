#!/usr/bin/env python3
"""JETOS repository test driver. JETOS-owned test orchestration stays Python."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
PORT = ROOT / "ports" / "gcc" / "ordered_hash_map_c"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, env=env)


def assert_no_github_actions() -> None:
    """Enforce Developer One MANDATE_004G locally and host-neutrally."""
    workflow_root = ROOT / ".github" / "workflows"
    if not workflow_root.exists():
        return
    files = sorted(path for path in workflow_root.rglob("*") if path.is_file())
    if files:
        relative = ", ".join(str(path.relative_to(ROOT)) for path in files)
        raise AssertionError(
            "GitHub Actions are forbidden by MANDATE_004G_NO_GITHUB_ACTIONS.md: "
            + relative
        )


def build_and_run(name: str, extra_flags: list[str]) -> None:
    BUILD.mkdir(exist_ok=True)
    output = BUILD / name
    run(
        "gcc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        *extra_flags,
        "-I",
        str(PORT),
        str(PORT / "ordered_hash_map.c"),
        str(PORT / "test_ordered_hash_map.c"),
        "-o",
        str(output),
    )
    run(str(output))


def main() -> int:
    assert_no_github_actions()
    run(sys.executable, "-m", "compileall", "-q", "src", "tools")
    run(sys.executable, "tools/test_architectures.py")
    run(sys.executable, "tools/test_package.py")
    run(sys.executable, "tools/test_kernel_codesign_baseline.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    run(
        sys.executable,
        "-c",
        "from jetos.hardware import snapshot; s=snapshot(); assert s['machine']; print('hardware smoke:', s['machine'])",
        env=env,
    )
    build_and_run("ordered_hash_map_test", ["-O2"])
    build_and_run(
        "ordered_hash_map_test_sanitize",
        ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined"],
    )
    print("JETOS test suite: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
