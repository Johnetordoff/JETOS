#!/usr/bin/env python3
"""JETOS Dona Code / Unicode smoke tests."""
from __future__ import annotations

import os
import sys
import tempfile
import unicodedata
from pathlib import Path


CASES = [
    "ASCII",
    "café",
    "Ελληνικά",
    "Кириллица",
    "العربية",
    "עברית",
    "देवनागरी",
    "漢字かな交じり文",
    "emoji: 🧪🚀",
    "supplementary: 𐐷",
    "combining: e\u0301",
    "variation: ✈️",
    "zero-width: a\u200db",
]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    checks = 0

    for text in CASES:
        encoded = text.encode("utf-8")
        decoded = encoded.decode("utf-8")
        check(decoded == text, f"UTF-8 round trip failed: {text!r}")
        checks += 1

    composed = "é"
    decomposed = "e\u0301"
    check(composed != decomposed, "test setup should use distinct code-point sequences")
    check(
        unicodedata.normalize("NFC", decomposed) == composed,
        "NFC normalization sanity check failed",
    )
    check(
        decomposed.encode("utf-8").decode("utf-8") == decomposed,
        "JETOS must preserve source Unicode sequence without implicit normalization",
    )
    checks += 3

    bad = b"\xff\xfe\xfa"
    try:
        bad.decode("utf-8")
    except UnicodeDecodeError:
        checks += 1
    else:
        raise AssertionError("malformed UTF-8 was silently accepted")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        filename = "café-漢字-🧪.txt"
        p = root / filename
        payload = "Dona Code → Unicode → UTF-8\n"
        p.write_text(payload, encoding="utf-8")
        check(p.read_text(encoding="utf-8") == payload, "Unicode filesystem I/O failed")
        check(filename in os.listdir(root), "Unicode filename did not round-trip")
        checks += 2

        if os.name == "posix":
            raw_name = b"raw-\xff-name"
            root_bytes = os.fsencode(root)
            fd = os.open(root_bytes + b"/" + raw_name, os.O_WRONLY | os.O_CREAT, 0o600)
            os.write(fd, b"raw")
            os.close(fd)
            names = os.listdir(root_bytes)
            check(raw_name in names, "arbitrary POSIX filename bytes did not round-trip")
            checks += 1

    check(sys.getfilesystemencoding().lower() == "utf-8", "filesystem encoding is not UTF-8")
    checks += 1

    print(f"JETOS Dona Code / Unicode: {checks} checks passed")
    print(f"filesystem encoding: {sys.getfilesystemencoding()}")
    print(f"default encoding: {sys.getdefaultencoding()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
