#!/usr/bin/env python3
"""Tests for the JETOS distro-neutral optional Docker harness."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_docker_contract",
    ROOT / "tools/docker_contract.py",
)
assert SPEC and SPEC.loader
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def main() -> int:
    contract.assert_contract()

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG JETOS_BOOTSTRAP_IMAGE" in dockerfile
    assert "FROM ${JETOS_BOOTSTRAP_IMAGE} AS base" in dockerfile
    for forbidden in (
        "debian:", "gentoo:", "ubuntu:", "alpine:", "FROM python:",
        "apt-get", "emerge ", "apk ", "dnf ", "yum ",
    ):
        assert forbidden not in dockerfile
    assert "JETOS_BOOTSTRAP_PYTHON=/usr/bin/python3" in dockerfile
    assert "command -v python3" in dockerfile
    assert "command -v qemu-system-arm" in dockerfile
    assert "command -v qemu-system-aarch64" in dockerfile
    assert "command -v qemu-system-x86_64" in dockerfile
    assert 'CMD ["python3", "jetos.py", "doctor"]' in dockerfile

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'SOURCE_LINUX = SOURCE / "linux"' in dev
    assert 'SOURCE_CPYTHON = SOURCE / "cpython"' in dev
    assert 'copy_source("Linux", SOURCE_LINUX' in dev
    assert 'copy_source("JetLang/CPython", SOURCE_CPYTHON' in dev
    assert 'runtime, stdlib = build_language()' in dev
    assert '"--python", str(runtime)' in dev
    assert '"--stdlib", str(stdlib)' in dev

    entrypoint = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert "JETOS_BOOTSTRAP_IMAGE" in entrypoint
    assert '"--build-arg"' in entrypoint

    print("JETOS distro-neutral Docker contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
