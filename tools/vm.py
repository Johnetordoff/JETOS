#!/usr/bin/env python3
"""Launch a JETOS VM in serial, local-window, or VNC display mode."""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import platform
import shutil


def normalize_arch(value: str | None = None) -> str:
    machine = (value or platform.machine()).lower()
    if machine in {"x86_64", "amd64", "x86"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(f"unsupported architecture: {machine}")


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS QEMU launcher")
    parser.add_argument("--arch", default=normalize_arch())
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--initramfs", type=Path, required=True)
    parser.add_argument("--memory", default="512M")
    parser.add_argument("--display", choices=("serial", "window", "vnc"), default="serial")
    parser.add_argument("--encryption", choices=("on", "off"), default="on")
    parser.add_argument("--vnc-bind", default="127.0.0.1")
    args = parser.parse_args()

    arch = normalize_arch(args.arch)
    accel = "kvm" if Path("/dev/kvm").exists() else "tcg"
    if arch == "x86_64":
        executable = "qemu-system-x86_64"
        serial_console = "ttyS0"
        machine: list[str] = ["-cpu", "host"] if accel == "kvm" else []
        gpu = ["-device", "virtio-vga"]
    else:
        executable = "qemu-system-aarch64"
        serial_console = "ttyAMA0"
        machine = ["-machine", "virt", "-cpu", "host" if accel == "kvm" else "max"]
        gpu = ["-device", "virtio-gpu-device"]

    qemu = shutil.which(executable)
    if not qemu:
        raise SystemExit(f"{executable} is not installed")

    kernel_cmdline = (
        f"console={serial_console} console=tty0 rdinit=/init panic=-1 "
        f"jetos.encryption={args.encryption}"
    )
    command = [
        qemu,
        "-accel",
        accel,
        *machine,
        "-m",
        args.memory,
        "-kernel",
        str(args.kernel),
        "-initrd",
        str(args.initramfs),
        "-append",
        kernel_cmdline,
        "-nic",
        "none",
        "-no-reboot",
    ]

    if args.display == "serial":
        command.append("-nographic")
    elif args.display == "window":
        command.extend([*gpu, "-serial", "stdio"])
        print(
            "JETOS VM window mode presents a virtual display device. "
            "The Tk desktop still requires the guest display backend to be completed.",
            flush=True,
        )
    else:
        command.extend([*gpu, "-serial", "stdio", "-display", f"vnc={args.vnc_bind}:0"])
        print(
            f"JETOS QEMU display exported by VNC on {args.vnc_bind}:5900. "
            "This proves guest display hardware exposure; the Tk guest backend is still separate.",
            flush=True,
        )

    print("+", " ".join(command), flush=True)
    os.execvp(qemu, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
