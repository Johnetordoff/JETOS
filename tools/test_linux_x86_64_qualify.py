#!/usr/bin/env python3
"""Fast contract tests for the generic x86_64 Linux guest qualifier."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_linux_x86_64_qualify",
    ROOT / "tools/linux_x86_64_qualify.py",
)
assert SPEC and SPEC.loader
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


def main() -> int:
    checks = 0
    original_which = qualify.shutil.which
    original_exists = qualify.Path.exists
    original_memory = qualify.build.initramfs_vm_memory
    try:
        qualify.shutil.which = lambda name: f"/usr/bin/{name}"
        qualify.Path.exists = (
            lambda self: False
            if str(self) == "/dev/kvm"
            else original_exists(self)
        )
        qualify.build.initramfs_vm_memory = lambda path: "1536M"
        command = qualify.qemu_command(Path("kernel"), Path("initrd"), "auto")
        assert command[0].endswith("qemu-system-x86_64")
        assert command[command.index("-accel") + 1] == "tcg"
        assert command[command.index("-m") + 1] == "1536M"
        assert command[command.index("-append") + 1] == "console=ttyS0 rdinit=/init panic=-1"
        assert command[command.index("-nic") + 1] == "none"
        checks += 5

        qualify.Path.exists = (
            lambda self: True
            if str(self) == "/dev/kvm"
            else original_exists(self)
        )
        command = qualify.qemu_command(Path("kernel"), Path("initrd"), "2048M")
        assert command[command.index("-accel") + 1] == "kvm"
        assert command[command.index("-m") + 1] == "2048M"
        checks += 2
    finally:
        qualify.shutil.which = original_which
        qualify.Path.exists = original_exists
        qualify.build.initramfs_vm_memory = original_memory

    source = (ROOT / "tools/linux_x86_64_qualify.py").read_text(encoding="utf-8")
    for marker in (
        "JETOS_STDLIB_QUALIFICATION=PASS",
        "JETOS_STDLIB_QUALIFICATION=FAIL",
        "JETOS_GUEST_QUALIFICATION=PASS",
        "JETOS_GUEST_QUALIFICATION=FAIL",
        "JETOS_X86_64_JETLANG_STDLIB_ON_JETOS=PASS",
    ):
        assert marker in source
        checks += 1
    assert "dev.build_all()" in source
    assert "stderr=subprocess.STDOUT" in source
    assert "stream.flush()" in source
    checks += 3

    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "console.log"
        path.write_text("last completed regression: test_example\n", encoding="utf-8")
        assert "test_example" in path.read_text(encoding="utf-8")
        checks += 1

    print(f"JETOS generic x86_64 Linux qualification contract: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
