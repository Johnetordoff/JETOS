#!/usr/bin/env python3
"""Run the Apple-Silicon/arm64 JetOS Green Gate and emit evidence.

A PASS requires a fresh source-built arm64 JetLang, fresh arm64 JetOS kernel,
fresh Fat qualification image, and a QEMU arm64 boot that reaches the in-guest
Green marker emitted only after stdlib and guest qualification succeed.

The gate has two stages so an M1 can use its own hypervisor:

* ``build`` runs in the Linux/arm64 build environment (normally the Docker
  harness): repository tests plus the fresh JetLang/kernel/Fat build. It
  records the exact revision and the SHA-256 of the kernel and initramfs.
* ``boot`` boots exactly those recorded artifacts. On an Apple-Silicon Mac it
  runs natively with Hypervisor.framework (``-accel hvf -cpu host``), which a
  Docker Desktop Linux VM on M1 cannot offer (no nested KVM), so the guest
  runs at native speed instead of under TCG emulation and is not limited by
  the Docker VM's memory allowance. On Linux/arm64 it uses KVM when usable.

``all`` (the default) runs both stages in one Linux/arm64 process, as before.
Docker stays a build harness only; it never defines the kernel or JetLang.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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
BUILT_STATUS = "BUILT"
BOOT_FAIL_STATUS = "BOOT_FAIL"
BOOTABLE_STATUSES = {BUILT_STATUS, BOOT_FAIL_STATUS}
ARM64_MACHINES = {"arm64", "aarch64"}
STAGES = ("all", "build", "boot")
REQUIRED_TOOLS = (
    "git", "ld", "make", "bc", "bison", "flex", "pahole", "pkg-config",
    "qemu-system-aarch64",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def host_machine() -> str:
    return platform.machine().lower()


def preflight() -> dict[str, object]:
    """Check the Linux/arm64 environment that builds the fresh artifacts."""
    if platform.system() != "Linux":
        raise RuntimeError(
            "M1 Green Gate executes in the Linux/arm64 development environment; "
            f"got {platform.system()}"
        )
    machine = host_machine()
    if machine not in ARM64_MACHINES:
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


def hvf_available(qemu: str) -> bool:
    """Return whether this QEMU build offers Hypervisor.framework."""
    try:
        result = subprocess.run(
            [qemu, "-accel", "help"],
            check=False,
            text=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.strip() == "hvf" for line in result.stdout.splitlines())


def accelerator(qemu: str) -> tuple[str, str]:
    """Pick the fastest accelerator that can run an arm64 guest on this host.

    Hardware acceleration needs an arm64 host: an arm64 guest is never run
    under HVF/KVM on another ISA, and nothing is inferred across hosts.
    """
    if host_machine() in ARM64_MACHINES:
        system = platform.system()
        if system == "Darwin" and hvf_available(qemu):
            return "hvf", "host"
        if system == "Linux" and common.kvm_usable():
            return "kvm", "host"
    return "tcg", "max"


def qemu_command(memory: str | None = None) -> list[str]:
    if not KERNEL.is_file():
        raise RuntimeError(f"fresh arm64 kernel missing after build: {KERNEL}")
    if not INITRAMFS.is_file():
        raise RuntimeError(f"fresh initramfs missing after build: {INITRAMFS}")
    qemu = shutil.which("qemu-system-aarch64")
    if qemu is None:
        raise RuntimeError("qemu-system-aarch64 is not installed on this host")
    if memory is None:
        memory = common.load_build_tool().initramfs_vm_memory(INITRAMFS)
    accel, cpu = accelerator(qemu)
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_record() -> dict[str, object]:
    return {
        name: {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for name, path in (("kernel", KERNEL), ("initramfs", INITRAMFS))
    }


def build_stage(evidence: dict[str, object], evidence_path: Path, build_timeout: int) -> None:
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
    if not KERNEL.is_file() or not INITRAMFS.is_file():
        raise RuntimeError("fresh arm64 build did not produce both kernel and initramfs")
    evidence["artifacts"] = artifact_record()
    evidence["vm_memory"] = common.load_build_tool().initramfs_vm_memory(INITRAMFS)
    # tools/dev.py clears .build on a fresh revision, which removes the
    # RUNNING record written above. Re-record before the long guest stage.
    common.write_evidence(evidence_path, evidence)


def load_built_evidence(evidence_path: Path) -> dict[str, object]:
    """Load a build-stage record and prove it still describes these files."""
    if not evidence_path.is_file():
        raise RuntimeError(f"no M1 build-stage evidence at {evidence_path}; run --stage build first")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("status") not in BOOTABLE_STATUSES:
        raise RuntimeError(
            f"M1 build-stage evidence status is {evidence.get('status')!r}; "
            f"expected one of {sorted(BOOTABLE_STATUSES)}"
        )
    current = common.revision()
    if evidence.get("revision") != current:
        raise RuntimeError(
            f"M1 artifacts were built from {evidence.get('revision')}, not the current revision {current}"
        )
    if evidence.get("artifacts") != artifact_record():
        raise RuntimeError("M1 kernel/initramfs changed since the build stage recorded them")
    evidence.setdefault("stages", {})
    evidence.pop("failure", None)
    return evidence


def boot_stage(evidence: dict[str, object], boot_timeout: int) -> None:
    memory = evidence.get("vm_memory")
    command = qemu_command(memory if isinstance(memory, str) else None)
    evidence["boot_host"] = {
        "system": platform.system(),
        "machine": host_machine(),
        "release": platform.release(),
        "python": platform.python_version(),
        "accel": command[command.index("-accel") + 1],
        "cpu": command[command.index("-cpu") + 1],
    }
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


def run_gate(
    *,
    evidence_path: Path,
    build_timeout: int,
    boot_timeout: int,
    stage: str = "all",
) -> int:
    if stage not in STAGES:
        raise ValueError(f"unknown M1 Green Gate stage: {stage!r}")
    evidence: dict[str, object] = {
        "schema_version": 2,
        "gate": "m1-linux-arm64-green",
        "status": "RUNNING",
        "started_at": utc_now(),
        "green_marker": GREEN_MARKER,
        "stages": {},
    }
    artifacts_ready = False
    try:
        if stage == "boot":
            evidence = load_built_evidence(evidence_path)
            evidence["boot_started_at"] = utc_now()
            artifacts_ready = True
        else:
            build_stage(evidence, evidence_path, build_timeout)
            artifacts_ready = True

        if stage == "build":
            evidence["status"] = BUILT_STATUS
            evidence["built_at"] = utc_now()
            common.write_evidence(evidence_path, evidence)
            print("JETOS_M1_ARTIFACTS=BUILT")
            print(f"M1 Green Gate evidence: {evidence_path}")
            return 0

        boot_stage(evidence, boot_timeout)
        evidence["status"] = "PASS"
        evidence["finished_at"] = utc_now()
        common.write_evidence(evidence_path, evidence)
        print(GREEN_MARKER)
        print(f"M1 Green Gate evidence: {evidence_path}")
        return 0
    except Exception as exc:
        # A failed native boot leaves the verified build reusable, so the
        # next boot attempt does not force a multi-hour rebuild.
        evidence["status"] = BOOT_FAIL_STATUS if artifacts_ready else "FAIL"
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
    parser.add_argument("--stage", choices=STAGES, default="all")
    args = parser.parse_args()
    evidence = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    return run_gate(
        evidence_path=evidence,
        build_timeout=args.build_timeout,
        boot_timeout=args.boot_timeout,
        stage=args.stage,
    )


if __name__ == "__main__":
    raise SystemExit(main())
