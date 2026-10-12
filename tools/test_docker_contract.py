#!/usr/bin/env python3
"""Tests for the JETOS Docker/Fat-mode contract."""
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
    assert "qemu-system-arm" in dockerfile
    assert "qemu-system-x86" in dockerfile
    assert "strace" in dockerfile
    assert "ENV CC=cc" in dockerfile
    assert "tools/container_os_qualify.py --phase build --require-toolchain" in dockerfile
    assert 'CMD ["python", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]' in dockerfile
    assert 'CMD ["python", "jetos.py", "doctor"]' in dockerfile

    entrypoint = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert 'sub.add_parser(' in entrypoint
    assert '"docker-test"' in entrypoint
    assert '"--target", TEST_TARGET' in entrypoint
    assert '"--target", DEV_TARGET' in entrypoint
    assert 'docker, "info", "--format", "{{.ServerVersion}}"' in entrypoint

    qualifier = (ROOT / "tools/container_os_qualify.py").read_text(encoding="utf-8")
    assert '"c_compiler": os.environ.get("CC", "cc")' in qualifier
    assert '"kernel_model": "shared host Linux kernel"' in qualifier
    assert 'phase == "runtime" and os.getpid() != 1' in qualifier

    jenkins = (ROOT / "Jenkinsfile").read_text(encoding="utf-8")
    assert "python3 jetos.py docker-test" in jenkins
    assert "github/workflows" not in jenkins.lower()

    native_test = (ROOT / "tools/test.py").read_text(encoding="utf-8")
    assert 'C_COMPILER = os.environ.get("CC", "cc")' in native_test
    assert 'run(\n        "gcc"' not in native_test

    print("JETOS Docker contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
