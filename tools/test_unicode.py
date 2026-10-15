#!/usr/bin/env python3
"""JETOS Dunicode / Unicode behavior tests."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unicodedata

# Test the checkout's own package on a plain host, not only where the Docker
# image sets PYTHONPATH=/jetos/src.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jetos import dunicode  # noqa: E402

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
        encoded = dunicode.encode(text)
        check(dunicode.decode(encoded) == text, f"round trip failed: {text!r}")
        check(
            dunicode.from_codepoints(dunicode.codepoints(text)) == text,
            f"scalar round trip failed: {text!r}",
        )
        checks += 2

    check(dunicode.DUNICODE_VERSION == "0.2", "version")
    check(dunicode.label(ord("A")) == "D+0041", "ASCII label")
    check(dunicode.label(ord("🧪")) == "D+1F9EA", "emoji label")
    check(
        dunicode.labels("A🧪") == ("D+0041", "D+1F9EA"),
        "label sequence",
    )
    checks += 4

    for bad in (-1, 0xD800, 0xDFFF, 0x110000):
        try:
            dunicode.from_codepoints([bad])
        except ValueError:
            checks += 1
        else:
            raise AssertionError(f"invalid scalar accepted: {bad:#x}")

    composed = "é"
    decomposed = "e\u0301"
    check(composed != decomposed, "normalization test setup")
    check(
        unicodedata.normalize("NFC", decomposed) == composed,
        "NFC sanity",
    )
    check(
        dunicode.decode(dunicode.encode(decomposed)) == decomposed,
        "Dunicode silently normalized",
    )
    checks += 3

    try:
        dunicode.decode(b"\xff\xfe\xfa")
    except UnicodeDecodeError:
        checks += 1
    else:
        raise AssertionError("malformed UTF-8 accepted")

    # Retirement affects new encoding, not historical decoding. This is the
    # Dunicode behavior that lets a convention remove a character cleanly.
    pistol = "🔫"
    historical = dunicode.encode(pistol)
    removed = frozenset({ord(pistol)})
    check(dunicode.decode(historical) == pistol, "historical decode changed")
    checks += 1

    try:
        dunicode.encode(pistol, removed=removed)
    except dunicode.RemovedCharacterError:
        checks += 1
    else:
        raise AssertionError("retired Dunicode scalar was re-encoded")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        filename = "café-漢字-🧪.txt"
        path = root / filename
        payload = "Dunicode ↔ Unicode ↔ UTF-8\n"
        path.write_text(payload, encoding="utf-8")
        check(path.read_text(encoding="utf-8") == payload, "filesystem text")
        check(filename in os.listdir(root), "Unicode filename")
        checks += 2

        if os.name == "posix":
            raw_name = b"raw-\xff-name"
            root_bytes = os.fsencode(root)
            fd = os.open(
                root_bytes + b"/" + raw_name,
                os.O_WRONLY | os.O_CREAT,
                0o600,
            )
            os.write(fd, b"raw")
            os.close(fd)
            check(raw_name in os.listdir(root_bytes), "raw filename bytes")
            checks += 1

    check(
        sys.getfilesystemencoding().lower() == "utf-8",
        "filesystem encoding is not UTF-8",
    )
    checks += 1

    print(f"JETOS Dunicode / Unicode: {checks} checks passed")
    print(f"Dunicode version: {dunicode.DUNICODE_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
