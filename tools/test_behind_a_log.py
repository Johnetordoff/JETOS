#!/usr/bin/env python3
"""Offline tests for the Behind a Log version-drift verifier."""
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
    check("16 patch release(s) behind" in mod.drift_description("6.12.96", "6.12.112", "kernel"), "kernel patch drift")
    check("1 major-number line(s) behind" in mod.drift_description("6.12.96", "7.2.10", "kernel"), "kernel major drift")
    checks += 4

    kernel = mod.linux_state(
        '{"releases":['
        '{"moniker":"stable","version":"7.2.10","released":{"isodate":"2026-10-11"}},'
        '{"moniker":"longterm","version":"6.12.112","released":{"isodate":"2026-10-03"}}'
        ']}',
        "6.12.96",
    )
    check(kernel["stable"] == "7.2.10", "kernel stable parse")
    check(kernel["same_line"] == "6.12.112", "kernel longterm parse")
    checks += 2

    py = mod.python_state("<li>Python 3.14.8</li><li>Python 3.15.0</li>")
    check(py["stable"] == "3.15.0", "python stable parse")
    checks += 1

    original_docs = mod.DOCS
    original_gentoo = mod.GENTOO_LOG
    original_python = mod.PYTHON_LOG
    try:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            mod.DOCS = docs
            mod.GENTOO_LOG = docs / "Behind a Log of Gentoo.md"
            mod.PYTHON_LOG = docs / "Behind a Log of Python.md"
            pins = {
                "linux_version": "6.12.96",
                "linux_commit": "linux-pin",
                "python_version": "3.14.8",
                "python_commit": "python-pin",
            }
            checked = "2026-10-14T19:00:00+00:00"
            mod.write_logs(pins, kernel, py, checked)
            first_g = mod.GENTOO_LOG.read_text(encoding="utf-8")
            first_p = mod.PYTHON_LOG.read_text(encoding="utf-8")
            mod.write_logs(pins, kernel, py, checked)
            second_g = mod.GENTOO_LOG.read_text(encoding="utf-8")
            second_p = mod.PYTHON_LOG.read_text(encoding="utf-8")
            check(first_g == second_g, "gentoo history idempotent")
            check(first_p == second_p, "python history idempotent")
            check("linux:6.12.96:7.2.10:6.12.112" in first_g, "gentoo fingerprint")
            check("python:3.14.8:3.15.0" in first_p, "python fingerprint")
            checks += 4
    finally:
        mod.DOCS = original_docs
        mod.GENTOO_LOG = original_gentoo
        mod.PYTHON_LOG = original_python

    print("JETOS Behind a Log verifier: %d checks passed" % checks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
