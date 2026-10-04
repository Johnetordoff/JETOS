"""JETOS Dunicode v0.2.

Dunicode is a reversible JETOS character layer over Unicode scalar values.
Version 0.2 also permits a current encoder to retire a character without
destroying the ability to decode historical data that contains it.
"""
from __future__ import annotations

DUNICODE_VERSION = "0.2"


class RemovedCharacterError(ValueError):
    """A scalar is valid historically but retired from current encoding."""


def _validate_scalar(value: int) -> int:
    if not isinstance(value, int):
        raise TypeError("Dunicode scalar must be an int")
    if value < 0 or value > 0x10FFFF:
        raise ValueError(f"Dunicode scalar out of range: {value!r}")
    if 0xD800 <= value <= 0xDFFF:
        raise ValueError(f"Dunicode surrogate scalar is invalid: {value:#x}")
    return value


def encode(text: str, *, removed: frozenset[int] = frozenset()) -> bytes:
    """Encode current Dunicode text as strict UTF-8.

    A removed scalar is rejected for new encoding, while decode() remains able
    to read historical bytes containing it. Removal is a repertoire/policy
    operation, not destructive reassignment of the character.
    """
    if not isinstance(text, str):
        raise TypeError("Dunicode text must be str")
    for value in codepoints(text):
        if value in removed:
            raise RemovedCharacterError(
                f"{label(value)} is retired from the current Dunicode encoder"
            )
    return text.encode("utf-8", "strict")


def decode(data: bytes | bytearray | memoryview) -> str:
    """Decode historical/current UTF-8 without applying removal policy."""
    return bytes(data).decode("utf-8", "strict")


def codepoints(text: str) -> tuple[int, ...]:
    if not isinstance(text, str):
        raise TypeError("Dunicode text must be str")
    values = tuple(ord(char) for char in text)
    for value in values:
        _validate_scalar(value)
    return values


def from_codepoints(values: object) -> str:
    return "".join(
        chr(_validate_scalar(value))
        for value in values  # type: ignore[union-attr]
    )


def label(value: int) -> str:
    value = _validate_scalar(value)
    width = max(4, len(f"{value:X}"))
    return f"D+{value:0{width}X}"


def labels(text: str) -> tuple[str, ...]:
    return tuple(label(value) for value in codepoints(text))
