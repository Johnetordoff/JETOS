#!/usr/bin/env python3
"""Run the Apple-Silicon/arm64 JetOS Green Gate and emit evidence.

A PASS requires a fresh source-built arm64 JetLang, fresh arm64 JetOS kernel,
fresh Fat qualification image, and a QEMU arm64 boot that reaches the in-guest
Green marker emitted only after stdlib and guest qualification succeed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import green_gate as common

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
KERNEL = BUILD / "linux/arch/arm64/boot/Image"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"
DEFAULT_EVIDENCE = BUILD / "m1-green-gate.json"
GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"
REQUIRED_TOOLS = (
    "git", "ld", "make", "bc", "bison", "flex", "pahole", "pkg-config",
    "qemu-system-aarch64",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def preflight() -> dict[str, object]:
    if platform.system() != "Linux":
        raise RuntimeError(
            "M1 Green Gate executes in the Linux/arm64 development environment; "
            f"got {platform.system()}"
        )
    machine = platform.machine().lower()
    if machine not in {"arm64", "aarch64"}:
        raise RuntimeError(f"M1 Green Gate requires arm64 execution; got {machine}")
    missing_sources = [
        label for path, label in common.REQUIRED_SOURCES.items() if not path.is_file()
    ]
    if missing_sources:
        raise RuntimeError("missing required source trees: " + ", ".join(missing_sources))
    tools = {name: shutil.which(name) for name in REQUIRED_TOOLS}
    missing_tools = [name for name, path in tools.items() if path is None]
    if missing_tools:
        raise RuntimeError("missing M1 Green-Gate host tools: " + ", ".join(missing_tools))
    compiler, configured_cc = common.compiler_command()
    return {
        "system": platform.system(),
        "machine": machine,
        "python": platform.python_version(),
        "tools": tools,
        "compiler": compiler,
        "configured_cc": configured_cc,
        "kvm": common.kvm_usable(),
    }


def qemu_command() -> list[str]:
    if not KERNEL.is_file():
        raise RuntimeError(f"fresh arm64 kernel missing after build: {KERNEL}")
    if not INITRAMFS.is_file():
        raise RuntimeError(f"fresh initramfs missing after build: {INITRAMFS}")
    qemu = shutil.which("qemu-system-aarch64")
    if qemu is None:
        raise RuntimeError("qemu-system-aarch64 disappeared after preflight")
    build_tool = common.load_build_tool()
    memory = build_tool.initramfs_vm_memory(INITRAMFS)
    kvm = common.kvm_usable()
    accel = "kvm" if kvm else "tcg"
    cpu = "host" if kvm else "max"
    return [
        qemu,
        "-accel", accel,
        "-machine", "virt",
        "-cpu", cpu,
        "-m", memory,
        "-kernel", str(KERNEL),
        "-initrd", str(INITRAMFS),
        "-append", "console=ttyAMA0 rdinit=/init panic=-1",
        "-nic", "none",
        "-nographic",
        "-no-reboot",
    ]


def run_gate(*, evidence_path: Path, build_timeout: int, boot_timeout: int) -> int:
    evidence: dict[str, object] = {
        "schema_version": 1,
        "gate": "m1-linux-arm64-green",
        "status": "RUNNING",
        "started_at": utc_now(),
        "green_marker": GREEN_MARKER,
        "stages": {},
    }
    try:
        if BUILD.exists():
            shutil.rmtree(BUILD)
        evidence["revision"] = common.revision()
        evidence["host"] = preflight()
        common.write_evidence(evidence_path, evidence)

        tests_rc, _, tests_tail, tests_timeout = common.run_stream(
            [sys.executable, "jetos.py", "test"], timeout=build_timeout
        )
        evidence["stages"]["repository_tests"] = {
            "returncode": tests_rc, "timed_out": tests_timeout, "tail": tests_tail,
        }
        if tests_timeout or tests_rc != 0:
            raise RuntimeError("repository-native test stage failed")

        build_rc, _, build_tail, build_timeout_hit = common.run_stream(
            [sys.executable, "tools/dev.py", "build"], timeout=build_timeout
        )
        evidence["stages"]["fresh_build"] = {
            "returncode": build_rc,
            "timed_out": build_timeout_hit,
            "kernel": str(KERNEL.relative_to(ROOT)),
            "initramfs": str(INITRAMFS.relative_to(ROOT)),
            "tail": build_tail,
        }
        if build_timeout_hit or build_rc != 0:
            raise RuntimeError("fresh arm64 JetLang/kernel/Fat build failed")
        # tools/dev.py clears .build on a fresh revision, which removes the
        # RUNNING record written above. Re-record before the long guest stage.
        common.write_evidence(evidence_path, evidence)

        command = qemu_command()
        boot_rc, marker_seen, boot_tail, boot_timeout_hit = common.run_stream(
            command, timeout=boot_timeout, marker=GREEN_MARKER
        )
        evidence["stages"]["qemu_guest"] = {
            "returncode_after_stop": boot_rc,
            "timed_out": boot_timeout_hit,
            "marker_seen": marker_seen,
            "command": command,
            "tail": boot_tail,
        }
        if not marker_seen:
            reason = "QEMU boot timed out" if boot_timeout_hit else "QEMU exited before Green marker"
            raise RuntimeError(reason)

        evidence["status"] = "PASS"
        evidence["finished_at"] = utc_now()
        common.write_evidence(evidence_path, evidence)
        print(GREEN_MARKER)
        print(f"M1 Green Gate evidence: {evidence_path}")
        return 0
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["finished_at"] = utc_now()
        evidence["failure"] = str(exc)
        common.write_evidence(evidence_path, evidence)
        print(f"JETOS_M1_GREEN_GATE=FAIL: {exc}", file=sys.stderr)
        print(f"M1 Green Gate evidence: {evidence_path}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--build-timeout", type=int, default=10800)
    parser.add_argument("--boot-timeout", type=int, default=10800)
    args = parser.parse_args()
    return run_gate(
        evidence_path=args.evidence,
        build_timeout=args.build_timeout,
        boot_timeout=args.boot_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
