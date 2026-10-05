#!/usr/bin/env python3
"""Inspect JETOS persistent-storage encryption policy and evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos.storage import (  # noqa: E402
    EncryptionOverride,
    StoragePolicyError,
    default_policy,
    load_policy,
    parse_encryption_mode,
)


def parse_override(value: str) -> EncryptionOverride:
    if "=" not in value:
        raise argparse.ArgumentTypeError("override must be PATH=on or PATH=off")
    prefix, raw_mode = value.split("=", 1)
    if not prefix.startswith("/"):
        raise argparse.ArgumentTypeError("override path must be absolute")
    try:
        enabled = parse_encryption_mode(raw_mode)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return EncryptionOverride(
        prefix=prefix,
        enabled=enabled,
        reason="explicit command-line storage policy override",
        owner="JETOS operator",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS storage encryption status")
    parser.add_argument("paths", nargs="*", default=["/", "/boot", "/tmp"])
    parser.add_argument("--encryption", choices=("on", "off"), default="on")
    parser.add_argument(
        "--override",
        action="append",
        type=parse_override,
        default=[],
        metavar="PATH=MODE",
        help="scoped override such as /scratch=off or /home/secure=on",
    )
    parser.add_argument("--config", type=Path, help="load global/scoped policy from JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return failure if a path requires encryption but is unprotected",
    )
    args = parser.parse_args()

    if args.config:
        policy = load_policy(args.config)
    else:
        policy = default_policy(
            encryption_enabled=(args.encryption == "on"),
            overrides=args.override,
        )

    print(
        json.dumps(
            {
                "global_encryption": policy.encryption_enabled,
                "overrides": [
                    {
                        "prefix": override.prefix,
                        "encryption": override.enabled,
                        "reason": override.reason,
                        "owner": override.owner,
                    }
                    for override in policy.overrides
                ],
            },
            sort_keys=True,
        )
    )

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
