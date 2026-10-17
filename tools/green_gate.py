#!/usr/bin/env python3
"""Run the canonical Linux x86_64 JetOS Green Gate and emit evidence.

This is the executable contract for issue #96. It does not infer success from
static checks. A PASS requires a fresh source-built JetLang, fresh source-built
x86_64 kernel, fresh Fat image, and a QEMU boot that reaches the in-guest Green
marker emitted only after full stdlib/CPython and guest qualification succeed.
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import selectors
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
KERNEL = BUILD / "linux/arch/x86/boot/bzImage"
INITRAMFS = BUILD / "jetos-initramfs.cpio.gz"
DEFAULT_EVIDENCE = BUILD / "green-gate.json"
GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"
TAIL_LINES = 4000

REQUIRED_SOURCES = {
    ROOT / "source/linux/Makefile": "Linux source",
    ROOT / "source/cpython/Python/sysmodule.c": "JetLang/CPython source",
}
REQUIRED_TOOLS = (
    "git",
    "ld",
    "make",
    "bc",
    "bison",
    "flex",
    "pahole",
    "pkg-config",
    "qemu-system-x86_64",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def compiler_command() -> tuple[list[str], str]:
    value = os.environ.get("CC", "cc")
    try:
        command = shlex.split(value)
    except ValueError as exc:
        raise RuntimeError(f"invalid CC command {value!r}: {exc}") from exc
    if not command:
        raise RuntimeError("CC is empty; configure a C compiler command")
    resolved = shutil.which(command[0])
    if resolved is None:
        raise RuntimeError(f"configured C compiler was not found: CC={value!r}")
    return [resolved, *command[1:]], value


def kvm_usable(path: Path = Path("/dev/kvm")) -> bool:
    """Return whether this process can actually open KVM, not merely see it."""
    if not path.exists():
        return False
    try:
        fd = os.open(path, os.O_RDWR)
    except OSError:
        return False
    else:
        os.close(fd)
        return True


def preflight() -> dict[str, object]:
    if platform.system() != "Linux":
        raise RuntimeError(f"Green Gate requires Linux execution; got {platform.system()}")
    machine = platform.machine().lower()
    if machine not in {"x86_64", "amd64"}:
        raise RuntimeError(f"Green Gate requires x86_64 execution; got {machine}")

    missing_sources = [label for path, label in REQUIRED_SOURCES.items() if not path.is_file()]
    if missing_sources:
        raise RuntimeError("missing required source trees: " + ", ".join(missing_sources))

    tools = {name: shutil.which(name) for name in REQUIRED_TOOLS}
    missing_tools = [name for name, path in tools.items() if path is None]
    if missing_tools:
        raise RuntimeError("missing Green-Gate host tools: " + ", ".join(missing_tools))
    compiler, configured_cc = compiler_command()

    return {
        "system": platform.system(),
        "machine": machine,
        "python": platform.python_version(),
        "tools": tools,
        "compiler": compiler,
        "configured_cc": configured_cc,
        "kvm": kvm_usable(),
    }


def write_evidence(path: Path, evidence: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_stream(
    command: list[str],
    *,
    timeout: int,
    marker: str | None = None,
) -> tuple[int | None, bool, list[str], bool]:
    """Stream one process, optionally stopping successfully when marker appears."""
    print("+", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    output: deque[str] = deque(maxlen=TAIL_LINES)
    seen = False
    timed_out = False
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            events = selector.select(timeout=min(1.0, remaining))
            if events:
                line = process.stdout.readline()
                if line:
                    print(line, end="", flush=True)
                    output.append(line.rstrip("\n"))
                    if marker is not None and marker in line:
                        seen = True
                        break
            if process.poll() is not None:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    output.append(line.rstrip("\n"))
                    if marker is not None and marker in line:
                        seen = True
                break
    finally:
        selector.close()

    if seen or timed_out:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    else:
        process.wait()

    return process.returncode, seen, list(output), timed_out


def load_build_tool():
    path = ROOT / "tools/build.py"
    spec = importlib.util.spec_from_file_location("jetos_green_build", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load build helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qemu_command() -> list[str]:
    if not KERNEL.is_file():
        raise RuntimeError(f"fresh kernel missing after build: {KERNEL}")
    if not INITRAMFS.is_file():
        raise RuntimeError(f"fresh initramfs missing after build: {INITRAMFS}")
    qemu = shutil.which("qemu-system-x86_64")
    if qemu is None:
        raise RuntimeError("qemu-system-x86_64 disappeared after preflight")
    build_tool = load_build_tool()
    memory = build_tool.initramfs_vm_memory(INITRAMFS)
    accel = "kvm" if kvm_usable() else "tcg"
    return [
        qemu,
        "-accel", accel,
        "-m", memory,
        "-kernel", str(KERNEL),
        "-initrd", str(INITRAMFS),
        "-append", "console=ttyS0 rdinit=/init panic=-1",
        "-nic", "none",
        "-nographic",
        "-no-reboot",
    ]


def run_gate(*, evidence_path: Path, build_timeout: int, boot_timeout: int) -> int:
    evidence: dict[str, object] = {
        "schema_version": 1,
        "gate": "linux-x86_64-green",
        "status": "RUNNING",
        "started_at": utc_now(),
        "green_marker": GREEN_MARKER,
        "stages": {},
    }
    try:
        # Green requires newly built artifacts on one exact revision, not cache reuse.
        if BUILD.exists():
            shutil.rmtree(BUILD)
        evidence["revision"] = revision()
        evidence["host"] = preflight()
        write_evidence(evidence_path, evidence)

        tests_rc, _, tests_tail, tests_timeout = run_stream(
            [sys.executable, "jetos.py", "test"], timeout=build_timeout
        )
        evidence["stages"]["repository_tests"] = {
            "returncode": tests_rc,
            "timed_out": tests_timeout,
            "tail": tests_tail,
        }
        if tests_timeout or tests_rc != 0:
            raise RuntimeError("repository-native test stage failed")

        build_rc, _, build_tail, build_timed_out = run_stream(
            [sys.executable, "tools/dev.py", "build"], timeout=build_timeout
        )
        evidence["stages"]["fresh_build"] = {
            "returncode": build_rc,
            "timed_out": build_timed_out,
            "kernel": str(KERNEL.relative_to(ROOT)),
            "initramfs": str(INITRAMFS.relative_to(ROOT)),
            "tail": build_tail,
        }
        if build_timed_out or build_rc != 0:
            raise RuntimeError("fresh JetLang/kernel/Fat build failed")

        command = qemu_command()
        boot_rc, marker_seen, boot_tail, boot_timed_out = run_stream(
            command, timeout=boot_timeout, marker=GREEN_MARKER
        )
        evidence["stages"]["qemu_guest"] = {
            "returncode_after_stop": boot_rc,
            "timed_out": boot_timed_out,
            "marker_seen": marker_seen,
            "command": command,
            "tail": boot_tail,
        }
        if not marker_seen:
            reason = "QEMU boot timed out" if boot_timed_out else "QEMU exited before Green marker"
            raise RuntimeError(reason)

        evidence["status"] = "PASS"
        evidence["finished_at"] = utc_now()
        write_evidence(evidence_path, evidence)
        print(f"{GREEN_MARKER}")
        print(f"Green Gate evidence: {evidence_path}")
        return 0
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["finished_at"] = utc_now()
        evidence["failure"] = str(exc)
        write_evidence(evidence_path, evidence)
        print(f"JETOS_GREEN_GATE=FAIL: {exc}", file=sys.stderr)
        print(f"Green Gate evidence: {evidence_path}", file=sys.stderr)
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
