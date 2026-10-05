#!/usr/bin/env python3
"""Inspect JETOS persistent-storage encryption state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos.storage import StoragePolicyError, default_policy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS storage encryption status")
    parser.add_argument("paths", nargs="*", default=["/", "/boot", "/tmp"])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return failure if any requested persistent path is unprotected",
    )
    args = parser.parse_args()

    policy = default_policy()
    failed = False
    for path in args.paths:
        try:
            state = policy.inspect(path)
        except StoragePolicyError as error:
            print(f"{path}: error: {error}")
            failed = True
            continue
        print(json.dumps(state.as_dict(), sort_keys=True))
        if args.strict and state.disposition == "unprotected":
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
