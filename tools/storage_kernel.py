#!/usr/bin/env python3
"""Patch/check Linux Kconfig for JETOS encrypted persistent storage."""
from __future__ import annotations

import argparse
from pathlib import Path


REQUIREMENTS = {
    "CONFIG_BLK_DEV_DM": "y",
    "CONFIG_DM_CRYPT": "y",
    "CONFIG_CRYPTO_AES": "y",
    "CONFIG_CRYPTO_XTS": "y",
}


def read_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
        elif raw.startswith("# CONFIG_") and raw.endswith(" is not set"):
            values[raw[2:-11]] = "n"
    return values


def failures(path: Path) -> tuple[str, ...]:
    values = read_config(path)
    return tuple(
        f"{key}={values.get(key, 'missing')} (need {wanted})"
        for key, wanted in REQUIREMENTS.items()
        if values.get(key) != wanted
    )


def patch(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        key: str | None = None
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]

        if key in REQUIREMENTS:
            if key not in seen:
                output.append(f"{key}={REQUIREMENTS[key]}")
                seen.add(key)
        else:
            output.append(line)

    for key, value in REQUIREMENTS.items():
        if key not in seen:
            output.append(f"{key}={value}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JETOS dm-crypt kernel configuration policy"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "patch"):
        command = sub.add_parser(name)
        command.add_argument("config", type=Path)
    args = parser.parse_args()

    if args.command == "patch":
        patch(args.config)

    problems = failures(args.config)
    if problems:
        print("JETOS encrypted-storage kernel profile: FAIL")
        for problem in problems:
            print(" ", problem)
        return 1

    print("JETOS encrypted-storage kernel profile: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
