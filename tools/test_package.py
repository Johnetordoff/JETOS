#!/usr/bin/env python3
"""Fast packaging checks for Fat/Skinny source and runtime policy."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_package", ROOT / "tools/package.py")
assert SPEC and SPEC.loader
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)
        linux = temp / "linux"
        cpython = temp / "cpython"
        rootfs = temp / "rootfs"

        (linux / "drivers/example").mkdir(parents=True)
        (linux / "Makefile").write_text("VERSION = 6\n", encoding="utf-8")
        (linux / "drivers/example/test.c").write_text("int test;\n", encoding="utf-8")
        (linux / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")

        (cpython / "Python").mkdir(parents=True)
        (cpython / "Python/sysmodule.c").write_text("/* cpython */\n", encoding="utf-8")

        fat_sources = package.install_mode_sources("fat", rootfs, linux, cpython)
        assert set(fat_sources) == {"jetos", "jetos_language", "linux"}
        assert (rootfs / "usr/src/linux/Makefile").is_file()
        assert (rootfs / "usr/src/jetos-language/Python/sysmodule.c").is_file()
        assert (rootfs / "usr/src/jetos/native/jetos_native.c").is_file()
        assert not (rootfs / "usr/src/linux/.git").exists()
        assert not (rootfs / "usr/src/jetos/vendor").exists()

        extension = rootfs / "jetos/src/jetos/_jetos_native.test.so"
        extension.parent.mkdir(parents=True, exist_ok=True)
        extension.write_bytes(b"test")
        manifest = package.write_mode_manifest(rootfs, "fat", extension, fat_sources)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["mode"] == "fat"
        assert data["carries_complete_source"] is True
        assert data["compiled_native_runtime_required"] is True
        assert data["native_backend"] == "c-extension"

        skinny_sources = package.install_mode_sources("skinny", rootfs, linux, cpython)
        assert skinny_sources == {}
        assert not (rootfs / "usr/src").exists()
        skinny_manifest = package.write_mode_manifest(rootfs, "skinny", extension, skinny_sources)
        skinny = json.loads(skinny_manifest.read_text(encoding="utf-8"))
        assert skinny["mode"] == "skinny"
        assert skinny["target_resolved"] is True
        assert skinny["source_trees"] == {}

        tool = package.install_stdlib_qualification(rootfs)
        assert tool == rootfs / "jetos/tools/stdlib_qualify.py"
        assert tool.is_file()
        package.install_stdlib_qualification(rootfs, "fast")
        assert (rootfs / "jetos/stdlib-qualify").read_text(encoding="utf-8") == "fast\n"
        package.install_stdlib_qualification(rootfs, "full")
        assert (rootfs / "jetos/stdlib-qualify").read_text(encoding="utf-8") == "full\n"

    print("JETOS packaging tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
