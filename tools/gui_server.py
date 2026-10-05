#!/usr/bin/env python3
"""Run the JETOS Tkinter desktop in Docker through a local VNC display."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def wait_for_x(display: str, timeout: float = 5.0) -> None:
    number = display.removeprefix(":").split(".", 1)[0]
    socket = Path("/tmp/.X11-unix") / f"X{number}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if socket.exists():
            return
        time.sleep(0.05)
    raise SystemExit(f"Xvfb did not create {socket}")


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS Docker/VNC GUI preview")
    parser.add_argument("--geometry", default="640x480")
    parser.add_argument("--port", type=int, default=5900)
    args = parser.parse_args()

    try:
        width, height = (int(part) for part in args.geometry.lower().split("x", 1))
    except (ValueError, AttributeError):
        raise SystemExit("geometry must be WIDTHxHEIGHT")
    if width <= 0 or height <= 0:
        raise SystemExit("geometry must be positive")

    display = ":99"
    xvfb = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_x(display)
        environment = os.environ.copy()
        environment["DISPLAY"] = display
        environment["PYTHONPATH"] = str(ROOT / "src")

        vnc = subprocess.Popen(
            [
                "x11vnc",
                "-display",
                display,
                "-forever",
                "-shared",
                "-nopw",
                "-rfbport",
                str(args.port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        try:
            print(f"JETOS desktop VNC ready on port {args.port}", flush=True)
            print(f"geometry: {width}x{height}", flush=True)
            return subprocess.call(
                [sys.executable, "-m", "jetos.desktop", "--fullscreen"],
                cwd=ROOT,
                env=environment,
            )
        finally:
            vnc.terminate()
            try:
                vnc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                vnc.kill()
    finally:
        xvfb.terminate()
        try:
            xvfb.wait(timeout=2)
        except subprocess.TimeoutExpired:
            xvfb.kill()


if __name__ == "__main__":
    raise SystemExit(main())
