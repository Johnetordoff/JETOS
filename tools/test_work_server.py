#!/usr/bin/env python3
"""Repository-local tests for the JETOS Work Server.

These tests exercise real Git worktrees/branches but replace expensive Docker/build
gates and the remote improver with deterministic test doubles.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_work_server", ROOT / "tools/work_server.py")
assert SPEC and SPEC.loader
ws = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ws)


PATCH = """diff --git a/src/core.py b/src/core.py
--- a/src/core.py
+++ b/src/core.py
@@ -1,2 +1,2 @@
 def value():
-    return 1
+    return 2
diff --git a/tools/test_core.py b/tools/test_core.py
--- a/tools/test_core.py
+++ b/tools/test_core.py
@@ -1,2 +1,2 @@
 from src.core import value
-assert value() == 1
+assert value() == 2
"""

FORBIDDEN_PATCH = """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -0,0 +1 @@
+forbidden: true
"""


def run(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        list(args), cwd=cwd, check=True, text=True, capture_output=True
    )
    return completed.stdout.strip()


def make_repo(parent: Path) -> Path:
    repo = parent / "repo"
    repo.mkdir()
    run(repo, "git", "init", "-q")
    (repo / ".gitignore").write_text(".build/\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("No GitHub Actions. Keep changes tested.\n", encoding="utf-8")
    (repo / "README.md").write_text("JETOS test repository\n", encoding="utf-8")
    (repo / "PYTHON_KERNEL_CODESIGN.md").write_text("Active experiments.\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src/core.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (repo / "tools").mkdir()
    (repo / "tools/test_core.py").write_text(
        "from src.core import value\nassert value() == 1\n", encoding="utf-8"
    )
    run(repo, "git", "add", "-A")
    run(
        repo,
        "git", "-c", "user.name=Test", "-c", "user.email=test@localhost",
        "commit", "-qm", "initial",
    )
    return repo


def passing_gate(root: Path):
    return True, [
        ws.Step(
            name="fake-gate",
            command=["fake"],
            returncode=0,
            duration_seconds=0.0,
            output="PASS",
        )
    ]


def main() -> int:
    checks = 0

    # Pure validation contracts.
    assert ws.patch_paths(PATCH) == ["src/core.py", "tools/test_core.py"]
    ws.validate_test_backing(ws.patch_paths(PATCH))
    checks += 2

    try:
        ws.patch_paths(FORBIDDEN_PATCH)
    except RuntimeError as exc:
        assert "forbidden" in str(exc).lower()
        checks += 1
    else:
        raise AssertionError("GitHub Actions workflow patch must be rejected")

    try:
        ws.validate_bind("0.0.0.0", None)
    except SystemExit:
        checks += 1
    else:
        raise AssertionError("non-loopback Work Server must require authentication")
    ws.validate_bind("0.0.0.0", "secret")
    checks += 1

    blocked_step = ws.Step(
        name="docker-os-qualification",
        command=["python", "jetos.py", "docker-test"],
        returncode=1,
        duration_seconds=0.0,
        output="JETOS Docker qualification cannot start: the Docker CLI executable was not found.",
    )
    assert ws.infrastructure_failure([blocked_step])
    checks += 1

    # A passing candidate is committed to a retained workbot/* branch.
    with tempfile.TemporaryDirectory() as temp:
        repo = make_repo(Path(temp))
        engine = ws.WorkEngine(root=repo, improver=lambda prompt: PATCH, gate_runner=passing_gate)
        cycle = engine.run_cycle(improve=True)
        assert cycle.status == "accepted", cycle.reason
        assert cycle.branch and cycle.accepted_commit
        branches = run(repo, "git", "branch", "--list", cycle.branch)
        assert cycle.branch in branches
        accepted_text = run(repo, "git", "show", f"{cycle.branch}:src/core.py")
        assert "return 2" in accepted_text
        assert (repo / ".build/work-server/candidates" / f"{cycle.id}.diff").is_file()
        checks += 5

    # A candidate that fails the second gate is rejected and its branch disappears.
    with tempfile.TemporaryDirectory() as temp:
        repo = make_repo(Path(temp))
        calls = 0

        def second_gate_fails(root: Path):
            nonlocal calls
            calls += 1
            ok = calls == 1
            return ok, [
                ws.Step(
                    name="fake-gate",
                    command=["fake"],
                    returncode=0 if ok else 1,
                    duration_seconds=0.0,
                    output="PASS" if ok else "candidate regression",
                )
            ]

        engine = ws.WorkEngine(
            root=repo,
            improver=lambda prompt: PATCH,
            gate_runner=second_gate_fails,
        )
        cycle = engine.run_cycle(improve=True)
        assert cycle.status == "rejected", cycle.reason
        assert cycle.branch
        assert not run(repo, "git", "branch", "--list", cycle.branch)
        checks += 3

    # Worker-host failures never invoke the code improver.
    with tempfile.TemporaryDirectory() as temp:
        repo = make_repo(Path(temp))
        called = False

        def blocked_gate(root: Path):
            return False, [blocked_step]

        def must_not_run(prompt: str) -> str:
            nonlocal called
            called = True
            raise AssertionError("improver must not run for infrastructure failures")

        cycle = ws.WorkEngine(
            root=repo,
            improver=must_not_run,
            gate_runner=blocked_gate,
        ).run_cycle(improve=True)
        assert cycle.status == "blocked", cycle.reason
        assert not called
        checks += 2

    # Responses API text extraction is dependency-free and deterministic.
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": "diff --git a/a b/a"}]}
        ]
    }
    assert ws.response_text(payload).startswith("diff --git")
    checks += 1

    # Secrets are opt-in and never silently guessed.
    previous_key = os.environ.pop(ws.OPENAI_KEY_ENV, None)
    previous_model = os.environ.pop(ws.MODEL_ENV, None)
    try:
        try:
            ws.call_openai_improver("test")
        except RuntimeError as exc:
            assert ws.OPENAI_KEY_ENV in str(exc) and ws.MODEL_ENV in str(exc)
            checks += 1
        else:
            raise AssertionError("improver must require explicit API configuration")
    finally:
        if previous_key is not None:
            os.environ[ws.OPENAI_KEY_ENV] = previous_key
        if previous_model is not None:
            os.environ[ws.MODEL_ENV] = previous_model

    source = (ROOT / "tools/work_server.py").read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "/v1/shell" not in source
    checks += 2

    print(f"JETOS Work Server tests: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
