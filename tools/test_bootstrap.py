#!/usr/bin/env python3
"""Fast tests for JETOS boot/build policy without building Linux."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_build",
    ROOT / "tools/build.py",
)
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

PACKAGE_SPEC = importlib.util.spec_from_file_location(
    "jetos_package",
    ROOT / "tools/package.py",
)
assert PACKAGE_SPEC and PACKAGE_SPEC.loader
package = importlib.util.module_from_spec(PACKAGE_SPEC)
PACKAGE_SPEC.loader.exec_module(package)


def check(
    value: bool,
    message: str,
) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0

    check(
        build.normalize_arch("AMD64")
        == "x86_64",
        "AMD64 normalization",
    )
    check(
        build.normalize_arch("arm64")
        == "arm64",
        "ARM64 normalization",
    )
    checks += 2

    x86 = build.kernel_requirements(
        "x86_64"
    )
    arm = build.kernel_requirements(
        "arm64"
    )
    check(
        x86["CONFIG_X86_64"] == "y",
        "x86 kernel identity",
    )
    check(
        x86["CONFIG_SERIAL_8250_CONSOLE"]
        == "y",
        "x86 serial console",
    )
    check(
        arm["CONFIG_ARM64"] == "y",
        "arm64 kernel identity",
    )
    check(
        arm[
            "CONFIG_SERIAL_AMBA_PL011_CONSOLE"
        ]
        == "y",
        "arm64 serial console",
    )
    checks += 4

    entry = build.cpio_entry(
        "hello",
        0o100644,
        b"world",
    )
    check(
        entry.startswith(b"070701"),
        "newc CPIO magic",
    )
    check(
        b"hello\0" in entry,
        "newc CPIO name",
    )
    check(
        b"world" in entry,
        "newc CPIO data",
    )
    checks += 3

    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "early.cpio.gz"
        (Path(temp) / "rootfs").mkdir()
        build.build_initramfs(Path(temp) / "rootfs", output)
        archive = build.gzip.decompress(output.read_bytes())
        for name in ("dev/console", "dev/null", "dev/random", "dev/urandom"):
            check(
                name.encode("utf-8") + b"\0" in archive,
                f"early device node {name}",
            )
        checks += 4

    with tempfile.TemporaryDirectory() as temp:
        rootfs = Path(temp)
        build.copy_jetos(rootfs)
        init = (
            rootfs
            / "init"
        ).read_text(
            encoding="utf-8"
        )
        check(
            init.startswith(
                "#!/usr/bin/python3\n"
            ),
            "Python init shebang",
        )
        check(
            (
                "sys.path.insert("
                "0, '/jetos/src')"
            )
            in init,
            "init self-locates JETOS",
        )
        check(
            (
                "from jetos.init "
                "import main"
            )
            in init,
            "init imports JETOS PID 1",
        )
        checks += 3

    with tempfile.TemporaryDirectory() as temp:
        rootfs = Path(temp)
        tool = package.install_guest_qualification(rootfs)
        marker = rootfs / "jetos/guest-qualify"
        check(tool.is_file(), "Fat guest qualification tool installed")
        check(
            marker.read_text(encoding="utf-8") == "run\n",
            "Fat guest qualification marker armed",
        )
        qualifier = tool.read_text(encoding="utf-8")
        check(
            "configure_loopback" in qualifier,
            "guest qualifier configures loopback",
        )
        check(
            "ThreadingHTTPServer" in qualifier and "urlopen" in qualifier,
            "guest qualifier runs server/client web smoke",
        )
        checks += 4

    print(
        "JETOS bootstrap tooling: "
        f"{checks} checks passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
