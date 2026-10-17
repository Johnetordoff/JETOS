#!/usr/bin/env python3
"""Contract tests for the canonical issue-96 Green Gate."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_gate():
    path = ROOT / "tools/green_gate.py"
    spec = importlib.util.spec_from_file_location("jetos_test_green_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    gate_text = (ROOT / "tools/green_gate.py").read_text(encoding="utf-8")
    init = (ROOT / "src/jetos/init.py").read_text(encoding="utf-8")
    entrypoint = (ROOT / "jetos.py").read_text(encoding="utf-8")

    assert 'GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"' in gate_text
    assert '"qemu-system-x86_64"' in gate_text
    assert '"qemu-system-arm"' not in gate_text
    assert '"qemu-system-aarch64"' not in gate_text
    assert 'shutil.rmtree(BUILD)' in gate_text
    assert '[sys.executable, "jetos.py", "test"]' in gate_text
    assert '[sys.executable, "tools/dev.py", "build"]' in gate_text
    assert 'evidence["status"] = "PASS"' in gate_text
    assert 'marker_seen' in gate_text

    gate = load_gate()
    with mock.patch.dict(os.environ, {"CC": "ccache gcc -m64"}, clear=False), \
         mock.patch.object(gate.shutil, "which", side_effect=lambda name: "/usr/bin/ccache" if name == "ccache" else None):
        command, configured = gate.compiler_command()
        assert command == ["/usr/bin/ccache", "gcc", "-m64"]
        assert configured == "ccache gcc -m64"
    with mock.patch.dict(os.environ, {"CC": "definitely-missing-jetos-cc"}, clear=False), \
         mock.patch.object(gate.shutil, "which", return_value=None):
        try:
            gate.compiler_command()
        except RuntimeError as exc:
            assert "configured C compiler was not found" in str(exc)
        else:
            raise AssertionError("missing configured compiler was accepted")
    assert '"cc"' not in gate_text[gate_text.index("REQUIRED_TOOLS = ("):gate_text.index(")\n\n\ndef utc_now")]

    # Seeing /dev/kvm is insufficient: containers and restricted users commonly
    # have the node without permission to open it. Green Gate must use TCG there.
    with tempfile.TemporaryDirectory() as temp:
        fake_kvm = Path(temp) / "kvm"
        fake_kvm.touch()
        with mock.patch.object(gate.os, "open", side_effect=PermissionError("denied")):
            assert not gate.kvm_usable(fake_kvm)
        read_fd, write_fd = os.pipe()
        os.close(write_fd)
        try:
            with mock.patch.object(gate.os, "open", return_value=read_fd):
                assert gate.kvm_usable(fake_kvm)
        finally:
            try:
                os.close(read_fd)
            except OSError:
                pass

    marker_index = init.index("print(GREEN_GATE_MARKER, flush=True)")
    stdlib_index = init.index("stdlib_qualified = run_armed_stdlib_qualification()")
    guest_index = init.index("guest_qualified = run_armed_guest_qualification()")
    assert stdlib_index < marker_index
    assert guest_index < marker_index
    assert "if stdlib_qualified and guest_qualified:" in init

    assert 'sub.add_parser("green"' in entrypoint
    assert 'choices=("auto", "docker", "native")' in entrypoint
    assert 'GREEN_DOCKER_PLATFORM = "linux/amd64"' in entrypoint
    assert '"--pull"' not in entrypoint[entrypoint.index("def green_docker"):entrypoint.index("def green(")]
    assert 'glob("test_*.py")' in entrypoint

    print("JETOS Green Gate contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
