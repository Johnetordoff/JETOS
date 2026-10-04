"""JETOS Dunicode v0.1.

Dunicode v0.1 is a deliberately reversible JETOS character layer:
each Dunicode scalar maps 1:1 to a Unicode scalar value, and text
serializes as strict UTF-8.
"""
from __future__ import annotations

DUNICODE_VERSION = "0.1"


def _validate_scalar(value: int) -> int:
    if not isinstance(value, int):
        raise TypeError("Dunicode scalar must be an int")
    if value < 0 or value > 0x10FFFF:
        raise ValueError(f"Dunicode scalar out of range: {value!r}")
    if 0xD800 <= value <= 0xDFFF:
        raise ValueError(f"Dunicode surrogate scalar is invalid: {value:#x}")
    return value


def encode(text: str) -> bytes:
    """Encode Dunicode/Unicode text as strict UTF-8."""
    if not isinstance(text, str):
        raise TypeError("Dunicode text must be str")
    return text.encode("utf-8", "strict")


def decode(data: bytes | bytearray | memoryview) -> str:
    """Decode strict UTF-8 into Dunicode/Unicode text."""
    return bytes(data).decode("utf-8", "strict")


def codepoints(text: str) -> tuple[int, ...]:
    """Return the Dunicode scalar sequence for text."""
    if not isinstance(text, str):
        raise TypeError("Dunicode text must be str")
    values = tuple(ord(char) for char in text)
    for value in values:
        _validate_scalar(value)
    return values


def from_codepoints(values: object) -> str:
    """Construct text from an iterable of Dunicode scalar values."""
    return "".join(chr(_validate_scalar(value)) for value in values)  # type: ignore[arg-type]


def label(value: int) -> str:
    """Format a Dunicode scalar using D+ hexadecimal notation."""
    value = _validate_scalar(value)
    width = max(4, len(f"{value:X}"))
    return f"D+{value:0{width}X}"


def labels(text: str) -> tuple[str, ...]:
    """Return D+ labels for every scalar in text."""
    return tuple(label(value) for value in codepoints(text))
