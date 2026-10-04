#!/usr/bin/env python3
"""JETOS Python-owned build and boot orchestration.

No JETOS-owned shell scripts or Makefiles are required for the first boot path.
Imported native tools (Linux Kbuild, a C compiler, QEMU) are invoked explicitly
when their native job is required.
"""
from __future__ import annotations

import argparse
import gzip
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / ".build"

FIRST_BOOT_KERNEL = {
    "CONFIG_64BIT": "y",
    "CONFIG_X86_64": "y",
    "CONFIG_BINFMT_ELF": "y",
    "CONFIG_BINFMT_SCRIPT": "y",
    "CONFIG_BLK_DEV_INITRD": "y",
    "CONFIG_RD_GZIP": "y",
    "CONFIG_DEVTMPFS": "y",
    "CONFIG_TTY": "y",
    "CONFIG_SERIAL_8250": "y",
    "CONFIG_SERIAL_8250_CONSOLE": "y",
    "CONFIG_PRINTK": "y",
    "CONFIG_PROC_FS": "y",
    "CONFIG_SYSFS": "y",
    "CONFIG_TMPFS": "y",
    "CONFIG_UNIX": "y",
}

VM_RECOMMENDED_KERNEL = {
    "CONFIG_PCI": {"y"},
    "CONFIG_VIRTIO_PCI": {"y", "m"},
    "CONFIG_VIRTIO_BLK": {"y", "m"},
    "CONFIG_VIRTIO_NET": {"y", "m"},
    "CONFIG_EXT4_FS": {"y", "m"},
}


def run(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=cwd, check=check, text=True)


def parse_ldd(binary: Path) -> list[Path]:
    """Return absolute shared-library paths required by an imported ELF binary."""
    result = subprocess.run(["ldd", str(binary)], check=True, text=True, capture_output=True)
    found: list[Path] = []
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line or "statically linked" in line:
            continue
        candidate: str | None = None
        if "=>" in line:
            rhs = line.split("=>", 1)[1].strip()
            if rhs.startswith("/"):
                candidate = rhs.split(" ", 1)[0]
        elif line.startswith("/"):
            candidate = line.split(" ", 1)[0]
        if candidate:
            path = Path(candidate)
            if path.exists() and path not in found:
                found.append(path)
    return found


def copy_absolute(source: Path, rootfs: Path) -> Path:
    target = rootfs / source.relative_to("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        link = os.readlink(source)
        target.unlink(missing_ok=True)
        target.symlink_to(link)
        semantic_target = Path(os.path.normpath(str(source.parent / link)))
        real_source = source.resolve()
        real_target = rootfs / semantic_target.relative_to("/")
        real_target.parent.mkdir(parents=True, exist_ok=True)
        if not real_target.exists():
            shutil.copy2(real_source, real_target)
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target, follow_symlinks=True)
    return target


def collect_python_runtime(python: Path, stdlib: Path, rootfs: Path) -> None:
    python = python.resolve()
    python_target = copy_absolute(python, rootfs)
    alias = rootfs / "usr/bin/python3"
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.unlink(missing_ok=True)
    alias.symlink_to(python_target.name)

    stdlib_target = rootfs / stdlib.relative_to("/")
    shutil.copytree(stdlib, stdlib_target, symlinks=True, dirs_exist_ok=True)

    # CPython itself must start before it can do any JETOS work. Copy its native
    # dynamic-loader/libc dependencies. Native extension libraries are copied
    # from the stdlib tree and their dependencies are added too.
    elf_files = [python]
    elf_files.extend(p for p in stdlib.rglob("*.so") if p.is_file())
    dependencies: list[Path] = []
    for elf in elf_files:
        try:
            for dep in parse_ldd(elf):
                if dep not in dependencies:
                    dependencies.append(dep)
        except subprocess.CalledProcessError:
            continue
    for dep in dependencies:
        copy_absolute(dep, rootfs)


def copy_jetos(rootfs: Path) -> None:
    target = rootfs / "jetos/src/jetos"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "src/jetos", target, dirs_exist_ok=True)
    shutil.copy2(ROOT / "src/jetos/startup.py", rootfs / "jetos/startup.py")

    init = rootfs / "init"
    init.write_text(
        "#!/usr/bin/python3\n"
        "from jetos.init import main\n"
        "main()\n",
        encoding="utf-8",
    )
    init.chmod(0o755)


def make_rootfs(destination: Path, python: Path, stdlib: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    for directory in ("dev", "proc", "sys", "tmp", "usr/bin", "jetos"):
        (destination / directory).mkdir(parents=True, exist_ok=True)
    collect_python_runtime(python, stdlib, destination)
    copy_jetos(destination)


def pad4(size: int) -> int:
    return (-size) & 3


def cpio_field(value: int) -> bytes:
    return f"{value:08x}".encode("ascii")


def cpio_entry(
    name: str,
    mode: int,
    data: bytes = b"",
    *,
    rdevmajor: int = 0,
    rdevminor: int = 0,
    ino: int = 1,
) -> bytes:
    name_bytes = name.encode("utf-8") + b"\0"
    header = b"070701" + b"".join([
        cpio_field(ino), cpio_field(mode), cpio_field(0), cpio_field(0),
        cpio_field(1), cpio_field(0), cpio_field(len(data)), cpio_field(0),
        cpio_field(0), cpio_field(rdevmajor), cpio_field(rdevminor),
        cpio_field(len(name_bytes)), cpio_field(0),
    ])
    result = header + name_bytes
    result += b"\0" * pad4(len(result))
    result += data
    result += b"\0" * pad4(len(data))
    return result


def build_initramfs(rootfs: Path, output: Path) -> None:
    pieces: list[bytes] = []
    ino = 1
    pieces.append(
        cpio_entry(
            "dev/console",
            stat.S_IFCHR | 0o600,
            rdevmajor=5,
            rdevminor=1,
            ino=ino,
        )
    )
    ino += 1

    for path in sorted(rootfs.rglob("*")):
        rel = path.relative_to(rootfs).as_posix()
        st = path.lstat()
        if path.is_symlink():
            data = os.readlink(path).encode("utf-8")
            mode = stat.S_IFLNK | 0o777
        elif path.is_dir():
            data = b""
            mode = stat.S_IFDIR | (st.st_mode & 0o7777)
        elif path.is_file():
            data = path.read_bytes()
            mode = stat.S_IFREG | (st.st_mode & 0o7777)
        else:
            continue
        pieces.append(cpio_entry(rel, mode, data, ino=ino))
        ino += 1

    pieces.append(cpio_entry("TRAILER!!!", stat.S_IFREG, b"", ino=ino))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            compresslevel=9,
            mtime=0,
        ) as stream:
            for piece in pieces:
                stream.write(piece)
    print(f"wrote {output} ({output.stat().st_size} bytes)")


def read_kernel_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
        elif raw.startswith("# CONFIG_") and raw.endswith(" is not set"):
            values[raw[2:-11]] = "n"
    return values


def check_kernel_config(path: Path) -> None:
    values = read_kernel_config(path)
    failures = [
        f"{key}={values.get(key, 'missing')} (need {need})"
        for key, need in FIRST_BOOT_KERNEL.items()
        if values.get(key) != need
    ]
    if failures:
        raise SystemExit(
            "JETOS first-boot kernel profile failed:\n  "
            + "\n  ".join(failures)
        )
    print("JETOS first-boot kernel profile: PASS")
    for key, accepted in VM_RECOMMENDED_KERNEL.items():
        value = values.get(key, "missing")
        status = "ready" if value in accepted else "not enabled yet"
        print(f"  {key}={value}: {status}")


def patch_kernel_config(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    wanted = FIRST_BOOT_KERNEL
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        key: str | None = None
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]

        if key in wanted:
            if key not in seen:
                output.append(f"{key}={wanted[key]}")
                seen.add(key)
        else:
            output.append(line)

    for key, value in wanted.items():
        if key not in seen:
            output.append(f"{key}={value}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def kernel_build(source: Path, *, arch: str, jobs: int, config: str) -> None:
    source = source.resolve()
    if not (source / "Makefile").exists():
        raise SystemExit(f"not a Linux source tree: {source}")
    if arch != "x86_64":
        raise SystemExit("first JETOS kernel profile currently targets x86_64")

    run(["make", f"ARCH={arch}", config], cwd=source)
    config_path = source / ".config"
    patch_kernel_config(config_path)
    run(["make", f"ARCH={arch}", "olddefconfig"], cwd=source)
    check_kernel_config(config_path)
    run(["make", f"ARCH={arch}", f"-j{jobs}", "bzImage"], cwd=source)

    image = source / "arch/x86/boot/bzImage"
    print(f"JETOS kernel image: {image} ({image.stat().st_size} bytes)")


def qemu_boot(kernel: Path, initramfs: Path, memory: str) -> None:
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise SystemExit("qemu-system-x86_64 is not installed")
    os.execvp(qemu, [
        qemu,
        "-m", memory,
        "-kernel", str(kernel),
        "-initrd", str(initramfs),
        "-append", "console=ttyS0 rdinit=/init panic=-1",
        "-nographic",
        "-no-reboot",
    ])


def chroot_dry_run(rootfs: Path) -> None:
    """Run the assembled CPython rootfs without a VM."""
    if os.geteuid() != 0:
        raise SystemExit("dry-run currently requires root for os.chroot()")
    run([
        sys.executable,
        str(Path(__file__).resolve()),
        "_enter-rootfs",
        str(rootfs),
    ])


def enter_rootfs(rootfs: Path) -> None:
    os.chroot(rootfs)
    os.chdir("/")
    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = "/jetos/startup.py"
    os.execv("/usr/bin/python3", ["/usr/bin/python3", "-S", "-i"])


def defaults() -> tuple[Path, Path]:
    executable = Path(sys.executable).resolve()
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path("/usr/lib") / version,
        Path(sys.prefix) / "lib" / version,
    ]
    stdlib = next((path for path in candidates if path.is_dir()), None)
    if stdlib is None:
        raise SystemExit("could not locate Python standard library")
    return executable, stdlib


def main() -> int:
    python, stdlib = defaults()
    parser = argparse.ArgumentParser(description="JETOS Python-owned build tool")
    sub = parser.add_subparsers(dest="command", required=True)

    root = sub.add_parser(
        "rootfs",
        help="assemble the JETOS CPython root filesystem",
    )
    root.add_argument("--output", type=Path, default=DEFAULT_BUILD / "rootfs")
    root.add_argument("--python", type=Path, default=python)
    root.add_argument("--stdlib", type=Path, default=stdlib)

    initrd = sub.add_parser(
        "initramfs",
        help="assemble rootfs and encode a bootable initramfs",
    )
    initrd.add_argument("--rootfs", type=Path, default=DEFAULT_BUILD / "rootfs")
    initrd.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BUILD / "jetos-initramfs.cpio.gz",
    )
    initrd.add_argument("--python", type=Path, default=python)
    initrd.add_argument("--stdlib", type=Path, default=stdlib)

    dry = sub.add_parser(
        "dry-run",
        help="open CPython from the assembled rootfs without a hypervisor",
    )
    dry.add_argument("--rootfs", type=Path, default=DEFAULT_BUILD / "rootfs")
    dry.add_argument("--python", type=Path, default=python)
    dry.add_argument("--stdlib", type=Path, default=stdlib)

    check = sub.add_parser(
        "kernel-check",
        help="validate an existing Linux .config for JETOS first boot",
    )
    check.add_argument("config", type=Path)

    kernel = sub.add_parser(
        "kernel",
        help="configure/build an imported Linux source tree",
    )
    kernel.add_argument("source", type=Path)
    kernel.add_argument("--arch", default="x86_64")
    kernel.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    kernel.add_argument("--config", default="defconfig")

    enter = sub.add_parser("_enter-rootfs", help=argparse.SUPPRESS)
    enter.add_argument("rootfs", type=Path)

    vm = sub.add_parser("vm", help="boot JETOS under QEMU")
    vm.add_argument("--kernel", type=Path, required=True)
    vm.add_argument(
        "--initramfs",
        type=Path,
        default=DEFAULT_BUILD / "jetos-initramfs.cpio.gz",
    )
    vm.add_argument("--memory", default="512M")

    args = parser.parse_args()

    if args.command == "rootfs":
        make_rootfs(args.output, args.python, args.stdlib)
        print(f"rootfs: {args.output}")
    elif args.command == "initramfs":
        make_rootfs(args.rootfs, args.python, args.stdlib)
        build_initramfs(args.rootfs, args.output)
    elif args.command == "dry-run":
        make_rootfs(args.rootfs, args.python, args.stdlib)
        chroot_dry_run(args.rootfs)
    elif args.command == "kernel-check":
        check_kernel_config(args.config)
    elif args.command == "kernel":
        kernel_build(
            args.source,
            arch=args.arch,
            jobs=args.jobs,
            config=args.config,
        )
    elif args.command == "_enter-rootfs":
        enter_rootfs(args.rootfs)
    elif args.command == "vm":
        qemu_boot(args.kernel, args.initramfs, args.memory)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
