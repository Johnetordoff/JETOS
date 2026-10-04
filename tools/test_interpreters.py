#!/usr/bin/env python3
"""Tests for the JETOS subinterpreter service model."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos.interpreters import (  # noqa: E402
    InterpreterSupervisor,
    plan_services,
    supported,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    checks = 0
    snapshot = {
        "capabilities": {
            "display": {
                "present": True,
                "active": True,
                "evidence": ["card0-HDMI-A-1", "1920x1080"],
            },
            "network": {
                "present": True,
                "active": False,
                "evidence": ["eth0"],
            },
            "audio": {
                "present": False,
                "active": False,
                "evidence": [],
            },
            "storage": {
                "present": True,
                "active": True,
                "evidence": ["nvme0n1", "sda"],
            },
        }
    }

    plans = plan_services(snapshot)
    names = {plan.name for plan in plans}
    check(names == {"display", "network", "storage"}, "capability plan")
    checks += 1

    per_device = plan_services(snapshot, per_device=True)
    per_device_names = {plan.name for plan in per_device}
    check(
        per_device_names
        == {"display:0", "display:1", "network:0", "storage:0", "storage:1"},
        "per-device plan",
    )
    checks += 1

    if supported():
        with InterpreterSupervisor() as supervisor:
            handle = supervisor.start(plans[0])
            check(handle.plan.name in supervisor.services, "service started")
            response = supervisor.request(handle.plan.name, ("ping",))
            check(response[0] == "pong", "subinterpreter ping")
            checks += 2
        check(not supervisor.services, "services closed")
        checks += 1
        runtime = "live subinterpreter test: PASS"
    else:
        runtime = "live subinterpreter test: SKIPPED (bootstrap Python < 3.14)"

    print(f"JETOS interpreter topology: {checks} checks passed")
    print(runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
