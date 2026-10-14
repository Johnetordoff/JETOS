#!/usr/bin/env python3
"""Fast packaging checks for Fat/Skinny source and qualification boundaries."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_package",
    ROOT / "tools/package.py",
)
assert SPEC and SPEC.loader
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def fake_make_rootfs(rootfs: Path, python: Path, stdlib: Path) -> None:
    del python, stdlib
    if rootfs.exists():
        shutil.rmtree(rootfs)
    (rootfs / "jetos").mkdir(parents=True)
    (rootfs / "runtime-marker").write_text("runtime\n", encoding="utf-8")
    # Deliberately stage both plausible locations. Skinny packaging must remove
    # them even if a future rootfs builder accidentally copies development junk.
    (rootfs / package.TEMPORARY_BULLSHIT_DIRNAME).mkdir()
    (rootfs / package.TEMPORARY_BULLSHIT_DIRNAME / "count_loc.py").write_text(
        "temporary\n", encoding="utf-8"
    )
    (rootfs / "jetos" / package.TEMPORARY_BULLSHIT_DIRNAME).mkdir()
    (rootfs / "jetos" / package.TEMPORARY_BULLSHIT_DIRNAME / "report.txt").write_text(
        "temporary\n", encoding="utf-8"
    )


def fake_build_initramfs(rootfs: Path, output: Path) -> None:
    assert (rootfs / "runtime-marker").is_file()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"jetos-test-initramfs")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        source = temp / "linux"
        rootfs = temp / "rootfs"
        output = temp / "image.cpio.gz"
        runtime = temp / "python"
        stdlib = temp / "stdlib"
        runtime.write_text("runtime\n", encoding="utf-8")
        stdlib.mkdir()
        (source / "drivers/example").mkdir(parents=True)
        (source / "Makefile").write_text("VERSION = 6\n", encoding="utf-8")
        (source / "README").write_text("Linux source\n", encoding="utf-8")
        (source / "drivers/example/test.c").write_text(
            "int jetos_linux_source_test;\n",
            encoding="utf-8",
        )
        (source / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")

        target = package.copy_linux_source(source, rootfs)
        assert target == rootfs / "usr/src/linux"
        assert (target / "Makefile").read_text(encoding="utf-8") == "VERSION = 6\n"
        assert (target / "README").is_file()
        assert (target / "drivers/example/test.c").is_file()
        assert not (target / ".git").exists()

        tool = package.install_stdlib_qualification(rootfs)
        assert tool == rootfs / "jetos/tools/stdlib_qualify.py"
        assert tool.is_file()
        assert not (rootfs / "jetos/stdlib-qualify").exists()

        package.install_stdlib_qualification(rootfs, "fast")
        assert (rootfs / "jetos/stdlib-qualify").read_text(encoding="utf-8") == "fast\n"

        package.install_stdlib_qualification(rootfs, "full")
        assert (rootfs / "jetos/stdlib-qualify").read_text(encoding="utf-8") == "full\n"

        original_make_rootfs = package.build.make_rootfs
        original_build_initramfs = package.build.build_initramfs
        package.build.make_rootfs = fake_make_rootfs
        package.build.build_initramfs = fake_build_initramfs
        try:
            package.package_rootfs(
                profile=package.PROFILE_FAT,
                rootfs=rootfs,
                output=output,
                python=runtime,
                stdlib=stdlib,
                linux_source=source,
                stdlib_qualify="fast",
            )
            assert (rootfs / "usr/src/linux/Makefile").is_file()
            assert (rootfs / "jetos/tools/stdlib_qualify.py").is_file()
            assert (rootfs / "jetos/stdlib-qualify").read_text(encoding="utf-8") == "fast\n"
            assert (rootfs / package.TEMPORARY_BULLSHIT_DIRNAME).is_dir()
            assert (rootfs / "jetos" / package.TEMPORARY_BULLSHIT_DIRNAME).is_dir()

            package.package_rootfs(
                profile=package.PROFILE_SKINNY,
                rootfs=rootfs,
                output=output,
                python=runtime,
                stdlib=stdlib,
                linux_source=source,
                stdlib_qualify=None,
            )
            assert (rootfs / "runtime-marker").is_file()
            assert not (rootfs / "usr/src/linux").exists()
            assert not (rootfs / "jetos/tools/stdlib_qualify.py").exists()
            assert not (rootfs / "jetos/stdlib-qualify").exists()
            assert not (rootfs / package.TEMPORARY_BULLSHIT_DIRNAME).exists()
            assert not (rootfs / "jetos" / package.TEMPORARY_BULLSHIT_DIRNAME).exists()
            assert output.read_bytes() == b"jetos-test-initramfs"

            try:
                package.package_rootfs(
                    profile=package.PROFILE_SKINNY,
                    rootfs=rootfs,
                    output=output,
                    python=runtime,
                    stdlib=stdlib,
                    linux_source=source,
                    stdlib_qualify="full",
                )
            except SystemExit:
                pass
            else:
                raise AssertionError("Skinny profile accepted Fat qualification tooling")
        finally:
            package.build.make_rootfs = original_make_rootfs
            package.build.build_initramfs = original_build_initramfs

    print("JETOS Fat/Skinny packaging tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
