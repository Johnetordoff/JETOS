#!/usr/bin/env python3
"""Absorb Source Brain submodules into the single outer JETOS repository.

This is an explicit one-time migration tool. It snapshots the currently pinned
Linux and CPython/JetLang source working trees, strips nested Git metadata,
replaces the gitlinks with normal tracked directories, records provenance, and
removes stale submodule metadata.

Run from a clean checkout whose submodules are initialized at their recorded
gitlink revisions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BRAIN = ROOT / "source-brain"
TARGETS = {
    "linux": SOURCE_BRAIN / "linux",
    "cpython": SOURCE_BRAIN / "cpython",
}
PROVENANCE = SOURCE_BRAIN / "UPSTREAM_PROVENANCE.json"


def run(*args: str, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def output(*args: str, cwd: Path = ROOT) -> str:
    return run(*args, cwd=cwd, capture=True).stdout.strip()


def require_clean_checkout() -> None:
    dirty = output("git", "status", "--porcelain")
    if dirty:
        raise SystemExit(
            "Refusing unified-source migration from a dirty checkout. "
            "Commit/stash current work first."
        )


def gitlink_sha(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    entry = output("git", "ls-files", "-s", "--", rel)
    if not entry:
        raise SystemExit(f"{rel} is not recorded in the outer repository")
    mode, sha, _stage_path = entry.split(maxsplit=2)
    if mode != "160000":
        raise SystemExit(f"{rel} is already not a gitlink (mode {mode})")
    return sha


def submodule_head(path: Path) -> str:
    return output("git", "-C", str(path), "rev-parse", "HEAD")


def submodule_url(name: str) -> str:
    return output(
        "git",
        "config",
        "-f",
        str(ROOT / ".gitmodules"),
        "--get",
        f"submodule.source-brain/{name}.url",
    )


def require_initialized_exact_sources() -> dict[str, dict[str, str]]:
    if not (ROOT / ".gitmodules").is_file():
        raise SystemExit(".gitmodules is missing; expected the pre-migration checkout")

    records: dict[str, dict[str, str]] = {}
    required = {
        "linux": "Makefile",
        "cpython": "Python/sysmodule.c",
    }
    for name, path in TARGETS.items():
        if not (path / required[name]).is_file():
            raise SystemExit(
                f"{path.relative_to(ROOT)} is not initialized; run "
                "`git submodule update --init source-brain/linux source-brain/cpython` first"
            )
        expected = gitlink_sha(path)
        actual = submodule_head(path)
        if actual != expected:
            raise SystemExit(
                f"{path.relative_to(ROOT)} HEAD {actual} does not match "
                f"outer gitlink {expected}"
            )
        records[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "upstream_url": submodule_url(name),
            "upstream_commit": expected,
        }
    return records


def copy_without_git(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )


def nested_git_metadata(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob(".git"):
        found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def remove_submodule_admin_metadata() -> None:
    modules_root = ROOT / ".git" / "modules" / "source-brain"
    for name in TARGETS:
        stale = modules_root / name
        if stale.exists():
            if stale.is_dir():
                shutil.rmtree(stale)
            else:
                stale.unlink()
    if modules_root.is_dir() and not any(modules_root.iterdir()):
        modules_root.rmdir()


def migrate(commit: bool) -> None:
    require_clean_checkout()
    records = require_initialized_exact_sources()

    with tempfile.TemporaryDirectory(prefix="jetos-unified-source-") as temp:
        temp_root = Path(temp)
        snapshots: dict[str, Path] = {}
        for name, source in TARGETS.items():
            snapshot = temp_root / name
            print(f"snapshot {source.relative_to(ROOT)} -> {snapshot}")
            copy_without_git(source, snapshot)
            snapshots[name] = snapshot

        run(
            "git",
            "rm",
            "-f",
            ".gitmodules",
            "source-brain/linux",
            "source-brain/cpython",
        )

        for name, destination in TARGETS.items():
            print(f"absorb {name} into outer repository")
            copy_without_git(snapshots[name], destination)

    provenance = {
        "schema_version": 1,
        "architecture": "single-outer-git-repository",
        "jetlang_identity": "CPython-derived improved JetLang runtime",
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": records,
    }
    PROVENANCE.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    nested = nested_git_metadata(SOURCE_BRAIN)
    if nested:
        raise SystemExit("Nested Git metadata remains: " + ", ".join(nested))

    run(
        "git",
        "add",
        "source-brain/linux",
        "source-brain/cpython",
        str(PROVENANCE.relative_to(ROOT)),
    )
    remove_submodule_admin_metadata()

    staged = output("git", "diff", "--cached", "--stat")
    print(staged)
    print("\nUnified-source invariants staged:")
    print("  .gitmodules removed")
    print("  source-brain/linux is ordinary tracked content")
    print("  source-brain/cpython is ordinary tracked content")
    print("  nested .git metadata absent")
    print(f"  provenance recorded in {PROVENANCE.relative_to(ROOT)}")

    if commit:
        run(
            "git",
            "commit",
            "-m",
            "Absorb Linux and CPython sources into unified JetOS repository",
        )
        print("migration committed")
    else:
        print("migration is staged but not committed; inspect and qualify before commit")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="commit the staged unified-source migration after validation",
    )
    args = parser.parse_args()
    migrate(args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
