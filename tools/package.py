#!/usr/bin/env python3
"""Build Fat or Skinny JETOS rootfs/initramfs artifacts."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD_TOOL = ROOT / "tools/build.py"
NATIVE_TOOL = ROOT / "tools/native.py"
STDLIB_TOOL = ROOT / "tools/stdlib_qualify.py"


def load_tool(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load JETOS tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load_tool("jetos_build", BUILD_TOOL)
native_build = load_tool("jetos_native_build", NATIVE_TOOL)
sys.path.insert(0, str(ROOT / "src"))
from jetos import mode as deployment_mode  # noqa: E402


def copy_source_tree(source: Path, target: Path, required: Path) -> Path:
    source = source.resolve()
    if not (source / required).is_file():
        raise SystemExit(f"incomplete source tree {source}: missing {required}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".build", "__pycache__"),
    )
    return target


def copy_linux_source(source: Path, rootfs: Path) -> Path:
    return copy_source_tree(source, rootfs / "usr/src/linux", Path("Makefile"))


def copy_cpython_source(source: Path, rootfs: Path) -> Path:
    return copy_source_tree(
        source,
        rootfs / "usr/src/jetos-language",
        Path("Python/sysmodule.c"),
    )


def copy_jetos_source(rootfs: Path) -> Path:
    target = rootfs / "usr/src/jetos"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        ROOT,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".build",
            "vendor",
            "__pycache__",
        ),
    )
    return target


def install_mode_sources(
    selected_mode: str,
    rootfs: Path,
    linux_source: Path,
    cpython_source: Path,
) -> dict[str, str]:
    source_root = rootfs / "usr/src"
    if deployment_mode.normalize(selected_mode) == deployment_mode.SKINNY:
        if source_root.exists():
            shutil.rmtree(source_root)
        return {}

    installed = {
        "jetos": str(copy_jetos_source(rootfs).relative_to(rootfs)),
        "jetos_language": str(copy_cpython_source(cpython_source, rootfs).relative_to(rootfs)),
        "linux": str(copy_linux_source(linux_source, rootfs).relative_to(rootfs)),
    }
    return installed


def install_stdlib_qualification(rootfs: Path, mode: str | None = None) -> Path:
    target = rootfs / "jetos/tools/stdlib_qualify.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STDLIB_TOOL, target)
    marker = rootfs / "jetos/stdlib-qualify"
    marker.unlink(missing_ok=True)
    if mode is not None:
        marker.write_text(mode + "\n", encoding="utf-8")
    return target


def install_native_runtime(rootfs: Path, python: Path) -> Path:
    package = rootfs / "jetos/src/jetos"
    extension = native_build.build(package, python)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(rootfs / "jetos/src")
    subprocess.run(
        [
            str(python),
            "-c",
            (
                "from jetos.native import BACKEND,require_accelerated;"
                "require_accelerated();"
                "assert BACKEND == 'c-extension';"
                "print('JETOS native runtime:', BACKEND)"
            ),
        ],
        check=True,
        env=env,
    )
    return extension


def write_mode_manifest(
    rootfs: Path,
    selected_mode: str,
    extension: Path,
    sources: dict[str, str],
) -> Path:
    selected = deployment_mode.policy(selected_mode)
    manifest = {
        "mode": selected.name,
        "carries_complete_source": selected.carries_complete_source,
        "target_resolved": selected.target_resolved,
        "compiled_native_runtime_required": selected.requires_compiled_native_runtime,
        "native_extension": extension.name,
        "native_backend": "c-extension",
        "source_trees": sources,
    }
    target = rootfs / "jetos/image-mode.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    python, stdlib = build.defaults()
    parser = argparse.ArgumentParser(description="Package Fat or Skinny JETOS")
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=python)
    parser.add_argument("--stdlib", type=Path, default=stdlib)
    parser.add_argument("--mode", choices=deployment_mode.MODES, default=deployment_mode.FAT)
    parser.add_argument("--linux-source", type=Path, default=ROOT / "vendor/linux")
    parser.add_argument("--cpython-source", type=Path, default=ROOT / "vendor/cpython")
    parser.add_argument(
        "--stdlib-qualify",
        choices=("fast", "full"),
        help="arm this image to run stdlib qualification during first boot",
    )
    args = parser.parse_args()

    build.make_rootfs(args.rootfs, args.python, args.stdlib)
    extension = install_native_runtime(args.rootfs, args.python)
    sources = install_mode_sources(
        args.mode,
        args.rootfs,
        args.linux_source,
        args.cpython_source,
    )
    install_stdlib_qualification(args.rootfs, args.stdlib_qualify)
    manifest = write_mode_manifest(args.rootfs, args.mode, extension, sources)
    build.build_initramfs(args.rootfs, args.output)

    print(f"JETOS mode: {deployment_mode.normalize(args.mode)}")
    print(f"native runtime: {extension.relative_to(args.rootfs)}")
    print(f"mode manifest: {manifest.relative_to(args.rootfs)}")
    if sources:
        for name, path in sources.items():
            print(f"Fat source {name}: {path}")
    else:
        print("Skinny source policy: bulk development source omitted")
    if args.stdlib_qualify:
        print(f"guest stdlib qualification armed: {args.stdlib_qualify}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
