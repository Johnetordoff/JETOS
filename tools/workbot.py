#!/usr/bin/env python3
"""Local JETOS Work Bot server.

The Work Bot exposes a deliberately small HTTP API for running repository-owned
qualification/build jobs, recording results, and turning failures into bounded
improvement proposals.  It never accepts arbitrary shell commands.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
from typing import Callable
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_BODY = 16 * 1024
MAX_OUTPUT = 64 * 1024
MAX_HISTORY = 100
DEFAULT_TIMEOUT = 60 * 60
TOKEN_ENV = "JETOS_WORKBOT_TOKEN"


@dataclass(frozen=True)
class JobSpec:
    name: str
    command: tuple[str, ...]
    description: str


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: now())
    started_at: str | None = None
    finished_at: str | None = None
    returncode: int | None = None
    duration_seconds: float | None = None
    output: str = ""
    proposals: list[dict[str, str]] = field(default_factory=list)
    steps: list[dict[str, object]] = field(default_factory=list)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def available_jobs(root: Path = ROOT) -> dict[str, JobSpec]:
    py = sys.executable
    jobs = {
        "doctor": JobSpec(
            "doctor",
            (py, "jetos.py", "doctor"),
            "Inspect development-host capabilities required by JETOS.",
        ),
        "test": JobSpec(
            "test",
            (py, "jetos.py", "test"),
            "Run the repository-owned JETOS qualification suite.",
        ),
        "build": JobSpec(
            "build",
            (py, "tools/dev.py", "build"),
            "Build the current JETOS development image without booting it.",
        ),
    }
    entrypoint = root / "jetos.py"
    try:
        text = entrypoint.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if "docker-test" in text:
        jobs["docker-test"] = JobSpec(
            "docker-test",
            (py, "jetos.py", "docker-test"),
            "Run JETOS operating-system qualification inside Docker.",
        )
    return jobs


def cycle_kinds(root: Path = ROOT) -> list[str]:
    jobs = available_jobs(root)
    ordered = ["doctor", "test"]
    if "docker-test" in jobs:
        ordered.append("docker-test")
    ordered.append("build")
    return ordered


def run_command(
    command: tuple[str, ...],
    *,
    root: Path = ROOT,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout[-MAX_OUTPUT:]


def analyze_failure(kind: str, output: str, returncode: int) -> list[dict[str, str]]:
    if returncode == 0:
        return []
    lower = output.lower()
    proposals: list[dict[str, str]] = []

    def add(title: str, evidence: str, next_action: str) -> None:
        proposals.append(
            {"title": title, "evidence": evidence, "next_action": next_action}
        )

    if "docker" in lower and ("not installed" in lower or "not found" in lower):
        add(
            "Provide the container-engine host capability",
            "The Docker qualification path could not find a container engine.",
            "Install/connect the Docker CLI and daemon on the JETOS worker host, then rerun docker-test.",
        )
    if "no module named" in lower or "modulenotfounderror" in lower:
        add(
            "Repair the Python module surface",
            "A required Python module was unavailable during qualification.",
            "Identify whether the module is stdlib, JETOS-owned, or imported native support; restore it without weakening the Python contract.",
        )
    if "assertionerror" in lower or "assertion failed" in lower:
        add(
            "Investigate a qualification regression",
            "A repository assertion failed.",
            "Reduce the failing case, compare it with the protected baseline, and fix the implementation rather than deleting the assertion.",
        )
    if "no such file or directory" in lower:
        add(
            "Restore a required build/runtime artifact",
            "A required path or executable was missing.",
            "Resolve the missing capability or generated artifact and add a preflight check if the failure can be detected earlier.",
        )
    if "error:" in lower or "failed" in lower:
        add(
            f"Reduce and repair the {kind} failure",
            f"The {kind} job exited with status {returncode}.",
            "Preserve the captured log, identify the earliest causal error, add or strengthen a regression test, then rerun this job.",
        )
    if not proposals:
        add(
            f"Investigate the {kind} failure",
            f"The {kind} job exited with status {returncode}.",
            "Inspect the captured output, reproduce locally, and convert the cause into a focused regression test before changing behavior.",
        )
    return proposals


Runner = Callable[[tuple[str, ...]], tuple[int, str]]


class WorkBot:
    def __init__(
        self,
        *,
        root: Path = ROOT,
        runner: Runner | None = None,
        history_limit: int = MAX_HISTORY,
    ) -> None:
        self.root = root
        self.runner = runner or (lambda command: run_command(command, root=root))
        self.history_limit = history_limit
        self.queue: queue.Queue[str] = queue.Queue()
        self.jobs: dict[str, Job] = {}
        self.history: deque[str] = deque(maxlen=history_limit)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.build_dir = root / ".build" / "workbot"
        self.jobs_dir = self.build_dir / "jobs"
        self.proposals_dir = self.build_dir / "proposals"

    def start(self) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        if not self.worker.is_alive():
            self.worker.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.queue.put("")
        if self.worker.is_alive():
            self.worker.join(timeout=5)

    def enqueue(self, kind: str) -> Job:
        if kind != "cycle" and kind not in available_jobs(self.root):
            raise ValueError(f"unsupported JETOS Work Bot job: {kind}")
        job = Job(id=uuid.uuid4().hex, kind=kind)
        with self.lock:
            self.jobs[job.id] = job
            self.history.append(job.id)
            self._persist(job)
        self.queue.put(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            recent = [asdict(self.jobs[job_id]) for job_id in reversed(self.history)]
            running = [job.id for job in self.jobs.values() if job.status == "running"]
            queued = [job.id for job in self.jobs.values() if job.status == "queued"]
        specs = available_jobs(self.root)
        return {
            "service": "JETOS Work Bot",
            "status": "ok",
            "available_jobs": {
                name: spec.description for name, spec in sorted(specs.items())
            },
            "cycle": cycle_kinds(self.root),
            "running": running,
            "queued": queued,
            "recent": recent,
        }

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            job_id = self.queue.get()
            if not job_id:
                continue
            job = self.get(job_id)
            if job is None:
                continue
            self._execute(job)

    def _execute(self, job: Job) -> None:
        with self.lock:
            job.status = "running"
            job.started_at = now()
            self._persist(job)
        started = time.monotonic()
        if job.kind == "cycle":
            returncode, output, proposals, steps = self._run_cycle()
            job.steps = steps
        else:
            spec = available_jobs(self.root)[job.kind]
            returncode, output = self.runner(spec.command)
            proposals = analyze_failure(job.kind, output, returncode)
        duration = time.monotonic() - started
        with self.lock:
            job.returncode = returncode
            job.output = output[-MAX_OUTPUT:]
            job.proposals = proposals
            job.duration_seconds = round(duration, 6)
            job.finished_at = now()
            job.status = "passed" if returncode == 0 else "failed"
            self._persist(job)
            if proposals:
                self._persist_proposals(job)

    def _run_cycle(self) -> tuple[int, str, list[dict[str, str]], list[dict[str, object]]]:
        combined: list[str] = []
        proposals: list[dict[str, str]] = []
        steps: list[dict[str, object]] = []
        overall = 0
        specs = available_jobs(self.root)
        for kind in cycle_kinds(self.root):
            spec = specs[kind]
            started = time.monotonic()
            returncode, output = self.runner(spec.command)
            duration = round(time.monotonic() - started, 6)
            step = {
                "kind": kind,
                "returncode": returncode,
                "duration_seconds": duration,
                "output": output[-MAX_OUTPUT:],
            }
            steps.append(step)
            combined.append(f"===== {kind} =====\n{output}")
            if returncode != 0:
                overall = returncode if overall == 0 else overall
                proposals.extend(analyze_failure(kind, output, returncode))
        return overall, "\n".join(combined)[-MAX_OUTPUT:], proposals, steps

    def _persist(self, job: Job) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        path = self.jobs_dir / f"{job.id}.json"
        path.write_text(json.dumps(asdict(job), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _persist_proposals(self, job: Job) -> None:
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        path = self.proposals_dir / f"{job.id}.json"
        payload = {
            "job_id": job.id,
            "kind": job.kind,
            "generated_at": now(),
            "proposals": job.proposals,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class WorkBotHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], bot: WorkBot, token: str | None):
        super().__init__(address, WorkBotHandler)
        self.bot = bot
        self.token = token


class WorkBotHandler(BaseHTTPRequestHandler):
    server: WorkBotHTTPServer

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"workbot-http: {self.address_string()} {fmt % args}", flush=True)

    def _authorized(self) -> bool:
        token = self.server.token
        if token is None:
            return True
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {token}"
        return secrets.compare_digest(supplied, expected)

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._json(401, {"error": "unauthorized"})
        return False

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"service": "JETOS Work Bot", "status": "ok"})
            return
        if not self._require_auth():
            return
        if path == "/v1/status":
            self._json(200, self.server.bot.snapshot())
            return
        if path == "/v1/jobs":
            self._json(200, self.server.bot.snapshot()["recent"])
            return
        prefix = "/v1/jobs/"
        if path.startswith(prefix):
            job = self.server.bot.get(path[len(prefix):])
            if job is None:
                self._json(404, {"error": "job not found"})
            else:
                self._json(200, asdict(job))
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        path = urlparse(self.path).path
        if path != "/v1/jobs":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid content length"})
            return
        if length <= 0 or length > MAX_BODY:
            self._json(413 if length > MAX_BODY else 400, {"error": "invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            kind = payload["kind"]
            if not isinstance(kind, str):
                raise TypeError
            job = self.server.bot.enqueue(kind)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self._json(400, {"error": str(exc) or "invalid request"})
            return
        self._json(202, asdict(job))


def validate_binding(host: str, token: str | None) -> None:
    loopback = {"127.0.0.1", "localhost", "::1"}
    if host not in loopback and not token:
        raise SystemExit(
            f"Refusing to expose JETOS Work Bot on {host!r} without authentication. "
            f"Set {TOKEN_ENV} to a strong token or bind to localhost."
        )


def serve(host: str, port: int, *, token: str | None, interval: int) -> None:
    validate_binding(host, token)
    bot = WorkBot()
    bot.start()
    server = WorkBotHTTPServer((host, port), bot, token)

    scheduler_stop = threading.Event()
    scheduler: threading.Thread | None = None
    if interval > 0:
        def schedule_loop() -> None:
            while not scheduler_stop.wait(interval):
                snap = bot.snapshot()
                if not snap["running"] and not snap["queued"]:
                    bot.enqueue("cycle")

        scheduler = threading.Thread(target=schedule_loop, daemon=True)
        scheduler.start()

    bound_host, bound_port = server.server_address[:2]
    print(f"JETOS Work Bot listening on http://{bound_host}:{bound_port}")
    print(f"jobs: {', '.join(sorted(available_jobs()))}; cycle")
    if token:
        print(f"authentication: bearer token from {TOKEN_ENV}")
    else:
        print("authentication: localhost-only")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler_stop.set()
        if scheduler is not None:
            scheduler.join(timeout=2)
        server.server_close()
        bot.stop()


def run_once(kind: str) -> int:
    bot = WorkBot()
    bot.start()
    job = bot.enqueue(kind)
    try:
        while True:
            current = bot.get(job.id)
            assert current is not None
            if current.status in {"passed", "failed"}:
                print(json.dumps(asdict(current), indent=2, sort_keys=True))
                return 0 if current.status == "passed" else (current.returncode or 1)
            time.sleep(0.05)
    finally:
        bot.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS local work/qualification bot")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="start the local Work Bot HTTP server")
    serve_parser.add_argument("--host", default=DEFAULT_HOST)
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="optionally enqueue a full cycle every N seconds when idle; 0 disables",
    )

    once = sub.add_parser("run-once", help="run one known job and print its JSON result")
    once.add_argument("kind", choices=["doctor", "test", "build", "docker-test", "cycle"])

    args = parser.parse_args()
    if args.command == "serve":
        if args.interval < 0:
            raise SystemExit("--interval must be >= 0")
        serve(args.host, args.port, token=os.environ.get(TOKEN_ENV), interval=args.interval)
        return 0
    if args.kind == "docker-test" and "docker-test" not in available_jobs():
        raise SystemExit("docker-test is not available in this JETOS checkout")
    return run_once(args.kind)


if __name__ == "__main__":
    raise SystemExit(main())
