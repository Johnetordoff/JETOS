#!/usr/bin/env python3
"""Build and qualify JetLang inside JetOS on an ODROID HC1-class ARMv7 host.

This is an execution path, not a readiness probe.  The canonical `qualify`
command requires a real ARMv7 ODROID-class Linux host, builds JetLang natively,
builds a 32-bit ARM JetOS kernel, creates a qualification initramfs, boots that
kernel under the host's QEMU system emulator, and waits for the stdlib/guest
qualification markers emitted by JetOS PID 1.

The qualification initramfs deliberately omits the complete Linux source tree.
The HC1 has constrained RAM; standard-library qualification needs the new
JetLang runtime, its stdlib/tests, JetOS userspace, and qualification tools, not
an in-RAM copy of the kernel source used to build the kernel.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import platform
import selectors
import shutil
import subprocess
import sys
import time
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
ODROID_ROOTFS = BUILD / "odroid-hc1-rootfs"
ODROID_INITRAMFS = BUILD / "odroid-hc1-qualification.cpio.gz"
ARMV7_ALIASES = frozenset({"armv7l", "armv7", "armhf"})
ODROID_MODEL_PATHS = (
    Path("/proc/device-tree/model"),
    Path("/sys/firmware/devicetree/base/model"),
)
ARMV7_KERNEL_CONFIG = {
    "CONFIG_ARM": "y",
    "CONFIG_AEABI": "y",
    "CONFIG_VFP": "y",
    "CONFIG_BINFMT_ELF": "y",
    "CONFIG_BINFMT_SCRIPT": "y",
    "CONFIG_BLK_DEV_INITRD": "y",
    "CONFIG_RD_GZIP": "y",
    "CONFIG_DEVTMPFS": "y",
    "CONFIG_TTY": "y",
    "CONFIG_PRINTK": "y",
    "CONFIG_PROC_FS": "y",
    "CONFIG_SYSFS": "y",
    "CONFIG_TMPFS": "y",
    "CONFIG_UNIX": "y",
    "CONFIG_NET": "y",
    "CONFIG_INET": "y",
    "CONFIG_SERIAL_AMBA_PL011": "y",
    "CONFIG_SERIAL_AMBA_PL011_CONSOLE": "y",
    "CONFIG_ARCH_VIRT": "y",
}


def load_tool(name: str) -> ModuleType:
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"jetos_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load JetOS tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load_tool("build")
dev = load_tool("dev")
package = load_tool("package")


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=True,
        text=True,
    )


def normalized_machine(machine: str | None = None) -> str:
    value = (machine or platform.machine()).lower()
    if value in ARMV7_ALIASES:
        return "armv7"
    return value


def board_model() -> str | None:
    for path in ODROID_MODEL_PATHS:
        try:
            value = path.read_bytes().replace(b"\0", b"").decode("utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if value:
            return value
    return None


def require_hc1_host(*, allow_generic_armv7: bool = False) -> str:
    machine = normalized_machine()
    if machine != "armv7":
        raise SystemExit(
            "ODROID HC1 full qualification must run on the ARMv7 host so "
            "JetLang is built natively for the same CPU ABI; "
            f"current host architecture is {platform.machine()!r}"
        )
    model = board_model()
    if allow_generic_armv7:
        return model or "generic ARMv7 host"
    if model is None or not any(token in model.lower() for token in ("odroid", "hardkernel")):
        raise SystemExit(
            "ARMv7 host found, but ODROID/Hardkernel board identity was not "
            "verified from the Linux device tree; use --allow-generic-armv7 "
            "only for non-HC1 development"
        )
    return model


def patch_kernel_config(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        key: str | None = None
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
        if key in ARMV7_KERNEL_CONFIG:
            if key not in seen:
                output.append(f"{key}={ARMV7_KERNEL_CONFIG[key]}")
                seen.add(key)
        else:
            output.append(line)
    for key, value in ARMV7_KERNEL_CONFIG.items():
        if key not in seen:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def check_kernel_config(path: Path) -> None:
    values = build.read_kernel_config(path)
    failures = [
        f"{key}={values.get(key, 'missing')} (need {need})"
        for key, need in ARMV7_KERNEL_CONFIG.items()
        if values.get(key) != need
    ]
    if failures:
        raise SystemExit(
            "JetOS ARMv7 first-boot kernel profile failed:\n  "
            + "\n  ".join(failures)
        )


def kernel_make_prefix(*, machine: str | None = None) -> list[str]:
    if normalized_machine(machine) == "armv7":
        return ["make", "ARCH=arm"]
    cross = os.environ.get("CROSS_COMPILE", "arm-linux-gnueabihf-")
    compiler = f"{cross}gcc"
    if not shutil.which(compiler):
        raise SystemExit(
            "ARMv7 cross-kernel build requires "
            f"{compiler}; install the hard-float ARM cross toolchain or run "
            "the full qualification natively on the HC1"
        )
    return ["make", "ARCH=arm", f"CROSS_COMPILE={cross}"]


def build_armv7_kernel(source: Path, *, jobs: int) -> Path:
    source = source.resolve()
    if not (source / "Makefile").is_file():
        raise SystemExit(f"not a Linux source tree: {source}")
    make = kernel_make_prefix()
    run([*make, "multi_v7_defconfig"], cwd=source)
    config = source / ".config"
    patch_kernel_config(config)
    run([*make, "olddefconfig"], cwd=source)
    check_kernel_config(config)
    run([*make, f"-j{jobs}", "zImage"], cwd=source)
    image = source / "arch/arm/boot/zImage"
    if not image.is_file():
        raise SystemExit(f"ARMv7 kernel build did not produce {image}")
    print(f"JetOS ARMv7 kernel: {image} ({image.stat().st_size} bytes)")
    return image


def build_qualification_initramfs(runtime: Path, stdlib: Path) -> Path:
    build.make_rootfs(ODROID_ROOTFS, runtime, stdlib)
    package.strip_temporary_bullshit(ODROID_ROOTFS)
    package.install_stdlib_qualification(ODROID_ROOTFS, "full")
    package.install_guest_qualification(ODROID_ROOTFS)
    build.build_initramfs(ODROID_ROOTFS, ODROID_INITRAMFS)
    print(
        "ODROID qualification image: runtime + stdlib/tests + JetOS userspace; "
        "Linux source intentionally omitted"
    )
    return ODROID_INITRAMFS


def qemu_command(kernel: Path, initramfs: Path, memory: str) -> list[str]:
    qemu = shutil.which("qemu-system-arm")
    if not qemu:
        raise SystemExit("qemu-system-arm is required on the ODROID host")
    accel = "kvm" if Path("/dev/kvm").exists() else "tcg"
    return [
        qemu,
        "-accel",
        accel,
        "-machine",
        "virt",
        "-cpu",
        "cortex-a15",
        "-m",
        memory,
        "-kernel",
        str(kernel),
        "-initrd",
        str(initramfs),
        "-append",
        "console=ttyAMA0 rdinit=/init panic=-1",
        "-nic",
        "none",
        "-nographic",
        "-no-reboot",
    ]


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def qualify_vm(
    kernel: Path,
    initramfs: Path,
    *,
    memory: str,
    timeout: int,
) -> None:
    command = qemu_command(kernel, initramfs, memory)
    print("+", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    stdlib_passed = False
    guest_passed = False
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise SystemExit(
                    "JetOS ARMv7 VM exited before qualification completed "
                    f"(status {process.returncode})"
                )
            events = selector.select(timeout=1.0)
            if not events:
                continue
            line = process.stdout.readline()
            if not line:
                continue
            print(line, end="", flush=True)
            if "JETOS_STDLIB_QUALIFICATION=FAIL" in line:
                raise SystemExit("JetLang standard-library tests failed inside JetOS")
            if "JETOS_GUEST_QUALIFICATION=FAIL" in line:
                raise SystemExit("JetOS guest runtime qualification failed")
            if "JETOS_STDLIB_QUALIFICATION=PASS" in line:
                stdlib_passed = True
            if "JETOS_GUEST_QUALIFICATION=PASS" in line:
                guest_passed = True
            if stdlib_passed and guest_passed:
                print("ODROID_HC1_JETLANG_STDLIB_ON_JETOS=PASS", flush=True)
                return
        raise SystemExit(
            "timed out before JetLang stdlib + JetOS guest qualification completed"
        )
    finally:
        selector.close()
        stop_process(process)


def build_all(*, allow_generic_armv7: bool = False) -> tuple[Path, Path, Path]:
    if platform.system() != "Linux":
        raise SystemExit("ODROID HC1 qualification requires Linux on the target host")
    model = require_hc1_host(allow_generic_armv7=allow_generic_armv7)
    revision = dev.prepare_revision_build()
    dev.tests()
    dev.prepare_sources()
    runtime, stdlib = dev.build_language()
    dev.qualify_stdlib(runtime)
    kernel = build_armv7_kernel(dev.LINUX_SOURCE, jobs=os.cpu_count() or 1)
    initramfs = build_qualification_initramfs(runtime, stdlib)
    print("\nJetOS ODROID HC1 qualification artifacts")
    print(f"  JetOS revision: {revision}")
    print(f"  board:          {model}")
    print(f"  host ABI:       {platform.machine()} / ARMv7 hard-float")
    print(f"  JetLang:        {runtime}")
    print(f"  kernel:         {kernel}")
    print(f"  initramfs:      {initramfs}")
    return runtime, kernel, initramfs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-host", help="verify that this is an ARMv7 ODROID-class host")
    check.add_argument("--allow-generic-armv7", action="store_true")

    kernel = sub.add_parser("kernel", help="build the ARMv7 JetOS kernel; cross-build is allowed")
    kernel.add_argument("--source", type=Path, default=dev.LINUX_SOURCE)
    kernel.add_argument("--jobs", type=int, default=os.cpu_count() or 1)

    qualify = sub.add_parser(
        "qualify",
        help="build JetLang + JetOS on the ARMv7 ODROID host and run stdlib tests inside JetOS",
    )
    qualify.add_argument("--allow-generic-armv7", action="store_true")
    qualify.add_argument("--memory", default="auto")
    qualify.add_argument("--timeout", type=int, default=4 * 60 * 60)

    args = parser.parse_args()
    if args.command == "check-host":
        model = require_hc1_host(allow_generic_armv7=args.allow_generic_armv7)
        print(f"ODROID ARMv7 host: {model}")
    elif args.command == "kernel":
        build_armv7_kernel(args.source, jobs=args.jobs)
    elif args.command == "qualify":
        _, image, initramfs = build_all(
            allow_generic_armv7=args.allow_generic_armv7
        )
        memory = args.memory
        if memory == "auto":
            memory = build.initramfs_vm_memory(initramfs)
            print(f"ODROID JetOS VM memory: {memory}")
        qualify_vm(
            image,
            initramfs,
            memory=memory,
            timeout=args.timeout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
