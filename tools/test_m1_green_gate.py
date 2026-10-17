#!/usr/bin/env python3
"""Contract tests for the executable Apple-Silicon/arm64 Green Gate."""
from __future__ import annotations

import importlib.util
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


def main() -> int:
    text = (ROOT / "tools/m1_green_gate.py").read_text(encoding="utf-8")
    assert 'KERNEL = BUILD / "linux/arch/arm64/boot/Image"' in text
    assert '"qemu-system-aarch64"' in text
    assert '"console=ttyAMA0 rdinit=/init panic=-1"' in text
    assert '"-machine", "virt"' in text
    assert 'accel = "kvm" if kvm else "tcg"' in text
    assert 'cpu = "host" if kvm else "max"' in text
    assert '[sys.executable, "jetos.py", "test"]' in text
    assert '[sys.executable, "tools/dev.py", "build"]' in text
    assert 'GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"' in text
    assert 'shutil.rmtree(BUILD)' in text
    build_failed = text.index('raise RuntimeError("fresh arm64 JetLang/kernel/Fat build failed")')
    guest_boot = text.index("command = qemu_command()")
    assert "write_evidence(evidence_path, evidence)" in text[build_failed:guest_boot]

    gate = load_gate()
    with mock.patch.object(gate.platform, "system", return_value="Linux"), \
         mock.patch.object(gate.platform, "machine", return_value="aarch64"), \
         mock.patch.object(gate.shutil, "which", return_value="/usr/bin/tool"), \
         mock.patch.object(gate.common, "compiler_command", return_value=(["/usr/bin/cc"], "cc")), \
         mock.patch.object(gate.common, "kvm_usable", return_value=True):
        host = gate.preflight()
        assert host["machine"] == "aarch64"
        assert host["kvm"] is True

    with mock.patch.object(gate.platform, "system", return_value="Linux"), \
         mock.patch.object(gate.platform, "machine", return_value="x86_64"):
        try:
            gate.preflight()
        except RuntimeError as exc:
            assert "requires arm64 execution" in str(exc)
        else:
            raise AssertionError("M1 gate accepted x86_64 host")

    fake_build = mock.Mock()
    fake_build.initramfs_vm_memory.return_value = "1024M"
    # Path instances are immutable (__slots__), so point the
    # gate at real artifact files instead of patching Path.is_file.
    with tempfile.TemporaryDirectory() as temp:
        kernel = Path(temp) / "Image"
        initramfs = Path(temp) / "jetos-initramfs.cpio.gz"
        kernel.touch()
        initramfs.touch()
        for kvm, accel, cpu in ((True, "kvm", "host"), (False, "tcg", "max")):
            with mock.patch.object(gate, "KERNEL", kernel), \
                 mock.patch.object(gate, "INITRAMFS", initramfs), \
                 mock.patch.object(gate.shutil, "which", return_value="/usr/bin/qemu-system-aarch64"), \
                 mock.patch.object(gate.common, "load_build_tool", return_value=fake_build), \
                 mock.patch.object(gate.common, "kvm_usable", return_value=kvm):
                command = gate.qemu_command()
                assert command[command.index("-accel") + 1] == accel
                assert command[command.index("-cpu") + 1] == cpu

    print("JETOS M1 Green Gate contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
