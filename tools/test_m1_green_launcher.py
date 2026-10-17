#!/usr/bin/env python3
"""Contract test for launching arm64 Green Gate from Apple Silicon."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_launcher():
    path = ROOT / "tools/m1_green.py"
    spec = importlib.util.spec_from_file_location("jetos_test_m1_green", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def launch(launcher, argv: list[str], *, hvf_qemu: str | None) -> list[list[str]]:
    commands: list[list[str]] = []
    with mock.patch.object(launcher.platform, "system", return_value="Darwin"), \
         mock.patch.object(launcher.platform, "machine", return_value="arm64"), \
         mock.patch.object(launcher, "host_hvf_qemu", return_value=hvf_qemu), \
         mock.patch.object(launcher.shutil, "which", return_value="/usr/local/bin/docker"), \
         mock.patch.object(launcher, "run", side_effect=commands.append), \
         mock.patch.dict(launcher.os.environ, {"JETOS_BOOTSTRAP_IMAGE": "example/arm64-tools"}), \
         mock.patch.object(sys, "argv", ["m1_green.py", *argv]), \
         contextlib.redirect_stdout(io.StringIO()):
        assert launcher.main() == 0
    return commands


def main() -> int:
    text = (ROOT / "tools/m1_green.py").read_text(encoding="utf-8")
    assert 'PLATFORM = "linux/arm64"' in text
    assert '"--platform", PLATFORM' in text
    assert '"python3", GATE' in text
    assert 'JETOS_BOOTSTRAP_IMAGE' in text
    assert '"--pull"' not in text

    launcher = load_launcher()

    # Default on an M1 with host QEMU/HVF: build in the container, boot natively.
    build, run, boot = launch(launcher, [], hvf_qemu="/opt/homebrew/bin/qemu-system-aarch64")
    assert build[:2] == ["/usr/local/bin/docker", "build"]
    assert run[:2] == ["/usr/local/bin/docker", "run"]
    assert run[run.index("--stage") + 1] == "build"
    assert boot[:2] == [sys.executable, "tools/m1_green_gate.py"]
    assert boot[boot.index("--stage") + 1] == "boot"
    assert boot[boot.index("--evidence") + 1] == run[run.index("--evidence") + 1]

    # Without host HVF, auto keeps the whole gate inside the container.
    commands = launch(launcher, [], hvf_qemu=None)
    assert len(commands) == 2
    assert commands[1][commands[1].index("--stage") + 1] == "all"

    # Reboot already-verified artifacts without rebuilding.
    (boot,) = launch(launcher, ["--boot", "host", "--skip-build"], hvf_qemu="/q")
    assert boot[boot.index("--stage") + 1] == "boot"

    for argv, hvf in ((["--boot", "host"], None), (["--boot", "container", "--skip-build"], "/q")):
        try:
            launch(launcher, argv, hvf_qemu=hvf)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"M1 launcher accepted {argv} with hvf={hvf}")

    with mock.patch.object(launcher.platform, "system", return_value="Linux"), \
         mock.patch.object(sys, "argv", ["m1_green.py"]):
        try:
            launcher.main()
        except SystemExit as exc:
            assert "Apple-Silicon macOS" in str(exc)
        else:
            raise AssertionError("M1 launcher accepted a Linux host")

    # The static canonical-path contract is not a test_*.py script, so run it
    # here; otherwise it rots unnoticed as the paths it pins evolve.
    contract = importlib.util.spec_from_file_location("jetos_m1_contract", ROOT / "tools/m1_contract.py")
    assert contract and contract.loader
    module = importlib.util.module_from_spec(contract)
    contract.loader.exec_module(module)
    with contextlib.redirect_stdout(io.StringIO()):
        assert module.main() == 0

    print("JETOS M1 Green launcher contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
