#!/usr/bin/env python3
"""JETOS optional Docker/Fat-mode harness contract checks.

JetOS is its own source-built Linux distribution. Docker is optional external
build/test machinery and must not select Debian, Gentoo, Python, or any other
distribution as the JetOS substrate. A caller-supplied bootstrap image may be
used only to provide already-installed build capabilities.

The JetOS runtime is built from the vendored source/linux and source/cpython
lineages by tools/dev.py. A bootstrap image/interpreter must never define the
guest runtime.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
JENKINSFILE = ROOT / "Jenkinsfile"
TEST_IMAGE = "jetos:fat-test"
DEV_IMAGE = "jetos:dev"
TEST_TARGET = "test"
DEV_TARGET = "dev"


def assert_contract() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    required_dockerfile = (
        "ARG JETOS_BOOTSTRAP_IMAGE",
        "FROM ${JETOS_BOOTSTRAP_IMAGE} AS base",
        "JETOS_BOOTSTRAP_PYTHON=/usr/bin/python3",
        "command -v python3",
        "command -v cc",
        "command -v make",
        "command -v ld",
        "command -v qemu-system-x86_64",
        "command -v qemu-system-arm",
        "command -v qemu-system-aarch64",
        "FROM base AS test",
        "RUN python3 tools/container_os_qualify.py --phase build --require-toolchain",
        "RUN python3 jetos.py test",
        "FROM base AS dev",
    )
    missing = [item for item in required_dockerfile if item not in dockerfile]
    if missing:
        raise AssertionError(
            "Dockerfile is missing required distro-neutral harness entries: "
            + ", ".join(missing)
        )

    forbidden = (
        "FROM python:",
        "ARG PYTHON_IMAGE=",
        "python:3.14.8-slim",
        "debian:",
        "gentoo:",
        "ubuntu:",
        "alpine:",
        "apt-get",
        "emerge ",
        "apk ",
        "dnf ",
        "yum ",
        ".github/workflows",
        "npm ",
        "node ",
    )
    present = [item for item in forbidden if item in dockerfile]
    if present:
        raise AssertionError(
            "Dockerfile selects a forbidden distribution/package substrate: "
            + ", ".join(present)
        )

    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    required_ignores = {".git", ".build", "source/linux", "source/cpython"}
    missing_ignores = sorted(required_ignores.difference(dockerignore))
    if missing_ignores:
        raise AssertionError(
            ".dockerignore is missing required entries: " + ", ".join(missing_ignores)
        )

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    source_runtime_contract = (
        'SOURCE_LINUX = SOURCE / "linux"',
        'SOURCE_CPYTHON = SOURCE / "cpython"',
        "def build_language()",
        "runtime, stdlib = build_language()",
        '"--python", str(runtime)',
        '"--stdlib", str(stdlib)',
    )
    missing_runtime = [item for item in source_runtime_contract if item not in dev]
    if missing_runtime:
        raise AssertionError(
            "JetOS build is not demonstrably packaging its vendored source-built runtime: "
            + ", ".join(missing_runtime)
        )

    if not JENKINSFILE.is_file():
        raise AssertionError("Jenkinsfile is required for Git-triggered JETOS qualification")
    jenkins = JENKINSFILE.read_text(encoding="utf-8")
    if "python3 tools/work_server.py run-cycle" not in jenkins:
        raise AssertionError("Jenkins must invoke the repository-owned JETOS Work Server cycle")
    if ".github/workflows" in jenkins:
        raise AssertionError("Jenkinsfile must not depend on GitHub Actions")


def main() -> int:
    assert_contract()
    print(
        "JETOS Docker contract: PASS "
        "(external bootstrap only; no distribution base; JetOS runtime source-built)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
