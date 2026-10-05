#!/usr/bin/env python3
"""Fast tests for the lean runtime-image profile."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_image", ROOT / "tools/image.py")
assert SPEC and SPEC.loader
image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(image)


def touch(path: Path, data: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        stdlib = Path("/usr/lib/python3.14")
        target = root / stdlib.relative_to("/")
        touch(target / "tkinter/__init__.py")
        touch(target / "json/__init__.py")
        touch(target / "test/test_os.py", b"test")
        touch(target / "idlelib/idle.py", b"idle")
        touch(target / "ensurepip/__init__.py", b"pip")
        touch(target / "json/__pycache__/decoder.pyc", b"cache")

        removed_files, removed_bytes = image.compact_stdlib(root, stdlib)
        assert removed_files == 4, removed_files
        checks += 1
        assert removed_bytes == len(b"testidlepipcache")
        checks += 1
        assert (target / "tkinter/__init__.py").exists()
        checks += 1
        assert (target / "json/__init__.py").exists()
        checks += 1
        assert not (target / "test").exists()
        checks += 1
        assert not (target / "idlelib").exists()
        checks += 1
        assert not (target / "ensurepip").exists()
        checks += 1
        assert not (target / "json/__pycache__").exists()
        checks += 1

    print(f"JETOS lean image profile: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
