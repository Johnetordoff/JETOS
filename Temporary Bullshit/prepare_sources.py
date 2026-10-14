#!/usr/bin/env python3
"""Ensure the JETOS Linux and JetLang source trees are present."""
from __future__ import annotations

from common import prepare_sources


def main() -> int:
    prepare_sources()
    print("JETOS source trees are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
