#!/usr/bin/env python3
"""Contract tests for the executable Apple-Silicon/arm64 Green Gate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
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
    assert '"-cpu", "max"' in text
    assert '[sys.executable, "jetos.py", "test"]' in text
    assert '[sys.executable, "tools/dev.py", "build"]' in text
    assert 'GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"' in text
    assert 'shutil.rmtree(BUILD)' in text

    gate = load_gate()
    with mock.patch.object(gate.platform, "system", return_value="Linux"), \
         mock.patch.object(gate.platform, "machine", return_value="aarch64"), \
         mock.patch.object(gate.shutil, "which", return_value="/usr/bin/tool"), \
         mock.patch.object(gate.common, "compiler_command", return_value=(["/usr/bin/cc"], "cc")):
        host = gate.preflight()
        assert host["machine"] == "aarch64"

    with mock.patch.object(gate.platform, "system", return_value="Linux"), \
         mock.patch.object(gate.platform, "machine", return_value="x86_64"):
        try:
            gate.preflight()
        except RuntimeError as exc:
            assert "requires arm64 execution" in str(exc)
        else:
            raise AssertionError("M1 gate accepted x86_64 host")

    print("JETOS M1 Green Gate contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
