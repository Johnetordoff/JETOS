#!/usr/bin/env python3
"""Contract tests for the executable Apple-Silicon/arm64 Green Gate."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_gate():
    path = ROOT / "tools/m1_green_gate.py"
    spec = importlib.util.spec_from_file_location("jetos_test_m1_green_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_text() -> None:
    text = (ROOT / "tools/m1_green_gate.py").read_text(encoding="utf-8")
    assert 'KERNEL = BUILD / "linux/arch/arm64/boot/Image"' in text
    assert '"qemu-system-aarch64"' in text
    assert '"console=ttyAMA0 rdinit=/init panic=-1"' in text
    assert '"-machine", "virt"' in text
    assert '[sys.executable, "jetos.py", "test"]' in text
    assert '[sys.executable, "tools/dev.py", "build"]' in text
    assert 'GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"' in text
    assert 'shutil.rmtree(BUILD)' in text
    build_failed = text.index('raise RuntimeError("fresh arm64 JetLang/kernel/Fat build failed")')
    artifacts = text.index('evidence["artifacts"] = artifact_record()')
    assert build_failed < artifacts
    assert "write_evidence(evidence_path, evidence)" in text[artifacts:text.index("def load_built_evidence")]


def check_preflight(gate) -> None:
    with tempfile.TemporaryDirectory() as temp:
        # Do not depend on whether this checkout has source/linux and
        # source/cpython populated: point the source check at real files.
        marker = Path(temp) / "marker"
        marker.touch()
        with mock.patch.object(gate.common, "REQUIRED_SOURCES", {marker: "source"}), \
             mock.patch.object(gate.platform, "system", return_value="Linux"), \
             mock.patch.object(gate.platform, "machine", return_value="aarch64"), \
             mock.patch.object(gate.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(gate.common, "compiler_command", return_value=(["/usr/bin/cc"], "cc")), \
             mock.patch.object(gate.common, "kvm_usable", return_value=True):
            host = gate.preflight()
            assert host["machine"] == "aarch64"
            assert host["kvm"] is True

    for system, machine, message in (
        ("Linux", "x86_64", "requires arm64 execution"),
        ("Darwin", "arm64", "Linux/arm64 development environment"),
    ):
        with mock.patch.object(gate.platform, "system", return_value=system), \
             mock.patch.object(gate.platform, "machine", return_value=machine):
            try:
                gate.preflight()
            except RuntimeError as exc:
                assert message in str(exc), exc
            else:
                raise AssertionError(f"M1 build stage accepted {system}/{machine}")


def check_accelerator(gate) -> None:
    cases = (
        # system, machine, kvm, hvf -> accel, cpu
        ("Linux", "aarch64", True, False, "kvm", "host"),
        ("Linux", "aarch64", False, False, "tcg", "max"),
        ("Darwin", "arm64", False, True, "hvf", "host"),
        ("Darwin", "arm64", False, False, "tcg", "max"),
        # Never hardware-accelerate an arm64 guest on another host ISA.
        ("Darwin", "x86_64", False, True, "tcg", "max"),
        ("Linux", "x86_64", True, False, "tcg", "max"),
    )
    for system, machine, kvm, hvf, accel, cpu in cases:
        with mock.patch.object(gate.platform, "system", return_value=system), \
             mock.patch.object(gate.platform, "machine", return_value=machine), \
             mock.patch.object(gate.common, "kvm_usable", return_value=kvm), \
             mock.patch.object(gate, "hvf_available", return_value=hvf):
            assert gate.accelerator("/q") == (accel, cpu), (system, machine, kvm, hvf)

    help_text = "Accelerators supported in QEMU binary:\ntcg\nhvf\n"
    with mock.patch.object(gate.subprocess, "run", return_value=mock.Mock(stdout=help_text)):
        assert gate.hvf_available("/q") is True
    with mock.patch.object(gate.subprocess, "run", return_value=mock.Mock(stdout="tcg\n")):
        assert gate.hvf_available("/q") is False
    with mock.patch.object(gate.subprocess, "run", side_effect=OSError):
        assert gate.hvf_available("/q") is False


def check_build_boot_handoff(gate) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        build = root / ".build"
        kernel = build / "linux/arch/arm64/boot/Image"
        initramfs = build / "jetos-initramfs.cpio.gz"
        evidence_path = build / "m1-green-gate.json"
        kernel.parent.mkdir(parents=True)
        kernel.write_bytes(b"kernel")
        initramfs.write_bytes(b"initramfs")

        def fake_build_stage(evidence, path, timeout):
            evidence["revision"] = "rev-a"
            evidence["artifacts"] = gate.artifact_record()
            evidence["vm_memory"] = "2048M"

        boots: list[list[str]] = []

        def fake_run_stream(command, *, timeout, marker=None):
            boots.append(command)
            return 0, outcome["marker"], ["guest"], False

        outcome = {"marker": True}
        with mock.patch.object(gate, "ROOT", root), \
             mock.patch.object(gate, "BUILD", build), \
             mock.patch.object(gate, "KERNEL", kernel), \
             mock.patch.object(gate, "INITRAMFS", initramfs), \
             mock.patch.object(gate, "build_stage", fake_build_stage), \
             mock.patch.object(gate, "accelerator", return_value=("hvf", "host")), \
             mock.patch.object(gate.shutil, "which", return_value="/opt/qemu-system-aarch64"), \
             mock.patch.object(gate.common, "run_stream", fake_run_stream), \
             mock.patch.object(gate.common, "load_build_tool", side_effect=AssertionError("boot recomputed memory")), \
             mock.patch.object(gate.common, "revision", return_value="rev-a"):

            def run(stage: str) -> dict:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    rc = gate.run_gate(
                        evidence_path=evidence_path, build_timeout=1, boot_timeout=1, stage=stage
                    )
                record = json.loads(evidence_path.read_text(encoding="utf-8"))
                assert (rc == 0) == (record["status"] in {"BUILT", "PASS"}), record
                return record

            record = run("build")
            assert record["status"] == "BUILT"
            assert record["artifacts"]["initramfs"]["path"] == ".build/jetos-initramfs.cpio.gz"
            assert not boots, "build stage must not boot"

            # A boot that never reaches the marker keeps the build reusable.
            outcome["marker"] = False
            record = run("boot")
            assert record["status"] == "BOOT_FAIL"
            assert record["failure"] == "QEMU exited before Green marker"

            outcome["marker"] = True
            record = run("boot")
            assert record["status"] == "PASS"
            assert "failure" not in record
            assert record["boot_host"]["accel"] == "hvf"
            assert record["boot_host"]["cpu"] == "host"
            assert boots[-1][boots[-1].index("-m") + 1] == "2048M"

            # Boot refuses artifacts it cannot tie to the recorded build.
            record = run("build")
            initramfs.write_bytes(b"initramfs-changed")
            boots.clear()
            assert run("boot")["failure"] == (
                "M1 kernel/initramfs changed since the build stage recorded them"
            )
            assert not boots

            initramfs.write_bytes(b"initramfs")
            run("build")
            with mock.patch.object(gate.common, "revision", return_value="rev-b"):
                assert "not the current revision rev-b" in run("boot")["failure"]
            assert not boots

            evidence_path.unlink()
            assert "run --stage build first" in run("boot")["failure"]


def main() -> int:
    check_text()
    gate = load_gate()
    check_preflight(gate)
    check_accelerator(gate)
    check_build_boot_handoff(gate)
    print("JETOS M1 Green Gate contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
