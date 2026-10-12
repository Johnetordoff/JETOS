#!/usr/bin/env python3
"""Measure the normal Python stdlib paths targeted by JETOS kernel co-design.

This is intentionally a baseline harness, not a claim that any JETOS kernel
fast path exists yet.  Run it on Fat JETOS before and after each native/kernel
experiment and on the HC1 when a physical image is available.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - non-POSIX portability
    resource = None


Result = dict[str, Any]


def _context_switches() -> int | None:
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_nvcsw + usage.ru_nivcsw)


def _measure(name: str, iterations: int, operation: Callable[[], None]) -> Result:
    before_switches = _context_switches()
    start = time.perf_counter_ns()
    for _ in range(iterations):
        operation()
    elapsed_ns = time.perf_counter_ns() - start
    after_switches = _context_switches()
    result: Result = {
        "name": name,
        "status": "PASS",
        "iterations": iterations,
        "elapsed_ns": elapsed_ns,
        "ns_per_iteration": elapsed_ns / iterations,
    }
    if before_switches is not None and after_switches is not None:
        result["context_switches"] = after_switches - before_switches
    return result


def benchmark_spawn(iterations: int) -> Result:
    def operation() -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-c", "pass"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"child exited {completed.returncode}")

    return _measure("jet_spawn/subprocess", iterations, operation)


def benchmark_copy(iterations: int, copy_bytes: int) -> Result:
    with tempfile.TemporaryDirectory(prefix="jetos-copy-") as temp:
        root = Path(temp)
        source = root / "source.bin"
        destination = root / "destination.bin"
        chunk = bytes(range(256)) * 4096
        remaining = copy_bytes
        with source.open("wb") as stream:
            while remaining:
                part = chunk[: min(len(chunk), remaining)]
                stream.write(part)
                remaining -= len(part)

        def operation() -> None:
            shutil.copyfile(source, destination)
            if destination.stat().st_size != copy_bytes:
                raise RuntimeError("copy size mismatch")
            destination.unlink()

        result = _measure("jet_copy/shutil.copyfile", iterations, operation)
        result["bytes_per_copy"] = copy_bytes
        return result


def _build_walk_fixture(root: Path) -> int:
    files = 0
    for first in range(8):
        level1 = root / f"d{first:02d}"
        level1.mkdir()
        for second in range(4):
            level2 = level1 / f"d{second:02d}"
            level2.mkdir()
            for item in range(8):
                (level2 / f"f{item:02d}.txt").write_text("jetos\n", encoding="utf-8")
                files += 1
    return files


def benchmark_walk(iterations: int, walk_root: Path | None) -> Result:
    if walk_root is not None:
        root = walk_root
        if not root.is_dir():
            return {
                "name": "jet_walk/os.walk",
                "status": "SKIP",
                "detail": f"walk root is not a directory: {root}",
            }
        fixture = None
        expected_minimum = 0
    else:
        fixture = tempfile.TemporaryDirectory(prefix="jetos-walk-")
        root = Path(fixture.name)
        expected_minimum = _build_walk_fixture(root)

    seen_last = 0

    def operation() -> None:
        nonlocal seen_last
        seen = 0
        for _, _, filenames in os.walk(root):
            seen += len(filenames)
        if seen < expected_minimum:
            raise RuntimeError(f"walk saw {seen}, expected at least {expected_minimum}")
        seen_last = seen

    try:
        result = _measure("jet_walk/os.walk", iterations, operation)
        result["root"] = str(root)
        result["files_seen"] = seen_last
        return result
    finally:
        if fixture is not None:
            fixture.cleanup()


def benchmark_waitset(iterations: int) -> Result:
    left, right = socket.socketpair()
    left.setblocking(False)
    right.setblocking(False)
    selector = selectors.DefaultSelector()
    selector.register(left, selectors.EVENT_READ)

    def operation() -> None:
        right.send(b"x")
        events = selector.select(timeout=1.0)
        if not events:
            raise RuntimeError("selector failed to wake")
        if left.recv(1) != b"x":
            raise RuntimeError("selector payload mismatch")

    try:
        result = _measure("jet_waitset/selectors", iterations, operation)
        result["selector"] = type(selector).__name__
        return result
    finally:
        selector.close()
        left.close()
        right.close()


def benchmark_memregion(iterations: int) -> Result:
    try:
        from multiprocessing import shared_memory
    except ImportError as exc:
        return {
            "name": "jet_memregion/multiprocessing.shared_memory",
            "status": "SKIP",
            "detail": str(exc),
        }

    def operation() -> None:
        region = shared_memory.SharedMemory(create=True, size=4096)
        try:
            region.buf[:5] = b"jetos"
            if bytes(region.buf[:5]) != b"jetos":
                raise RuntimeError("shared-memory round trip failed")
        finally:
            region.close()
            region.unlink()

    return _measure("jet_memregion/multiprocessing.shared_memory", iterations, operation)


def benchmark_temp(iterations: int) -> Result:
    with tempfile.TemporaryDirectory(prefix="jetos-temp-parent-") as parent:
        def operation() -> None:
            fd, name = tempfile.mkstemp(prefix="jetos-", suffix=".tmp", dir=parent)
            os.close(fd)
            os.unlink(name)

        return _measure("jet_temp/tempfile.mkstemp", iterations, operation)


def run_suite(
    *,
    iterations: int,
    copy_bytes: int,
    walk_root: Path | None,
) -> dict[str, Any]:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    if copy_bytes < 1:
        raise ValueError("copy_bytes must be >= 1")

    benchmarks: list[tuple[str, Callable[[], Result]]] = [
        ("spawn", lambda: benchmark_spawn(iterations)),
        ("copy", lambda: benchmark_copy(iterations, copy_bytes)),
        ("walk", lambda: benchmark_walk(iterations, walk_root)),
        ("waitset", lambda: benchmark_waitset(iterations)),
        ("memregion", lambda: benchmark_memregion(iterations)),
        ("temp", lambda: benchmark_temp(iterations)),
    ]

    results: list[Result] = []
    for short_name, benchmark in benchmarks:
        try:
            results.append(benchmark())
        except Exception as exc:  # baseline must report all experiments
            results.append({
                "name": short_name,
                "status": "FAIL",
                "detail": f"{type(exc).__name__}: {exc}",
            })

    return {
        "schema": "jetos.kernel-codesign-baseline.v1",
        "python": sys.version,
        "platform": sys.platform,
        "machine": os.uname().machine if hasattr(os, "uname") else None,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--copy-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument(
        "--walk-root",
        type=Path,
        default=None,
        help="optional real tree to walk; on Fat JETOS use the Linux source tree",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = run_suite(
        iterations=args.iterations,
        copy_bytes=args.copy_bytes,
        walk_root=args.walk_root,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 1 if any(item["status"] == "FAIL" for item in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
