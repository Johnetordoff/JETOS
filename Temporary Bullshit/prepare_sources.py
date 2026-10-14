#!/usr/bin/env python3
"""Initialize the pinned JETOS Linux and JetLang source trees."""
from __future__ import annotations

from common import prepare_sources


def main() -> int:
    prepare_sources()
    print("JETOS source submodules initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
