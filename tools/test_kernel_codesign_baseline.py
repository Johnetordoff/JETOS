#!/usr/bin/env python3
"""Fast checks for the six Python/kernel co-design baseline experiments."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kernel_codesign_baseline",
    ROOT / "tools/kernel_codesign_baseline.py",
)
assert SPEC and SPEC.loader
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    report = baseline.run_suite(iterations=1, copy_bytes=4096, walk_root=None)
    check(report["schema"] == "jetos.kernel-codesign-baseline.v1", "schema")

    results = report["results"]
    check(len(results) == 6, "six experiments required")

    names = {item["name"] for item in results}
    expected_prefixes = {
        "jet_spawn/subprocess",
        "jet_copy/shutil.copyfile",
        "jet_walk/os.walk",
        "jet_waitset/selectors",
        "jet_memregion/multiprocessing.shared_memory",
        "jet_temp/tempfile.mkstemp",
    }
    check(names == expected_prefixes, f"unexpected experiments: {names}")

    failures = [item for item in results if item["status"] == "FAIL"]
    check(not failures, f"baseline failures: {failures}")

    print("JETOS Python/kernel co-design baseline: 6 experiments passed/skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
