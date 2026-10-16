#!/usr/bin/env python3
"""JETOS Docker/Fat-mode contract checks.

JETOS uses the Docker CLI directly from Python. The host supplies Docker and
Git; compiler, linker, kernel-build, QEMU, and JetLang build dependencies live
inside the repository-owned Docker image. There is intentionally no Docker SDK
or GitHub Actions dependency.

The container Python is a bootstrap/orchestration interpreter only. The JetOS
runtime must be built from the pinned source/cpython lineage by tools/dev.py;
a prebuilt Python Docker image must never define the guest runtime.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
JENKINSFILE = ROOT / "Jenkinsfile"
BASE_IMAGE = "debian:trixie-slim"
TEST_IMAGE = "jetos:fat-test"
DEV_IMAGE = "jetos:dev"
TEST_TARGET = "test"
DEV_TARGET = "dev"


def assert_contract() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    required_dockerfile = (
        f"ARG BASE_IMAGE={BASE_IMAGE}",
        "FROM ${BASE_IMAGE} AS base",
        "python3",
        "JETOS_BOOTSTRAP_PYTHON=/usr/bin/python3",
        "binutils",
        "qemu-system-x86",
        "qemu-system-arm",
        'ENV CC="ccache cc"',
        "FROM base AS test",
        "RUN python3 tools/container_os_qualify.py --phase build --require-toolchain",
        "RUN python3 jetos.py test",
        'CMD ["python3", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]',
        "FROM base AS dev",
        "command -v qemu-system-aarch64",
        "command -v ld",
    )
    missing = [item for item in required_dockerfile if item not in dockerfile]
    if missing:
        raise AssertionError(
            "Dockerfile is missing required JETOS build dependencies/contract entries: "
            + ", ".join(missing)
        )

    forbidden = (
        "FROM python:",
        "ARG PYTHON_IMAGE=",
        "python:3.14.8-slim",
        "python:3.13",
        "python:3.12",
        ".github/workflows",
        "npm ",
        "node ",
    )
    present = [item for item in forbidden if item in dockerfile]
    if present:
        raise AssertionError(
            "Dockerfile contains stale/forbidden material: " + ", ".join(present)
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
        'SOURCE_CPYTHON = SOURCE / "cpython"',
        "def build_language()",
        "runtime, stdlib = build_language()",
        '"--python", str(runtime)',
        '"--stdlib", str(stdlib)',
    )
    missing_runtime = [item for item in source_runtime_contract if item not in dev]
    if missing_runtime:
        raise AssertionError(
            "JetOS Fat build is not demonstrably packaging the source-built "
            "JetLang runtime: " + ", ".join(missing_runtime)
        )

    if not JENKINSFILE.is_file():
        raise AssertionError("Jenkinsfile is required for Git-triggered JETOS qualification")
    jenkins = JENKINSFILE.read_text(encoding="utf-8")
    if "python3 tools/work_server.py run-cycle" not in jenkins:
        raise AssertionError("Jenkins must invoke the repository-owned JETOS Work Server cycle")
    if "jetos.py docker-test" in jenkins:
        raise AssertionError("Jenkins must not duplicate the Work Server's Docker qualification policy")
    if ".github/workflows" in jenkins:
        raise AssertionError("Jenkinsfile must not depend on GitHub Actions")


def main() -> int:
    assert_contract()
    print(
        "JETOS Docker contract: PASS "
        f"({BASE_IMAGE}; bootstrap-python=build-only; "
        f"targets={TEST_TARGET},{DEV_TARGET}; build-deps=container-owned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
