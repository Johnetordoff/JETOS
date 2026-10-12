#!/usr/bin/env python3
"""Fast self-tests for the Python↔OS qualification harness."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_os_qualify",
    ROOT / "tools/os_qualify.py",
)
assert SPEC and SPEC.loader
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


def main() -> int:
    assert len(qualify.PROBES) >= 40
    for required in (
        "filesystem-basic",
        "fd-low-level",
        "links",
        "permissions",
        "process-fork-wait",
        "process-exec",
        "signals",
        "mmap",
        "fcntl-locks",
        "pty-termios",
        "selectors",
        "unix-socket",
        "loopback-network",
        "shared-memory",
        "threads",
        "multiprocessing-fork",
        "proc-sys-dev",
    ):
        assert required in qualify.PROBES, required

    os_surface = qualify.callable_surface("os")
    assert os_surface["import"] == "PASS"
    names = {item["name"] for item in os_surface["callables"]}
    for required in ("open", "stat", "read", "write", "kill"):
        assert required in names, required

    for probe in (
        "filesystem-basic",
        "fd-low-level",
        "links",
        "subprocess",
        "threads",
    ):
        status, detail = qualify.run_probe(probe)
        assert status == "PASS", f"{probe}: {status}: {detail}"

    sample = {
        "modules": {"os": os_surface},
        "probes": {"filesystem-basic": {"status": "PASS", "detail": ""}},
        "noise": "ignored",
    }
    comparable = qualify.comparable(sample)
    assert set(comparable) == {"modules", "probes"}
    assert "noise" not in comparable

    print(
        "JETOS Python/OS qualification harness: "
        f"{len(qualify.PROBES)} capability probes defined"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
