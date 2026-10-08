#!/usr/bin/env python3
"""Repository policy tests for JETOS-owned Python and Gen2 identity."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TOP_LEVEL = {"jetos"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
FORBIDDEN_TRACKED_NAMES = {
    "requirements.txt", "requirements-dev.txt", "Pipfile", "poetry.lock", "uv.lock",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, text=True, capture_output=True)
    return [ROOT / line for line in result.stdout.splitlines() if line]


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            found.add(node.module.split(".", 1)[0])
    return found


def main() -> int:
    files = tracked_files()
    checks = 0
    forbidden = sorted(
        path.relative_to(ROOT).as_posix() for path in files
        if path.name in FORBIDDEN_TRACKED_NAMES
    )
    if forbidden:
        raise AssertionError("third-party Python dependency manifests are forbidden: " + ", ".join(forbidden))
    checks += 1

    violations: list[str] = []
    python_files = [path for path in files if path.suffix == ".py"]
    for path in python_files:
        for module in sorted(imports_for(path)):
            if module not in STDLIB and module not in LOCAL_TOP_LEVEL:
                violations.append(f"{path.relative_to(ROOT)} imports non-stdlib module {module!r}")
    if violations:
        raise AssertionError("\n".join(violations))
    checks += len(python_files)

    constitution = (ROOT / "JETOS_CONSTITUTION.txt").read_text(encoding="utf-8")
    if "A JETOS generation is a frozen source generation" not in constitution:
        raise AssertionError("JETOS policy must define frozen generations")
    if "JetOS Python" not in constitution:
        raise AssertionError("JetOS Python must be the active runtime identity")
    checks += 2

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    if "github.com" in dev or "python_release.py" in dev or "tools/sources.py" in dev:
        raise AssertionError("sealed Gen2 build path must not perform live source/freshness checks")
    checks += 1

    print(
        f"JETOS Gen2 policy: {checks} checks passed; "
        f"{len(python_files)} tracked Python files are standard-library/JETOS-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
