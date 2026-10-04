#!/usr/bin/env python3
"""Headless geometry tests for the JETOS desktop shell."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos.desktop import layout_for, parse_geometry  # noqa: E402


SIZES = [
    (1, 1),
    (64, 32),
    (191, 113),
    (320, 200),
    (320, 240),
    (517, 301),
    (640, 480),
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1920, 1080),
    (1080, 1920),
    (2560, 1080),
    (3440, 1440),
    (3840, 2160),
    (7680, 4320),
]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def inside(child, parent) -> bool:
    return (
        child.x >= parent.x
        and child.y >= parent.y
        and child.right <= parent.right
        and child.bottom <= parent.bottom
        and child.width >= 1
        and child.height >= 1
    )


def main() -> int:
    checks = 0

    check(parse_geometry("640x480") == (640, 480), "lowercase geometry")
    check(parse_geometry("517×301") == (517, 301), "multiplication geometry")
    check(parse_geometry(" 1080 X 1920 ") == (1080, 1920), "spaced geometry")
    checks += 3

    for value in ("", "640", "0x480", "-1x100", "100x0", "abcxdef"):
        try:
            parse_geometry(value)
        except ValueError:
            checks += 1
        else:
            raise AssertionError(f"invalid geometry accepted: {value!r}")

    for width, height in SIZES:
        layout = layout_for(width, height)
        check(layout.screen.width == width, f"screen width {width}x{height}")
        check(layout.screen.height == height, f"screen height {width}x{height}")
        check(inside(layout.taskbar, layout.screen), f"taskbar {width}x{height}")
        check(inside(layout.start_button, layout.taskbar), f"start {width}x{height}")
        check(inside(layout.clock, layout.taskbar), f"clock {width}x{height}")
        check(inside(layout.welcome_window, layout.screen), f"window {width}x{height}")
        checks += 6

    tiny = layout_for(1, 1)
    check(tiny.taskbar.width == 1, "1px taskbar width")
    check(tiny.taskbar.height == 1, "1px taskbar height")
    checks += 2

    normal = layout_for(640, 480)
    high = layout_for(3840, 2160)
    check(high.scale > normal.scale, "high-resolution scale")
    checks += 1

    print(f"JETOS desktop layout: {checks} checks passed across {len(SIZES)} geometries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
