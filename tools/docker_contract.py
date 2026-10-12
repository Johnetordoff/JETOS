#!/usr/bin/env python3
"""JETOS Docker/Fat-mode contract checks.

JETOS uses the Docker CLI directly from Python.  There is intentionally no
Docker SDK dependency and no hosted CI dependency.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
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
        "FROM base AS test",
        "RUN python jetos.py test",
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


def main() -> int:
    assert_contract()
    print(
        "JETOS Docker contract: PASS "
        f"({PYTHON_IMAGE}; targets={TEST_TARGET},{DEV_TARGET})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
