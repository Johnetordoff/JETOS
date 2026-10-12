"""Python-facing JETOS native runtime.

Qualified packaged runtimes compile and import ``_jetos_native``. The fallback
keeps source inspection and host-side diagnostics usable before that build step.
"""
from __future__ import annotations

try:
    from ._jetos_native import NativeBuffer, xor_bytes
except ImportError:
    ACCELERATED = False
    BACKEND = "python-fallback"

    class NativeBuffer:
        """Compatibility fallback for the C-backed runtime object."""

        def __init__(self, size: int) -> None:
            if size < 0:
                raise ValueError("size must be non-negative")
            self._data = bytearray(size)

        @property
        def size(self) -> int:
            return len(self._data)

        def __len__(self) -> int:
            return len(self._data)

        def fill(self, value: int) -> None:
            if not 0 <= value <= 255:
                raise ValueError("fill value must be between 0 and 255")
            self._data[:] = bytes((value,)) * len(self._data)

        def copy_from(self, data: bytes | bytearray | memoryview) -> None:
            view = bytes(data)
            if len(view) != len(self._data):
                raise ValueError(
                    f"source length {len(view)} does not match buffer size {len(self._data)}"
                )
            self._data[:] = view

        def to_bytes(self) -> bytes:
            return bytes(self._data)

        def checksum64(self) -> int:
            value = 1469598103934665603
            for byte in self._data:
                value ^= byte
                value = (value * 1099511628211) & ((1 << 64) - 1)
            return value

    def xor_bytes(data: bytes | bytearray | memoryview, key: int) -> bytes:
        if not 0 <= key <= 255:
            raise ValueError("key must be between 0 and 255")
        return bytes(byte ^ key for byte in bytes(data))
else:
    ACCELERATED = True
    BACKEND = "c-extension"


def require_accelerated() -> None:
    """Fail qualification if the compiled target-native extension is absent."""
    if not ACCELERATED:
        raise RuntimeError("JETOS compiled native C extension is not active")


__all__ = [
    "ACCELERATED",
    "BACKEND",
    "NativeBuffer",
    "require_accelerated",
    "xor_bytes",
]
