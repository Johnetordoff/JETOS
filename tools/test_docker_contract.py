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
spec_loader = SPEC.loader
spec_loader.exec_module(contract)


def main() -> int:
    contract.assert_contract()

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "qemu-system-arm" in dockerfile
    assert "qemu-system-x86" in dockerfile
    assert "qemu-system-aarch64" in dockerfile
    assert "strace" in dockerfile
    assert "ENV CC=cc" in dockerfile
    assert "command -v qemu-system-aarch64" in dockerfile
    assert "command -v cc" in dockerfile
    assert "command -v make" in dockerfile
    assert "libgdbm-dev" in dockerfile
    assert "libgdbm-compat-dev" in dockerfile
    assert "tk-dev" in dockerfile
    assert "tools/container_os_qualify.py --phase build --require-toolchain" in dockerfile
    assert 'CMD ["python", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]' in dockerfile
    assert 'CMD ["python", "jetos.py", "doctor"]' in dockerfile
    assert "VOLUME [\"/jetos/.build\"]" in dockerfile

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "source-brain/linux" in dockerignore
    assert "source-brain/cpython" in dockerignore
    assert "vendor/linux" not in dockerignore
    assert "vendor/cpython" not in dockerignore

    entrypoint = (ROOT / "jetos.py").read_text(encoding="utf-8")
    assert 'sub.add_parser(' in entrypoint
    assert '"docker-test"' in entrypoint
    assert '"--target", TEST_TARGET' in entrypoint
    assert '"--target", DEV_TARGET' in entrypoint
    assert 'docker, "info", "--format", "{{.ServerVersion}}"' in entrypoint
    assert '"source-brain/linux": "Makefile"' in entrypoint
    assert '"source-brain/cpython": "Python/sysmodule.c"' in entrypoint
    assert '"submodule"' in entrypoint
    assert '"--init"' in entrypoint
    assert 'ensure_dev_sources()' in entrypoint
    assert 'sys.stdin.isatty() and sys.stdout.isatty()' in entrypoint
    assert 'def apple_silicon_docker_platform()' in entrypoint
    assert 'return "linux/arm64"' in entrypoint
    assert 'Docker platform: {docker_platform} (Apple Silicon native)' in entrypoint
    assert 'build_command.extend(["--platform", docker_platform])' in entrypoint
    assert 'run_command.extend(["--platform", docker_platform])' in entrypoint
    assert 'command.extend(["--platform", docker_platform])' in entrypoint

    dev = (ROOT / "tools/dev.py").read_text(encoding="utf-8")
    assert 'BUILD_REVISION = BUILD / ".jetos-build-revision"' in dev
    assert '["git", "rev-parse", "HEAD"]' in dev
    assert 'def clear_build_directory()' in dev
    assert 'for child in BUILD.iterdir()' in dev
    assert 'shutil.rmtree(BUILD)' not in dev
    assert 'def prepare_revision_build()' in dev
    assert 'clear_build_directory()' in dev
    assert 'JETOS source copy complete: {name}' in dev
    assert 'revision = prepare_revision_build()' in dev
    assert 'print(f"  JetOS revision: {revision}")' in dev

    qualifier = (ROOT / "tools/container_os_qualify.py").read_text(encoding="utf-8")
    assert '"c_compiler": os.environ.get("CC", "cc")' in qualifier
    assert '"kernel_model": "shared host Linux kernel"' in qualifier
    assert 'phase == "runtime" and os.getpid() != 1' in qualifier

    jenkins = (ROOT / "Jenkinsfile").read_text(encoding="utf-8")
    assert "python3 tools/work_server.py run-cycle" in jenkins
    assert "python3 jetos.py docker-test" not in jenkins
    assert "github/workflows" not in jenkins.lower()

    work_server = (ROOT / "tools/work_server.py").read_text(encoding="utf-8")
    assert '"docker-os-qualification", [python, "jetos.py", "docker-test"]' in work_server
    assert '"fat-build", [python, "jetos.py", "dev", "--build-only"]' in work_server
    assert '".github/workflows/"' in work_server
    assert '"source-brain/linux/"' in work_server
    assert '"source-brain/cpython/"' in work_server

    native_test = (ROOT / "tools/test.py").read_text(encoding="utf-8")
    assert 'C_COMPILER = os.environ.get("CC", "cc")' in native_test
    assert 'run(\n        "gcc"' not in native_test

    print("JETOS Docker contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
