#!/usr/bin/env python3
"""JETOS Docker/Fat-mode contract checks.

JETOS uses the Docker CLI directly from Python. There is intentionally no
Docker SDK dependency and absolutely no GitHub Actions dependency. Jenkins may
schedule the same repository-owned command, but does not own the test logic.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
JENKINSFILE = ROOT / "Jenkinsfile"
PYTHON_IMAGE = "python:3.14.8-slim"
TEST_IMAGE = "jetos:fat-test"
DEV_IMAGE = "jetos:dev"
TEST_TARGET = "test"
DEV_TARGET = "dev"


def assert_contract() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    required_dockerfile = (
        f"ARG PYTHON_IMAGE={PYTHON_IMAGE}",
        "FROM ${PYTHON_IMAGE} AS base",
        "ENV CC=cc",
        "FROM base AS test",
        "RUN python tools/container_os_qualify.py --phase build --require-toolchain",
        "RUN python jetos.py test",
        'CMD ["python", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]',
        "FROM base AS dev",
    )
    missing = [item for item in required_dockerfile if item not in dockerfile]
    if missing:
        raise AssertionError(
            "Dockerfile is missing required JETOS contract entries: "
            + ", ".join(missing)
        )

    forbidden = (
        ".github/workflows",
        "python:3.13",
        "python:3.12",
        "npm ",
        "node ",
    )
    present = [item for item in forbidden if item in dockerfile]
    if present:
        raise AssertionError(
            "Dockerfile contains stale/forbidden material: " + ", ".join(present)
        )

    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    required_ignores = {".git", ".build", "vendor/linux", "vendor/cpython"}
    missing_ignores = sorted(required_ignores.difference(dockerignore))
    if missing_ignores:
        raise AssertionError(
            ".dockerignore is missing required entries: " + ", ".join(missing_ignores)
        )

    if not JENKINSFILE.is_file():
        raise AssertionError("Jenkinsfile is required for Git-triggered Docker qualification")
    jenkins = JENKINSFILE.read_text(encoding="utf-8")
    if "python3 jetos.py docker-test" not in jenkins:
        raise AssertionError(
            "Jenkins must invoke the repository-owned `python3 jetos.py docker-test` contract"
        )
    if ".github/workflows" in jenkins:
        raise AssertionError("Jenkinsfile must not depend on GitHub Actions")


def main() -> int:
    assert_contract()
    print(
        "JETOS Docker contract: PASS "
        f"({PYTHON_IMAGE}; targets={TEST_TARGET},{DEV_TARGET}; scheduler=Jenkins-compatible)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
