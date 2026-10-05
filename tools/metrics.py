#!/usr/bin/env python3
"""Measure JETOS source size, language mix, and Python annotation coverage."""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
JETOS_OWNED_PREFIXES = ("src/", "tools/")
SOURCE_SUFFIXES = {
    ".py": "python",
    ".c": "c",
    ".h": "c_header",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp_header",
    ".hh": "cpp_header",
    ".s": "assembly",
    ".S": "assembly",
}


@dataclass(frozen=True)
class LanguageMetric:
    files: int = 0
    physical_lines: int = 0
    nonblank_lines: int = 0


@dataclass(frozen=True)
class TypeMetric:
    functions: int
    fully_annotated_functions: int
    coverage_percent: float


def tracked_paths() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return tuple(ROOT / value for value in result.stdout.splitlines() if value)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_jetos_owned(path: Path) -> bool:
    name = relative(path)
    return name.startswith(JETOS_OWNED_PREFIXES)


def text_lines(path: Path) -> tuple[int, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0, 0
    lines = text.splitlines()
    return len(lines), sum(bool(line.strip()) for line in lines)


def language_metrics(paths: Iterable[Path]) -> dict[str, LanguageMetric]:
    raw: dict[str, list[int]] = {}
    for path in paths:
        kind = SOURCE_SUFFIXES.get(path.suffix)
        if kind is None or not path.is_file():
            continue
        physical, nonblank = text_lines(path)
        current = raw.setdefault(kind, [0, 0, 0])
        current[0] += 1
        current[1] += physical
        current[2] += nonblank
    return {
        name: LanguageMetric(files=values[0], physical_lines=values[1], nonblank_lines=values[2])
        for name, values in sorted(raw.items())
    }


def _function_fully_annotated(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    parameters = [*positional, *node.args.kwonlyargs]
    if node.args.vararg is not None:
        parameters.append(node.args.vararg)
    if node.args.kwarg is not None:
        parameters.append(node.args.kwarg)
    return all(argument.annotation is not None for argument in parameters) and node.returns is not None


def type_metric(paths: Iterable[Path]) -> TypeMetric:
    functions = 0
    fully_annotated = 0
    for path in paths:
        if path.suffix != ".py" or not is_jetos_owned(path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            functions += 1
            fully_annotated += int(_function_fully_annotated(node))
    coverage = 100.0 if functions == 0 else fully_annotated * 100.0 / functions
    return TypeMetric(functions, fully_annotated, round(coverage, 2))


def cpp_debt(paths: Iterable[Path]) -> tuple[str, ...]:
    cpp_suffixes = {".cc", ".cpp", ".cxx", ".hpp", ".hh"}
    return tuple(sorted(relative(path) for path in paths if path.suffix in cpp_suffixes))


def owned_cpp_violations(paths: Iterable[Path]) -> tuple[str, ...]:
    return tuple(path for path in cpp_debt(paths) if path.startswith(JETOS_OWNED_PREFIXES))


def report() -> dict[str, object]:
    paths = tracked_paths()
    owned = tuple(path for path in paths if is_jetos_owned(path))
    all_text_lines = sum(text_lines(path)[0] for path in paths if path.is_file())
    owned_text_lines = sum(text_lines(path)[0] for path in owned if path.is_file())
    return {
        "tracked_files": len(paths),
        "tracked_text_lines": all_text_lines,
        "jetos_owned_files": len(owned),
        "jetos_owned_text_lines": owned_text_lines,
        "languages": {
            key: asdict(value) for key, value in language_metrics(paths).items()
        },
        "type_annotations": asdict(type_metric(paths)),
        "cpp_migration_debt": list(cpp_debt(paths)),
        "owned_cpp_violations": list(owned_cpp_violations(paths)),
    }


def print_human(data: dict[str, object]) -> None:
    print("JETOS source metrics")
    print(f"tracked files: {data['tracked_files']}")
    print(f"tracked text lines: {data['tracked_text_lines']}")
    print(f"JETOS-owned files: {data['jetos_owned_files']}")
    print(f"JETOS-owned text lines: {data['jetos_owned_text_lines']}")
    print("language source:")
    languages = data["languages"]
    assert isinstance(languages, dict)
    for name, metric in languages.items():
        assert isinstance(metric, dict)
        print(
            f"  {name}: {metric['files']} files / "
            f"{metric['physical_lines']} lines / {metric['nonblank_lines']} nonblank"
        )
    types = data["type_annotations"]
    assert isinstance(types, dict)
    print(
        "fully annotated functions: "
        f"{types['fully_annotated_functions']}/{types['functions']} "
        f"({types['coverage_percent']}%)"
    )
    debt = data["cpp_migration_debt"]
    assert isinstance(debt, list)
    print(f"C++ migration-debt files: {len(debt)}")
    violations = data["owned_cpp_violations"]
    assert isinstance(violations, list)
    print(f"new JETOS-owned C++ violations: {len(violations)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure JETOS source/type metrics")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    data = report()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_human(data)
    violations = data["owned_cpp_violations"]
    if args.strict and isinstance(violations, list) and violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
