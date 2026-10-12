#!/usr/bin/env python3
"""JETOS self-hosted work server.

The Work Server owns build/test/improvement cycles rather than exposing a shell.
A cycle is intentionally conservative:

1. require a clean Git checkout;
2. create a disposable linked worktree and candidate branch;
3. run Docker JETOS OS qualification and the Fat build gate;
4. if requested, ask an explicitly configured improver for one bounded diff;
5. validate/apply that diff only inside the disposable worktree;
6. rerun every gate;
7. retain a Git commit/branch only when the candidate passes.

GitHub Actions are never used. Jenkins may schedule `run-cycle`; the repository
owns all work policy.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
TOKEN_ENV = "JETOS_WORKSERVER_TOKEN"
IMPROVE_ENV = "JETOS_WORKSERVER_IMPROVE"
PUSH_ENV = "JETOS_WORKSERVER_PUSH"
OPENAI_KEY_ENV = "OPENAI_API_KEY"
MODEL_ENV = "JETOS_WORKBOT_MODEL"
MAX_LOG = 96 * 1024
MAX_PATCH = 128 * 1024
MAX_CONTEXT = 160 * 1024
MAX_FILES = 12
MAX_HISTORY = 50
REQUEST_LIMIT = 32 * 1024
TIMEOUT = 60 * 60
FORBIDDEN_PATH_PREFIXES = (
    ".git/",
    ".github/workflows/",
    "vendor/linux/",
    "vendor/cpython/",
)
INFRASTRUCTURE_MARKERS = (
    "docker cli executable was not found",
    "docker daemon is not reachable",
    "cannot connect to the docker daemon",
    "error during connect",
    "temporary failure resolving",
    "network is unreachable",
    "could not resolve host",
    "no space left on device",
)


@dataclass
class Step:
    name: str
    command: list[str]
    returncode: int
    duration_seconds: float
    output: str


@dataclass
class Cycle:
    id: str
    improve: bool
    status: str = "queued"
    created_at: str = field(default_factory=lambda: now())
    started_at: str | None = None
    finished_at: str | None = None
    base_commit: str | None = None
    branch: str | None = None
    accepted_commit: str | None = None
    pushed: bool = False
    candidate_patch: str | None = None
    reason: str = ""
    steps: list[Step] = field(default_factory=list)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def run_process(
    args: list[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    timeout: int = TIMEOUT,
) -> tuple[int, str, float]:
    started = time.monotonic()
    completed = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return completed.returncode, completed.stdout[-MAX_LOG:], time.monotonic() - started


def git(root: Path, *args: str, input_text: str | None = None) -> tuple[int, str]:
    rc, out, _ = run_process(["git", *args], cwd=root, input_text=input_text)
    return rc, out


def require_clean_checkout(root: Path) -> str:
    rc, status = git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    if rc != 0:
        raise RuntimeError(f"git status failed: {status.strip()}")
    if status.strip():
        raise RuntimeError(
            "JETOS Work Server requires a clean checkout; commit or stash local changes first."
        )
    rc, head = git(root, "rev-parse", "HEAD")
    if rc != 0:
        raise RuntimeError(f"cannot resolve HEAD: {head.strip()}")
    return head.strip()


def qualification_commands() -> list[tuple[str, list[str]]]:
    python = sys.executable
    return [
        ("docker-os-qualification", [python, "jetos.py", "docker-test"]),
        ("fat-build", [python, "jetos.py", "dev", "--build-only"]),
    ]


def execute_gates(root: Path) -> tuple[bool, list[Step]]:
    steps: list[Step] = []
    for name, command in qualification_commands():
        rc, output, duration = run_process(command, cwd=root)
        steps.append(
            Step(
                name=name,
                command=command,
                returncode=rc,
                duration_seconds=round(duration, 6),
                output=output,
            )
        )
        if rc != 0:
            return False, steps
    return True, steps


def infrastructure_failure(steps: list[Step]) -> str | None:
    failed = [step for step in steps if step.returncode != 0]
    if not failed:
        return None
    text = "\n".join(step.output.lower() for step in failed)
    for marker in INFRASTRUCTURE_MARKERS:
        if marker in text:
            return marker
    return None


def relevant_files(root: Path, logs: str) -> list[Path]:
    candidates = [Path("AGENTS.md"), Path("README.md"), Path("PYTHON_KERNEL_CODESIGN.md")]
    pattern = re.compile(r"(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:py|c|h|md|toml|json)")
    for match in pattern.findall(logs):
        candidates.append(Path(match))
    seen: set[str] = set()
    result: list[Path] = []
    for relative in candidates:
        normalized = relative.as_posix().lstrip("./")
        if normalized in seen or normalized.startswith(FORBIDDEN_PATH_PREFIXES):
            continue
        path = root / normalized
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 48 * 1024:
                continue
        except OSError:
            continue
        seen.add(normalized)
        result.append(Path(normalized))
        if len(result) >= MAX_FILES:
            break
    return result


def build_improvement_prompt(root: Path, steps: list[Step], baseline_passed: bool) -> str:
    logs = "\n".join(f"===== {s.name} =====\n{s.output}" for s in steps)
    context_parts: list[str] = []
    total = 0
    for relative in relevant_files(root, logs):
        text = (root / relative).read_text(encoding="utf-8", errors="replace")
        block = f"\n===== FILE {relative.as_posix()} =====\n{text}"
        if total + len(block) > MAX_CONTEXT:
            break
        context_parts.append(block)
        total += len(block)

    objective = (
        "The current gates pass. Make one small, test-backed JETOS improvement that "
        "advances an existing documented objective without changing protected semantics."
        if baseline_passed
        else
        "Repair the earliest causal qualification/build failure without weakening, deleting, "
        "or bypassing the failing test or protected Python semantics."
    )
    return f"""You are the JETOS Work Bot improver. {objective}

Hard constraints:
- Return exactly one unified Git diff and no prose outside the diff.
- Never create or modify .github/workflows or any GitHub Actions configuration.
- Do not modify vendor/linux or vendor/cpython in this candidate.
- Keep the change small: at most {MAX_FILES} files.
- Include or strengthen a repository-owned regression test for executable behavior changes.
- Do not add Node.js or a JavaScript package/build stack.
- Preserve Python 3.14 behavior and every applicable JETOS mandate in AGENTS.md.
- Do not remove, skip, or weaken tests merely to obtain a pass.
- Do not try to repair missing Docker, networking, disk space, or other worker-host infrastructure by changing JETOS source.

Qualification output:
{logs[-MAX_CONTEXT:]}

Repository context:
{''.join(context_parts)}
"""


def response_text(payload: dict[str, object]) -> str:
    pieces: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str):
                        pieces.append(text)
    direct = payload.get("output_text")
    if not pieces and isinstance(direct, str):
        pieces.append(direct)
    return "\n".join(pieces).strip()


def call_openai_improver(prompt: str) -> str:
    key = os.environ.get(OPENAI_KEY_ENV)
    model = os.environ.get(MODEL_ENV)
    if not key or not model:
        raise RuntimeError(
            f"automatic improvement requires both {OPENAI_KEY_ENV} and {MODEL_ENV}; "
            "secrets are read only from the process environment"
        )
    body = json.dumps({"model": model, "input": prompt}).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=180) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-4096:]
        raise RuntimeError(f"improver API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"improver API unavailable: {exc}") from exc
    text = response_text(payload)
    if not text:
        raise RuntimeError("improver returned no text output")
    return text


def extract_diff(text: str) -> str:
    fenced = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("diff --git ")
    if start < 0:
        raise RuntimeError("improver response did not contain a unified git diff")
    patch = text[start:].strip() + "\n"
    if len(patch.encode("utf-8")) > MAX_PATCH:
        raise RuntimeError("candidate patch exceeds the Work Server size limit")
    return patch


def patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git a/"):
            continue
        parts = line.split()
        if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
            raise RuntimeError("malformed diff header")
        old = parts[2][2:]
        new = parts[3][2:]
        if old != new:
            raise RuntimeError("automatic candidate renames are not permitted")
        paths.append(new)
    if not paths:
        raise RuntimeError("candidate patch changes no files")
    if len(set(paths)) > MAX_FILES:
        raise RuntimeError("candidate patch changes too many files")
    for path in paths:
        if path.startswith(FORBIDDEN_PATH_PREFIXES):
            raise RuntimeError(f"candidate patch touches forbidden path: {path}")
        if path.startswith("/") or ".." in Path(path).parts:
            raise RuntimeError(f"unsafe candidate path: {path}")
    if any(".github/workflows" in line for line in patch.splitlines()):
        raise RuntimeError("candidate patch mentions forbidden GitHub Actions workflow path")
    return sorted(set(paths))


def validate_test_backing(paths: list[str]) -> None:
    executable = any(
        path.endswith((".py", ".c", ".h")) and "test" not in Path(path).name.lower()
        for path in paths
    )
    test_change = any("test" in Path(path).name.lower() for path in paths)
    if executable and not test_change:
        raise RuntimeError("automatic executable-code changes must include a regression-test change")


def apply_patch(worktree: Path, patch: str) -> None:
    paths = patch_paths(patch)
    validate_test_backing(paths)
    rc, out = git(worktree, "apply", "--check", "--whitespace=error-all", "-", input_text=patch)
    if rc != 0:
        raise RuntimeError(f"candidate patch failed git apply --check: {out.strip()}")
    rc, out = git(worktree, "apply", "--whitespace=error-all", "-", input_text=patch)
    if rc != 0:
        raise RuntimeError(f"candidate patch could not be applied: {out.strip()}")


def cleanup_worktree(root: Path, path: Path) -> None:
    git(root, "worktree", "remove", "--force", str(path))


def delete_branch(root: Path, branch: str) -> None:
    git(root, "branch", "-D", branch)


def persist_cycle(cycle: Cycle, state: Path) -> None:
    directory = state / "cycles"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{cycle.id}.json"
    target.write_text(json.dumps(asdict(cycle), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[MAX_HISTORY:]:
        old.unlink(missing_ok=True)


Improver = Callable[[str], str]
GateRunner = Callable[[Path], tuple[bool, list[Step]]]


class WorkEngine:
    def __init__(
        self,
        root: Path = ROOT,
        improver: Improver | None = None,
        gate_runner: GateRunner = execute_gates,
    ) -> None:
        self.root = root
        self.state = root / ".build" / "work-server"
        self.improver = improver or call_openai_improver
        self.gate_runner = gate_runner
        self.lock = threading.Lock()

    def run_cycle(
        self,
        *,
        improve: bool,
        push: bool = False,
        cycle_id: str | None = None,
    ) -> Cycle:
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("another JETOS Work Server cycle is already running")
        cycle = Cycle(id=cycle_id or uuid.uuid4().hex, improve=improve)
        persist_cycle(cycle, self.state)
        branch: str | None = None
        worktree: Path | None = None
        accepted = False
        try:
            cycle.status = "running"
            cycle.started_at = now()
            cycle.base_commit = require_clean_checkout(self.root)
            persist_cycle(cycle, self.state)

            branch = f"workbot/{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{cycle.id[:8]}"
            cycle.branch = branch
            temp_root = Path(tempfile.mkdtemp(prefix="jetos-workserver-"))
            worktree = temp_root / "worktree"
            rc, out = git(self.root, "worktree", "add", "-b", branch, str(worktree), cycle.base_commit)
            if rc != 0:
                raise RuntimeError(f"cannot create isolated worktree: {out.strip()}")

            baseline_ok, baseline_steps = self.gate_runner(worktree)
            cycle.steps.extend(baseline_steps)
            blocked = infrastructure_failure(baseline_steps)
            if blocked:
                cycle.status = "blocked"
                cycle.reason = f"worker infrastructure failure: {blocked}"
                return cycle
            persist_cycle(cycle, self.state)

            if not improve:
                cycle.status = "passed" if baseline_ok else "failed"
                cycle.reason = "qualification passed" if baseline_ok else "qualification failed"
                return cycle

            prompt = build_improvement_prompt(worktree, baseline_steps, baseline_ok)
            raw = self.improver(prompt)
            patch = extract_diff(raw)
            cycle.candidate_patch = patch
            candidate_dir = self.state / "candidates"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (candidate_dir / f"{cycle.id}.diff").write_text(patch, encoding="utf-8")
            apply_patch(worktree, patch)

            candidate_ok, candidate_steps = self.gate_runner(worktree)
            for step in candidate_steps:
                step.name = "candidate-" + step.name
            cycle.steps.extend(candidate_steps)
            blocked = infrastructure_failure(candidate_steps)
            if blocked:
                cycle.status = "blocked"
                cycle.reason = f"worker infrastructure failed while validating candidate: {blocked}"
                return cycle
            if not candidate_ok:
                cycle.status = "rejected"
                cycle.reason = "candidate did not pass the full JETOS gates"
                return cycle

            rc, out = git(worktree, "status", "--porcelain=v1")
            if rc != 0 or not out.strip():
                raise RuntimeError("improver produced no effective repository change")
            rc, out = git(worktree, "add", "-A")
            if rc != 0:
                raise RuntimeError(f"cannot stage accepted candidate: {out.strip()}")
            rc, out = git(
                worktree,
                "-c", "user.name=JETOS Work Bot",
                "-c", "user.email=jetos-workbot@localhost",
                "commit", "-m", f"Work Bot: validated improvement {cycle.id[:8]}",
            )
            if rc != 0:
                raise RuntimeError(f"cannot commit accepted candidate: {out.strip()}")
            rc, commit = git(worktree, "rev-parse", "HEAD")
            if rc != 0:
                raise RuntimeError(f"cannot resolve accepted commit: {commit.strip()}")
            cycle.accepted_commit = commit.strip()
            accepted = True

            if push:
                rc, out = git(worktree, "push", "-u", "origin", branch)
                if rc != 0:
                    cycle.status = "accepted"
                    cycle.reason = f"candidate accepted locally but push failed: {out.strip()[-2048:]}"
                    return cycle
                cycle.pushed = True
            cycle.status = "accepted"
            cycle.reason = "candidate passed all gates and was retained as a Git branch"
            return cycle
        except Exception as exc:
            cycle.status = "error"
            cycle.reason = str(exc)
            return cycle
        finally:
            cycle.finished_at = now()
            persist_cycle(cycle, self.state)
            if worktree is not None:
                cleanup_worktree(self.root, worktree)
                shutil.rmtree(worktree.parent, ignore_errors=True)
            if branch and not accepted:
                delete_branch(self.root, branch)
            self.lock.release()


class WorkServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], engine: WorkEngine, token: str | None):
        super().__init__(address, WorkHandler)
        self.engine = engine
        self.token = token
        self.cycles: dict[str, Cycle] = {}
        self.cycles_lock = threading.RLock()
        self.queue: queue.Queue[tuple[str, bool, bool]] = queue.Queue()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def enqueue(self, improve: bool, push: bool) -> Cycle:
        cycle = Cycle(id=uuid.uuid4().hex, improve=improve)
        with self.cycles_lock:
            self.cycles[cycle.id] = cycle
        self.queue.put((cycle.id, improve, push))
        return cycle

    def _loop(self) -> None:
        while True:
            cycle_id, improve, push = self.queue.get()
            result = self.engine.run_cycle(improve=improve, push=push, cycle_id=cycle_id)
            with self.cycles_lock:
                self.cycles[cycle_id] = result


class WorkHandler(BaseHTTPRequestHandler):
    server: WorkServer

    def log_message(self, fmt: str, *args: object) -> None:
        print("jetos-work-server:", fmt % args, flush=True)

    def authorized(self) -> bool:
        if self.server.token is None:
            return True
        supplied = self.headers.get("Authorization", "")
        return secrets.compare_digest(supplied, f"Bearer {self.server.token}")

    def json_response(self, status: int, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self.json_response(200, {"service": "JETOS Work Server", "status": "ok"})
            return
        if not self.authorized():
            self.json_response(401, {"error": "unauthorized"})
            return
        if path == "/v1/status":
            with self.server.cycles_lock:
                recent = [asdict(c) for c in list(self.server.cycles.values())[-20:]]
            self.json_response(200, {"service": "JETOS Work Server", "recent": recent})
            return
        prefix = "/v1/cycles/"
        if path.startswith(prefix):
            cycle_id = path[len(prefix):]
            with self.server.cycles_lock:
                cycle = self.server.cycles.get(cycle_id)
            if cycle is None:
                self.json_response(404, {"error": "cycle not found"})
            else:
                self.json_response(200, asdict(cycle))
            return
        self.json_response(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self.authorized():
            self.json_response(401, {"error": "unauthorized"})
            return
        if urlparse(self.path).path != "/v1/cycles":
            self.json_response(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.json_response(400, {"error": "invalid Content-Length"})
            return
        if length < 0 or length > REQUEST_LIMIT:
            self.json_response(413, {"error": "request too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.json_response(400, {"error": "invalid JSON"})
            return
        improve = bool(payload.get("improve", False))
        push = bool(payload.get("push", False))
        if push and not improve:
            self.json_response(400, {"error": "push is only valid for improvement cycles"})
            return
        cycle = self.server.enqueue(improve, push)
        self.json_response(202, asdict(cycle))


def validate_bind(host: str, token: str | None) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"} and not token:
        raise SystemExit(
            f"refusing non-loopback Work Server bind without {TOKEN_ENV} authentication"
        )


def serve(host: str, port: int) -> int:
    token = os.environ.get(TOKEN_ENV)
    validate_bind(host, token)
    server = WorkServer((host, port), WorkEngine(), token)
    print(f"JETOS Work Server listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


def run_once(improve: bool, push: bool) -> int:
    cycle = WorkEngine().run_cycle(improve=improve, push=push)
    print(json.dumps(asdict(cycle), indent=2, default=str))
    return 0 if cycle.status in {"passed", "accepted"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS self-hosted build/test/improvement server")
    sub = parser.add_subparsers(dest="command", required=True)

    server = sub.add_parser("serve", help="run the persistent JETOS Work Server")
    server.add_argument("--host", default=DEFAULT_HOST)
    server.add_argument("--port", type=int, default=DEFAULT_PORT)

    once = sub.add_parser("run-cycle", help="run one qualification/improvement cycle")
    once.add_argument("--improve", action="store_true", default=truthy(os.environ.get(IMPROVE_ENV)))
    once.add_argument("--push", action="store_true", default=truthy(os.environ.get(PUSH_ENV)))

    args = parser.parse_args()
    if args.command == "serve":
        return serve(args.host, args.port)
    return run_once(args.improve, args.push)


if __name__ == "__main__":
    raise SystemExit(main())
