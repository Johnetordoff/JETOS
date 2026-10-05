#!/usr/bin/env python3
"""Materialize and inspect the source trees that make up JETOS.

The JETOS repository is intentionally small, but the operating system is not
500 lines of C.  This tool makes pinned upstream source visible under sources/
so a developer can inspect CPython/JETOS Language, Linux, GCC experiments, and
Raspberry Pi substrate beside the JETOS-owned orchestration code.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


@dataclass(frozen=True)
class SourceSpec:
    name: str
    role: str
    repository: str
    commit: str
    destination: str
    version: str = ""
    jetos_patch: bool = False


SPECS = (
    SourceSpec(
        "jetos-language",
        "runtime / OS control language",
        "https://github.com/python/cpython.git",
        "8e6e75d9102e39bed2a2b279203a396741180f12",
        "cpython",
        "3.14.8",
        True,
    ),
    SourceSpec(
        "linux",
        "kernel substrate",
        "https://github.com/gregkh/linux.git",
        "6d15a1029d425b15c59463910ebdccc4afe760d6",
        "linux",
        "6.12.96",
    ),
    SourceSpec(
        "gcc",
        "toolchain / C++ migration source",
        "https://github.com/gcc-mirror/gcc.git",
        "4bf11aca586c9eef753b6f76d29ae19e1b505694",
        "gcc",
    ),
    SourceSpec(
        "raspberrypi-linux",
        "Raspberry Pi kernel target",
        "https://github.com/raspberrypi/linux.git",
        "43c132e8863c3bff3647033b6a7d2bf87b15501c",
        "raspberrypi-linux",
    ),
    SourceSpec(
        "raspberrypi-firmware",
        "Raspberry Pi firmware / boot substrate",
        "https://github.com/raspberrypi/firmware.git",
        "cdb0453d483cc220b53b96e24bc6d361fc511733",
        "raspberrypi-firmware",
    ),
)

# These are deliberately visible gaps.  Current builds obtain these native
# libraries from the Linux/Docker build environment rather than from a pinned,
# materialized source tree.  A source-complete JETOS must close these gaps.
SOURCE_GAPS = (
    "libc / dynamic loader",
    "Tcl/Tk",
    "X11/display libraries used by the current Tk host path",
    "OpenSSL/crypto libraries used by enabled stdlib modules",
    "zlib/bzip2/lzma compression libraries",
    "SQLite/readline/libffi/uuid native libraries where included",
    "binutils/make and other build-tool sources used to produce native artifacts",
)

TEXT_SUFFIXES = {
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".s", ".S",
    ".rs", ".py", ".sh", ".asm", ".m", ".mm", ".java", ".go", ".zig",
    ".tcl", ".tk", ".pl", ".pm", ".rb", ".lua", ".js", ".ts",
}


def run(args: list[str], *, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=capture)


def destination(spec: SourceSpec) -> Path:
    return SOURCES / spec.destination


def git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        return run(["git", "rev-parse", "HEAD"], cwd=path, capture=True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def sync_one(spec: SourceSpec) -> None:
    target = destination(spec)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "init", str(target)])
        run(["git", "remote", "add", "origin", spec.repository], cwd=target)
        run(["git", "fetch", "--depth", "1", "origin", spec.commit], cwd=target)
        run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=target)
        if spec.jetos_patch:
            run(["git", "switch", "-c", "jetos-language"], cwd=target)
    head = git_head(target)
    if head != spec.commit and not spec.jetos_patch:
        raise SystemExit(f"{spec.name}: expected {spec.commit}, found {head}")
    if spec.jetos_patch:
        # The branch is expected to become dirty/committed relative to upstream;
        # language.py performs the small JETOS-owned CPython modifications.
        run([sys.executable, "tools/language.py", "patch", str(target)])


def sync(names: set[str] | None) -> None:
    chosen = [spec for spec in SPECS if not names or spec.name in names]
    unknown = (names or set()) - {spec.name for spec in SPECS}
    if unknown:
        raise SystemExit("unknown source component(s): " + ", ".join(sorted(unknown)))
    for spec in chosen:
        sync_one(spec)


def status_data() -> dict[str, object]:
    components: list[dict[str, object]] = []
    for spec in SPECS:
        path = destination(spec)
        components.append(
            {
                "name": spec.name,
                "role": spec.role,
                "version": spec.version,
                "repository": spec.repository,
                "pinned_commit": spec.commit,
                "path": str(path.relative_to(ROOT)),
                "present": path.exists(),
                "head": git_head(path),
                "jetos_patch": spec.jetos_patch,
            }
        )
    return {
        "components": components,
        "source_gaps": list(SOURCE_GAPS),
        "source_complete": not SOURCE_GAPS,
    }


def print_status() -> None:
    data = status_data()
    print("JETOS source tree")
    for item in data["components"]:
        assert isinstance(item, dict)
        mark = "present" if item["present"] else "missing"
        version = f" {item['version']}" if item["version"] else ""
        print(f"  {item['name']}{version}: {mark} -> {item['path']}")
        print(f"    {item['role']}")
        print(f"    pin {item['pinned_commit']}")
    print("\nKnown source-completeness gaps:")
    for gap in data["source_gaps"]:
        print(f"  - {gap}")
    print("\nsource-complete: NO" if data["source_gaps"] else "\nsource-complete: YES")


def iter_source_files(paths: list[Path]):
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix in TEXT_SUFFIXES:
                yield path


def line_census(include_jetos: bool = True) -> dict[str, dict[str, int]]:
    roots = [destination(spec) for spec in SPECS if destination(spec).exists()]
    if include_jetos:
        roots.extend((ROOT / "src", ROOT / "tools"))
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path in iter_source_files(roots):
        suffix = path.suffix or "[no extension]"
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        counts[suffix][0] += 1
        counts[suffix][1] += len(lines)
    return {
        suffix: {"files": values[0], "physical_lines": values[1]}
        for suffix, values in sorted(counts.items(), key=lambda item: (-item[1][1], item[0]))
    }


def print_lines(as_json: bool) -> None:
    data = line_census()
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=False))
        return
    if not any(destination(spec).exists() for spec in SPECS):
        print("No upstream source trees are materialized yet.")
        print("Run: python jetos.py sources sync")
        return
    print("JETOS + materialized upstream source lines by extension")
    print(f"{'extension':<12} {'files':>10} {'physical lines':>16}")
    print("-" * 40)
    for suffix, metric in data.items():
        print(f"{suffix:<12} {metric['files']:>10,} {metric['physical_lines']:>16,}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize/inspect the full JETOS source tree")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="clone pinned upstream sources into sources/")
    sync_parser.add_argument("components", nargs="*")
    sub.add_parser("status", help="show visible source trees and unresolved source gaps")
    lines = sub.add_parser("lines", help="count source lines by extension across visible source trees")
    lines.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "sync":
        sync(set(args.components) if args.components else None)
    elif args.command == "status":
        print_status()
    elif args.command == "lines":
        print_lines(args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
