#!/usr/bin/env python3
"""Freeze and materialize JETOS vendored source snapshots.

`freeze` is an explicit maintainer operation that uses the network to refresh
pinned upstream source. Normal JETOS prepare/build/run paths use only
`materialize`, which reads verified source chunks already stored in this repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
MANIFEST = VENDOR / "sources.json"
CHUNK_SIZE = 45 * 1024 * 1024

SOURCES = {
    "linux": {
        "repository": "https://github.com/gregkh/linux.git",
        "commit": "6d15a1029d425b15c59463910ebdccc4afe760d6",
        "version": "6.12.96",
        "license": "GPL-2.0-only",
    },
    "cpython": {
        "repository": "https://github.com/python/cpython.git",
        "commit": "9d22a5334bd5273962adceeb697a1337e9a0ca21",
        "version": "JETOS language 0.1 / CPython ancestor",
        "license": "PSF-2.0",
    },
}


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=check,
        text=True,
        capture_output=capture,
        env=env,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clone_exact(destination: Path, repository: str, commit: str) -> None:
    run(["git", "init", "-q", str(destination)])
    run(["git", "remote", "add", "origin", repository], cwd=destination)
    run(["git", "fetch", "--depth", "1", "origin", commit], cwd=destination)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)
    actual = run(
        ["git", "rev-parse", "HEAD"],
        cwd=destination,
        capture=True,
    ).stdout.strip()
    if actual != commit:
        raise SystemExit(f"pinned source mismatch: wanted {commit}, got {actual}")


def patch_cpython_snapshot(source: Path) -> None:
    run([
        sys.executable,
        str(ROOT / "tools/language.py"),
        "patch",
        str(source),
    ])
    run(["git", "add", "Include/jetos.h", "Python/sysmodule.c"], cwd=source)
    if run(["git", "diff", "--cached", "--quiet"], cwd=source, check=False).returncode == 0:
        return
    upstream_date = run(
        ["git", "show", "-s", "--format=%cI", "HEAD"],
        cwd=source,
        capture=True,
    ).stdout.strip()
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = upstream_date
    env["GIT_COMMITTER_DATE"] = upstream_date
    run(
        [
            "git",
            "-c",
            "user.name=JETOS Bootstrap",
            "-c",
            "user.email=jetos@localhost",
            "commit",
            "-m",
            "Apply frozen JETOS language identity",
        ],
        cwd=source,
        env=env,
    )


def write_archive(source: Path, output: Path) -> None:
    print(f"archiving {source} -> {output}", flush=True)
    process = subprocess.Popen(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=source,
        stdout=subprocess.PIPE,
    )
    if process.stdout is None:
        raise SystemExit("git archive did not provide stdout")
    with lzma.open(output, "wb", preset=9) as compressed:
        shutil.copyfileobj(process.stdout, compressed, length=1024 * 1024)
    process.stdout.close()
    if process.wait() != 0:
        raise SystemExit("git archive failed")


def split_archive(name: str, archive: Path) -> list[dict[str, object]]:
    directory = VENDOR / name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    parts: list[dict[str, object]] = []
    with archive.open("rb") as source:
        index = 0
        while True:
            data = source.read(CHUNK_SIZE)
            if not data:
                break
            filename = f"source.tar.xz.part-{index:03d}"
            path = directory / filename
            path.write_bytes(data)
            parts.append({
                "file": f"{name}/{filename}",
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
            index += 1
    return parts


def freeze() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "format": 1,
        "chunk_size": CHUNK_SIZE,
        "sources": {},
    }
    sources = manifest["sources"]
    assert isinstance(sources, dict)

    with tempfile.TemporaryDirectory(prefix="jetos-vendor-") as temp_name:
        temp = Path(temp_name)
        for name, spec in SOURCES.items():
            checkout = temp / name
            clone_exact(checkout, spec["repository"], spec["commit"])
            if name == "cpython":
                patch_cpython_snapshot(checkout)
            snapshot_commit = run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                capture=True,
            ).stdout.strip()
            tree_sha = run(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=checkout,
                capture=True,
            ).stdout.strip()
            archive = temp / f"{name}.tar.xz"
            write_archive(checkout, archive)
            parts = split_archive(name, archive)
            sources[name] = {
                "upstream_repository": spec["repository"],
                "upstream_commit": spec["commit"],
                "version": spec["version"],
                "license": spec["license"],
                "snapshot_commit": snapshot_commit,
                "tree_sha": tree_sha,
                "archive_format": "tar.xz",
                "archive_size": archive.stat().st_size,
                "archive_sha256": sha256_file(archive),
                "parts": parts,
                "jetos_patched": name == "cpython",
            }

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verify()
    print(f"wrote {MANIFEST.relative_to(ROOT)}")


def read_manifest() -> dict[str, object]:
    if not MANIFEST.is_file():
        raise SystemExit(
            "vendored source manifest is missing; JETOS builds do not fetch "
            "sources automatically"
        )
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("format") != 1 or not isinstance(data.get("sources"), dict):
        raise SystemExit("unsupported vendored source manifest")
    return data


def source_entry(name: str) -> dict[str, object]:
    sources = read_manifest()["sources"]
    assert isinstance(sources, dict)
    entry = sources.get(name)
    if not isinstance(entry, dict):
        raise SystemExit(f"vendored source is not defined: {name}")
    return entry


def rebuild_archive(name: str, output: Path) -> dict[str, object]:
    entry = source_entry(name)
    parts = entry.get("parts")
    if not isinstance(parts, list) or not parts:
        raise SystemExit(f"vendored source has no parts: {name}")
    digest = hashlib.sha256()
    total = 0
    with output.open("wb") as merged:
        for part in parts:
            if not isinstance(part, dict):
                raise SystemExit(f"invalid part record for {name}")
            relative = part.get("file")
            if not isinstance(relative, str):
                raise SystemExit(f"invalid part path for {name}")
            path = VENDOR / relative
            if not path.is_file():
                raise SystemExit(f"vendored source part is missing: {path}")
            part_digest = hashlib.sha256()
            part_size = 0
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    merged.write(block)
                    digest.update(block)
                    part_digest.update(block)
                    part_size += len(block)
                    total += len(block)
            if part_size != part.get("size"):
                raise SystemExit(f"size mismatch for {path}")
            if part_digest.hexdigest() != part.get("sha256"):
                raise SystemExit(f"hash mismatch for {path}")
    if total != entry.get("archive_size"):
        raise SystemExit(f"archive size mismatch for {name}")
    if digest.hexdigest() != entry.get("archive_sha256"):
        raise SystemExit(f"archive hash mismatch for {name}")
    return entry


def verify(name: str | None = None) -> None:
    names = [name] if name else sorted(read_manifest()["sources"])
    with tempfile.TemporaryDirectory(prefix="jetos-verify-") as temp_name:
        temp = Path(temp_name)
        for source_name in names:
            output = temp / f"{source_name}.tar.xz"
            entry = rebuild_archive(source_name, output)
            print(
                f"verified {source_name}: {entry['archive_sha256']} "
                f"({entry['archive_size']} bytes)"
            )


def materialize(name: str, destination: Path) -> None:
    entry = source_entry(name)
    marker_data = {
        "name": name,
        "archive_sha256": entry["archive_sha256"],
        "snapshot_commit": entry["snapshot_commit"],
        "upstream_commit": entry["upstream_commit"],
    }
    marker = destination / ".jetos-vendor.json"
    if marker.is_file():
        try:
            current = json.loads(marker.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = None
        if current == marker_data:
            print(f"vendored {name} already materialized: {destination}")
            return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"jetos-{name}-",
        suffix=".tar.xz",
        dir=destination.parent,
        delete=False,
    ) as temporary:
        archive = Path(temporary.name)
    try:
        rebuild_archive(name, archive)
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True)
        with tarfile.open(archive, "r:xz") as source:
            source.extractall(destination, filter="data")
    finally:
        archive.unlink(missing_ok=True)

    required = {
        "linux": destination / "Makefile",
        "cpython": destination / "Python/sysmodule.c",
    }[name]
    if not required.is_file():
        raise SystemExit(f"vendored {name} materialization is incomplete")
    marker.write_text(
        json.dumps(marker_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"materialized {name}: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="freeze and materialize JETOS vendored source snapshots"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "freeze",
        help="explicit maintainer operation: fetch pinned upstreams and vendor them",
    )
    verify_parser = sub.add_parser("verify", help="verify vendored source chunks")
    verify_parser.add_argument("name", nargs="?", choices=sorted(SOURCES))
    materialize_parser = sub.add_parser(
        "materialize",
        help="offline: reconstruct and extract one vendored source",
    )
    materialize_parser.add_argument("name", choices=sorted(SOURCES))
    materialize_parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    if args.command == "freeze":
        freeze()
    elif args.command == "verify":
        verify(args.name)
    else:
        materialize(args.name, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
