#!/usr/bin/env python3
"""Check that JETOS Language tracks the latest stable Python release."""
from __future__ import annotations

import argparse
import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

PINNED_VERSION = "3.14.8"
SOURCE_RELEASES_URL = "https://www.python.org/downloads/source/"
LATEST_PATTERN = re.compile(
    r"Latest Python 3 Release\s*-\s*Python\s+(\d+\.\d+\.\d+)"
)


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"not a stable Python X.Y.Z version: {value!r}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def latest_stable(timeout: float = 10.0) -> str:
    request = Request(
        SOURCE_RELEASES_URL,
        headers={"User-Agent": "JETOS stable-Python checker"},
    )
    with urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", "strict")
    match = LATEST_PATTERN.search(text)
    if not match:
        raise RuntimeError("could not locate latest stable Python version")
    return match.group(1)


def check(*, offline_ok: bool = False) -> int:
    try:
        latest = latest_stable()
    except (OSError, URLError, RuntimeError) as error:
        if offline_ok:
            print(
                "JETOS Language freshness: UNVERIFIED "
                f"(offline or Python.org unavailable: {error})"
            )
            return 0
        raise

    pinned = version_tuple(PINNED_VERSION)
    newest = version_tuple(latest)
    print(f"JETOS pinned stable Python: {PINNED_VERSION}")
    print(f"Python.org latest stable:   {latest}")

    if pinned < newest:
        raise SystemExit(
            "JETOS Language is behind stable Python. Update the pinned CPython "
            "version/commit before continuing."
        )
    if pinned > newest:
        raise SystemExit(
            "JETOS pin is newer than Python.org's latest stable release; "
            "verify that a pre-release was not pinned."
        )

    print("JETOS Language stable-Python freshness: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("check", "latest"),
        nargs="?",
        default="check",
    )
    parser.add_argument("--offline-ok", action="store_true")
    args = parser.parse_args()

    if args.command == "latest":
        print(latest_stable())
        return 0
    return check(offline_ok=args.offline_ok)


if __name__ == "__main__":
    raise SystemExit(main())
