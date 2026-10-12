#!/usr/bin/env python3
"""Build and exercise the JETOS CPython C-extension spine."""
from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_native_build", ROOT / "tools/native.py")
assert SPEC and SPEC.loader
native_build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native_build)


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        package = root / "jetos"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        shutil.copy2(ROOT / "src/jetos/native.py", package / "native.py")
        extension = native_build.build(package)
        assert extension.is_file()

        sys.path.insert(0, str(root))
        try:
            module = importlib.import_module("jetos.native")
            assert module.ACCELERATED is True
            assert module.BACKEND == "c-extension"
            module.require_accelerated()

            buffer = module.NativeBuffer(4)
            assert len(buffer) == 4
            assert buffer.size == 4
            buffer.fill(0x41)
            assert buffer.to_bytes() == b"AAAA"
            first_checksum = buffer.checksum64()
            buffer.copy_from(b"ABCD")
            assert buffer.to_bytes() == b"ABCD"
            assert buffer.checksum64() != first_checksum
            assert module.xor_bytes(b"abc", 0x20) == b"ABC"
        finally:
            sys.path.remove(str(root))
            for name in list(sys.modules):
                if name == "jetos" or name.startswith("jetos."):
                    sys.modules.pop(name, None)

    print("JETOS native extension tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
