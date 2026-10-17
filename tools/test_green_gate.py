#!/usr/bin/env python3
"""Contract tests for the canonical issue-96 Green Gate."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    gate = (ROOT / "tools/green_gate.py").read_text(encoding="utf-8")
    init = (ROOT / "src/jetos/init.py").read_text(encoding="utf-8")
    entrypoint = (ROOT / "jetos.py").read_text(encoding="utf-8")

    assert 'GREEN_MARKER = "JETOS_GREEN_GATE_PREPROMPT=PASS"' in gate
    assert '"qemu-system-x86_64"' in gate
    assert '"qemu-system-arm"' not in gate
    assert '"qemu-system-aarch64"' not in gate
    assert 'shutil.rmtree(BUILD)' in gate
    assert '[sys.executable, "jetos.py", "test"]' in gate
    assert '[sys.executable, "tools/dev.py", "build"]' in gate
    assert 'evidence["status"] = "PASS"' in gate
    assert 'marker_seen' in gate
    build_failed = gate.index('raise RuntimeError("fresh JetLang/kernel/Fat build failed")')
    guest_boot = gate.index("command = qemu_command()")
    assert "write_evidence(evidence_path, evidence)" in gate[build_failed:guest_boot]

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
