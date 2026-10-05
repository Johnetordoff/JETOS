#!/usr/bin/env python3
"""Small repeatable benchmarks for JETOS-owned hot-path candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import desktop, dunicode, storage  # noqa: E402


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def ns_per_operation(operation: Callable[[], object], iterations: int, rounds: int) -> int:
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed = time.perf_counter_ns() - start
        samples.append(elapsed / iterations)
    return round(statistics.median(samples))


def benchmark(iterations: int, rounds: int) -> dict[str, object]:
    text = ("JETOS Δ 漢 🧪 Python operating system " * 8).strip()
    encoded = dunicode.encode(text)
    mountinfo = "\n".join(
        (
            "24 22 0:21 / / rw,relatime - rootfs rootfs rw",
            "25 24 0:22 / /tmp rw,nosuid,nodev - tmpfs tmpfs rw",
            "26 24 8:2 / /state rw,relatime - ext4 /dev/mmcblk0p2 rw",
        )
    )
    cases: dict[str, Callable[[], object]] = {
        "dunicode_encode": lambda: dunicode.encode(text),
        "dunicode_decode": lambda: dunicode.decode(encoded),
        "desktop_layout_640x480": lambda: desktop.layout_for(640, 480),
        "desktop_layout_3840x2160": lambda: desktop.layout_for(3840, 2160),
        "storage_parse_mountinfo": lambda: storage.parse_mountinfo(mountinfo),
    }
    results = {
        name: ns_per_operation(operation, iterations, rounds)
        for name, operation in cases.items()
    }
    return {
        "commit": git_head(),
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "iterations_per_round": iterations,
        "rounds": rounds,
        "unit": "median nanoseconds per operation",
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark small JETOS-owned operations")
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1 or args.rounds < 1:
        raise SystemExit("iterations and rounds must be positive")
    data = benchmark(args.iterations, args.rounds)
    rendered = json.dumps(data, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote benchmark: {args.output}")
    if args.json or not args.output:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
