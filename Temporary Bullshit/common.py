#!/usr/bin/env python3
"""Shared helpers for temporary JETOS source-accounting commands."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INVENTORY_TOOL = ROOT / "tools/source_inventory.py"
SOURCE_SUBMODULES = ("source-brain/linux", "source-brain/cpython")


def load_inventory() -> ModuleType:
    spec = importlib.util.spec_from_file_location("jetos_source_inventory", INVENTORY_TOOL)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load inventory tool: {INVENTORY_TOOL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_sources() -> None:
    """Initialize the pinned native source trees efficiently in one Git operation."""
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive", *SOURCE_SUBMODULES],
        cwd=ROOT,
        check=True,
    )


def scan() -> dict:
    return load_inventory().scan(ROOT)


def complete(data: dict) -> bool:
    summary = data["summary"]
    return bool(
        summary["source_brain_linux_initialized"]
        and summary["source_brain_cpython_initialized"]
        and summary["shared_initialized"]
    )


def print_completeness(data: dict) -> None:
    summary = data["summary"]
    print("Linux source initialized:", summary["source_brain_linux_initialized"])
    print("JetLang/CPython-derived source initialized:", summary["source_brain_cpython_initialized"])
    print("Shared source initialized:", summary["shared_initialized"])
    if not complete(data):
        print("WARNING: inventory is partial; initialize all source trees before using it as the global baseline.")
