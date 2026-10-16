#!/usr/bin/env python3
"""Offline tests for the JetLang Python integration-backlog verifier."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_behind_a_log",
    ROOT / "tools" / "verify_behind_a_log.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0
    check(mod.version_tuple("3.15.0") == (3, 15, 0), "version tuple")
    check("1 feature series behind" in mod.drift_description("3.14.8", "3.15.0", "feature"), "python series drift")
    checks += 2

    py = mod.python_state(
        "<li>Python 3.14.8</li><li>Python 3.15.0</li><li>Python 3.16.0a1</li>"
    )
    check(py["stable"] == "3.15.0", "python stable parse ignores preview")
    checks += 1

    original_docs = mod.DOCS
    original_python = mod.PYTHON_LOG
    try:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            mod.DOCS = docs
            mod.PYTHON_LOG = docs / "Behind a Log of Python.md"
            pins = {"python_version": "3.14.8", "python_commit": "python-pin"}
            checked = "2026-10-16T14:00:00+00:00"
            mod.write_log(pins, py, checked)
            first = mod.PYTHON_LOG.read_text(encoding="utf-8")
            mod.write_log(pins, py, checked)
            second = mod.PYTHON_LOG.read_text(encoding="utf-8")
            check(first == second, "python history idempotent")
            check("python:3.14.8:3.15.0" in first, "python fingerprint")
            checks += 2
    finally:
        mod.DOCS = original_docs
        mod.PYTHON_LOG = original_python

    source = (ROOT / "tools/verify_behind_a_log.py").read_text(encoding="utf-8")
    check("KERNEL_RELEASES" not in source, "kernel drift tracking retired")
    check("GENTOO_LOG" not in source, "gentoo rolling log retired")
    checks += 2

    print("JETOS Python Behind-a-Log verifier: %d checks passed" % checks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
