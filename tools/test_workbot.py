#!/usr/bin/env python3
"""Tests for the local JETOS Work Bot server."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_workbot", ROOT / "tools/workbot.py")
assert SPEC and SPEC.loader
workbot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbot)


def wait_for(bot, job_id: str, timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = bot.get(job_id)
        assert job is not None
        if job.status in {"passed", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError("workbot job did not finish")


def main() -> int:
    checks = 0

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "jetos.py").write_text("# minimal test checkout\n", encoding="utf-8")

        def passing_runner(command: tuple[str, ...]):
            return 0, "PASS " + " ".join(command)

        bot = workbot.WorkBot(root=root, runner=passing_runner)
        bot.start()
        job = bot.enqueue("test")
        finished = wait_for(bot, job.id)
        assert finished.status == "passed"
        assert finished.returncode == 0
        assert (root / ".build/workbot/jobs" / f"{job.id}.json").is_file()
        checks += 3

        try:
            bot.enqueue("shell")
        except ValueError:
            checks += 1
        else:
            raise AssertionError("arbitrary workbot jobs must be rejected")
        bot.stop()

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "jetos.py").write_text("# minimal test checkout\n", encoding="utf-8")

        def failing_runner(command: tuple[str, ...]):
            if command[-1] == "test":
                return 1, "AssertionError: protected behavior changed"
            return 0, "PASS"

        bot = workbot.WorkBot(root=root, runner=failing_runner)
        bot.start()
        job = bot.enqueue("cycle")
        finished = wait_for(bot, job.id)
        assert finished.status == "failed"
        assert finished.proposals
        assert any("qualification" in item["title"].lower() for item in finished.proposals)
        assert (root / ".build/workbot/proposals" / f"{job.id}.json").is_file()
        assert [step["kind"] for step in finished.steps] == ["doctor", "test", "build"]
        checks += 5
        bot.stop()

    try:
        workbot.validate_binding("0.0.0.0", None)
    except SystemExit:
        checks += 1
    else:
        raise AssertionError("non-loopback Work Bot must require a token")
    workbot.validate_binding("0.0.0.0", "secret")
    checks += 1

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "jetos.py").write_text("# minimal test checkout\n", encoding="utf-8")
        bot = workbot.WorkBot(root=root, runner=lambda command: (0, "PASS"))
        bot.start()
        server = workbot.WorkBotHTTPServer(("127.0.0.1", 0), bot, "token")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                payload = json.load(response)
            assert payload["status"] == "ok"
            checks += 1

            try:
                urlopen(f"http://127.0.0.1:{port}/v1/status", timeout=2)
            except HTTPError as exc:
                assert exc.code == 401
                checks += 1
            else:
                raise AssertionError("authenticated endpoint accepted no token")

            request = Request(
                f"http://127.0.0.1:{port}/v1/jobs",
                data=json.dumps({"kind": "test"}).encode("utf-8"),
                headers={
                    "Authorization": "Bearer token",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=2) as response:
                created = json.load(response)
            assert created["kind"] == "test"
            assert wait_for(bot, created["id"]).status == "passed"
            checks += 2
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            bot.stop()

    print(f"JETOS Work Bot tests: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
