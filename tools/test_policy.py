#!/usr/bin/env python3
"""Repository policy tests for JETOS-owned Python code."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TOP_LEVEL = {"jetos"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
FORBIDDEN_TRACKED_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                found.add(node.module.split(".", 1)[0])
    return found


def main() -> int:
    files = tracked_files()
    checks = 0

    forbidden = sorted(
        path.relative_to(ROOT).as_posix()
        for path in files
        if path.name in FORBIDDEN_TRACKED_NAMES
    )
    if forbidden:
        raise AssertionError(
            "third-party Python dependency manifests are forbidden: "
            + ", ".join(forbidden)
        )
    checks += 1

    violations: list[str] = []
    python_files = [path for path in files if path.suffix == ".py"]
    for path in python_files:
        for module in sorted(imports_for(path)):
            if module in STDLIB or module in LOCAL_TOP_LEVEL:
                continue
            violations.append(
                f"{path.relative_to(ROOT)} imports non-stdlib module {module!r}"
            )
    if violations:
        raise AssertionError("\n".join(violations))
    checks += len(python_files)

    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    if not docker.startswith("FROM python:3.14.8-slim\n"):
        raise AssertionError("Docker development Python must be pinned to 3.14.8 stable")
    checks += 1

    language = (ROOT / "tools/language.py").read_text(encoding="utf-8")
    if 'UPSTREAM_VERSION = "3.14.8"' not in language:
        raise AssertionError("JETOS Language is not pinned to Python 3.14.8 stable")
    if "3.16.0a" in language or "main" in language.split("UPSTREAM_VERSION", 1)[0]:
        raise AssertionError("JETOS Language must not pin a pre-release/main Python base")
    checks += 1

    print(
        f"JETOS policy: {checks} checks passed; "
        f"{len(python_files)} Python files are standard-library/JETOS-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
