#!/usr/bin/env python3
"""JETOS Python-owned rootfs, kernel, initramfs, and VM orchestration."""
from __future__ import annotations

import argparse
import gzip
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD = ROOT / ".build"

COMMON_FIRST_BOOT_KERNEL = {
    "CONFIG_64BIT": "y",
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
    # Facilities the supported JetLang standard library requires of the OS
    # (pty/termios, POSIX shm/semaphores, sockets/loopback, threads,
    # selectors). Pinned so kernel reduction cannot silently drop them.
    "CONFIG_UNIX98_PTYS": "y",
    "CONFIG_SHMEM": "y",
    "CONFIG_INET": "y",
    "CONFIG_FUTEX": "y",
    "CONFIG_EPOLL": "y",
}

ARCH_FIRST_BOOT_KERNEL = {
    "x86_64": {
        "CONFIG_X86_64": "y",
        "CONFIG_SERIAL_8250": "y",
        "CONFIG_SERIAL_8250_CONSOLE": "y",
    },
    "arm64": {
        "CONFIG_ARM64": "y",
        "CONFIG_SERIAL_AMBA_PL011": "y",
        "CONFIG_SERIAL_AMBA_PL011_CONSOLE": "y",
    },
}

VM_RECOMMENDED_KERNEL = {
    "CONFIG_PCI": {"y"},
    "CONFIG_VIRTIO": {"y"},
    "CONFIG_VIRTIO_PCI": {"y", "m"},
    "CONFIG_VIRTIO_BLK": {"y", "m"},
    "CONFIG_VIRTIO_NET": {"y", "m"},
    "CONFIG_EXT4_FS": {"y", "m"},
}


def normalize_arch(value: str | None = None) -> str:
    machine = (value or platform.machine()).lower()
    if machine in {"x86_64", "amd64", "x86"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise SystemExit(f"unsupported JETOS architecture: {machine}")


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=check,
        text=True,
    )


def parse_ldd(binary: Path) -> list[Path]:
    result = subprocess.run(
        ["ldd", str(binary)],
        check=True,
        text=True,
        capture_output=True,
    )
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
        shutil.copytree(
            source,
            target,
            symlinks=True,
            dirs_exist_ok=True,
        )
    else:
        shutil.copy2(source, target, follow_symlinks=True)
    return target


def collect_python_runtime(
    python: Path,
    stdlib: Path,
    rootfs: Path,
) -> None:
    python = python.resolve()
    stdlib = stdlib.resolve()
    python_target = copy_absolute(python, rootfs)
    alias = rootfs / "usr/bin/python3"
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.unlink(missing_ok=True)
    guest_python = "/" + python_target.relative_to(rootfs).as_posix()
    alias.symlink_to(guest_python)

    stdlib_target = rootfs / stdlib.relative_to("/")
    shutil.copytree(
        stdlib,
        stdlib_target,
        symlinks=True,
        dirs_exist_ok=True,
    )

    elf_files = [python]
    elf_files.extend(
        path
        for path in stdlib.rglob("*.so")
        if path.is_file()
    )
    dependencies: list[Path] = []
    for elf in elf_files:
        try:
            for dependency in parse_ldd(elf):
                if dependency not in dependencies:
                    dependencies.append(dependency)
        except subprocess.CalledProcessError:
            continue
    for dependency in dependencies:
        copy_absolute(dependency, rootfs)
    collect_dlopen_runtime(dependencies, rootfs)


# Libraries the C runtime loads with dlopen() at run time, so ldd never
# reports them. glibc dlopens libgcc_s for pthread_cancel/pthread_exit and
# unwinding; without it threaded JetLang aborts with
# "libgcc_s.so.1 must be installed for pthread_exit to work".
DLOPEN_RUNTIME_LIBRARIES = ("libgcc_s.so.1",)


def collect_dlopen_runtime(dependencies: list[Path], rootfs: Path) -> list[Path]:
    """Copy dlopen-only runtime libraries from the same directory as libc.

    Searching only the directories that already supplied the runtime's
    ldd-resolved libraries keeps the guest on one ABI/architecture.
    """
    directories: list[Path] = []
    for dependency in dependencies:
        if dependency.parent not in directories:
            directories.append(dependency.parent)
    copied: list[Path] = []
    for name in DLOPEN_RUNTIME_LIBRARIES:
        found = next((d / name for d in directories if (d / name).exists()), None)
        if found is None:
            print(f"JETOS rootfs WARNING: dlopen runtime library {name} not found beside the runtime's libraries", flush=True)
            continue
        copy_absolute(found, rootfs)
        copied.append(found)
    return copied


# Minimal account/name-service database. CPython's pwd/grp/getpass/
# os.path.expanduser and socket name resolution of "localhost" read these
# ordinary Linux files; JETOS provides them instead of patching JetLang.
ETC_FILES = {
    "etc/passwd": "root:x:0:0:root:/root:/usr/bin/python3\nnobody:x:65534:65534:nobody:/nonexistent:/bin/false\n",
    "etc/group": "root:x:0:\ntty:x:5:\nnogroup:x:65534:\n",
    "etc/hosts": "127.0.0.1\tlocalhost\n::1\tlocalhost ip6-localhost ip6-loopback\n",
    "etc/nsswitch.conf": "passwd: files\ngroup: files\nshadow: files\nhosts: files dns\nnetworks: files\nprotocols: files\nservices: files\n",
}


def write_etc(rootfs: Path) -> None:
    for relative, content in ETC_FILES.items():
        path = rootfs / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o644)
    (rootfs / "root").mkdir(mode=0o700, exist_ok=True)


def copy_jetos(rootfs: Path) -> None:
    target = rootfs / "jetos/src/jetos"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        ROOT / "src/jetos",
        target,
        dirs_exist_ok=True,
    )
    shutil.copy2(
        ROOT / "src/jetos/startup.py",
        rootfs / "jetos/startup.py",
    )

    init = rootfs / "init"
    init.write_text(
        "#!/usr/bin/python3\n"
        "import sys\n"
        "sys.path.insert(0, '/jetos/src')\n"
        "from jetos.init import main\n"
        "main()\n",
        encoding="utf-8",
    )
    init.chmod(0o755)


def make_rootfs(
    destination: Path,
    python: Path,
    stdlib: Path,
) -> None:
    if platform.system() != "Linux":
        raise SystemExit(
            "JETOS rootfs assembly currently runs on Linux; "
            "use `python jetos.py dev` on macOS/Windows"
        )
    if destination.exists():
        shutil.rmtree(destination)
    for directory in (
        "dev",
        "proc",
        "sys",
        "tmp",
        "usr/bin",
        "jetos",
    ):
        (destination / directory).mkdir(
            parents=True,
            exist_ok=True,
        )
    (destination / "tmp").chmod(0o1777)
    write_etc(destination)
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
        cpio_field(ino),
        cpio_field(mode),
        cpio_field(0),
        cpio_field(0),
        cpio_field(1),
        cpio_field(0),
        cpio_field(len(data)),
        cpio_field(0),
        cpio_field(0),
        cpio_field(rdevmajor),
        cpio_field(rdevminor),
        cpio_field(len(name_bytes)),
        cpio_field(0),
    ])
    result = header + name_bytes
    result += b"\0" * pad4(len(result))
    result += data
    result += b"\0" * pad4(len(data))
    return result


# Character devices PID 1 needs before it can mount devtmpfs. JetLang is
# PID 1 and seeds hash randomization at startup: early in boot getrandom()
# can report EAGAIN, and CPython then requires /dev/urandom or aborts.
EARLY_DEVICE_NODES = (
    ("dev/console", 0o600, 5, 1),
    ("dev/null", 0o666, 1, 3),
    ("dev/random", 0o666, 1, 8),
    ("dev/urandom", 0o666, 1, 9),
)


def build_initramfs(
    rootfs: Path,
    output: Path,
) -> None:
    pieces: list[bytes] = []
    ino = 1
    for name, permissions, major, minor in EARLY_DEVICE_NODES:
        pieces.append(
            cpio_entry(
                name,
                stat.S_IFCHR | permissions,
                rdevmajor=major,
                rdevminor=minor,
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
        pieces.append(
            cpio_entry(
                rel,
                mode,
                data,
                ino=ino,
            )
        )
        ino += 1

    pieces.append(
        cpio_entry(
            "TRAILER!!!",
            stat.S_IFREG,
            b"",
            ino=ino,
        )
    )
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with output.open("wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            compresslevel=9,
            mtime=0,
        ) as stream:
            for piece in pieces:
                stream.write(piece)
    print(
        f"wrote {output} "
        f"({output.stat().st_size} bytes)"
    )


def kernel_requirements(
    target_arch: str,
) -> dict[str, str]:
    target_arch = normalize_arch(target_arch)
    return {
        **COMMON_FIRST_BOOT_KERNEL,
        **ARCH_FIRST_BOOT_KERNEL[target_arch],
    }


def read_kernel_config(
    path: Path,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if (
            raw.startswith("CONFIG_")
            and "=" in raw
        ):
            key, value = raw.split("=", 1)
            values[key] = value
        elif (
            raw.startswith("# CONFIG_")
            and raw.endswith(" is not set")
        ):
            values[raw[2:-11]] = "n"
    return values


def check_kernel_config(
    path: Path,
    target_arch: str,
) -> None:
    values = read_kernel_config(path)
    wanted = kernel_requirements(target_arch)
    failures = [
        (
            f"{key}="
            f"{values.get(key, 'missing')} "
            f"(need {need})"
        )
        for key, need in wanted.items()
        if values.get(key) != need
    ]
    if failures:
        raise SystemExit(
            "JETOS first-boot kernel "
            "profile failed:\n  "
            + "\n  ".join(failures)
        )
    print(
        "JETOS first-boot kernel profile "
        f"({normalize_arch(target_arch)}): PASS"
    )
    for key, accepted in VM_RECOMMENDED_KERNEL.items():
        value = values.get(
            key,
            "missing",
        )
        status = (
            "ready"
            if value in accepted
            else "not enabled yet"
        )
        print(
            f"  {key}={value}: {status}"
        )


def patch_kernel_config(
    path: Path,
    target_arch: str,
) -> None:
    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()
    wanted = kernel_requirements(target_arch)
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        key: str | None = None
        if (
            line.startswith("CONFIG_")
            and "=" in line
        ):
            key = line.split("=", 1)[0]
        elif (
            line.startswith("# CONFIG_")
            and line.endswith(" is not set")
        ):
            key = line[2:-11]

        if key in wanted:
            if key not in seen:
                output.append(
                    f"{key}={wanted[key]}"
                )
                seen.add(key)
        else:
            output.append(line)

    for key, value in wanted.items():
        if key not in seen:
            output.append(f"{key}={value}")

    path.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8",
    )


def kernel_image(
    source: Path,
    target_arch: str,
) -> Path:
    if normalize_arch(target_arch) == "x86_64":
        return source / "arch/x86/boot/bzImage"
    return source / "arch/arm64/boot/Image"


def kernel_build(
    source: Path,
    *,
    target_arch: str,
    jobs: int,
    config: str,
) -> Path:
    source = source.resolve()
    target_arch = normalize_arch(target_arch)

    if not (source / "Makefile").exists():
        raise SystemExit(
            f"not a Linux source tree: {source}"
        )

    run(
        [
            "make",
            f"ARCH={target_arch}",
            config,
        ],
        cwd=source,
    )
    config_path = source / ".config"
    patch_kernel_config(
        config_path,
        target_arch,
    )
    run(
        [
            "make",
            f"ARCH={target_arch}",
            "olddefconfig",
        ],
        cwd=source,
    )
    check_kernel_config(
        config_path,
        target_arch,
    )
    target = (
        "bzImage"
        if target_arch == "x86_64"
        else "Image"
    )
    run(
        [
            "make",
            f"ARCH={target_arch}",
            f"-j{jobs}",
            target,
        ],
        cwd=source,
    )

    image = kernel_image(
        source,
        target_arch,
    )
    print(
        f"JETOS kernel image: "
        f"{image} "
        f"({image.stat().st_size} bytes)"
    )
    return image


MIB = 1024 * 1024
VM_MEMORY_HEADROOM = 512 * MIB


def initramfs_vm_memory(initramfs: Path) -> str:
    """Size guest RAM so the kernel can unpack the initramfs into rootfs.

    The compressed archive and its unpacked contents are both resident while
    the kernel unpacks it, and the unpacked rootfs stays in RAM afterwards.
    A Fat image carries full source trees, so a fixed small default makes the
    kernel fail with "Initramfs unpacking failed: write error" and panic.
    The initramfs rootfs is tmpfs, which defaults to half of RAM, so the
    unpacked size counts twice. The gzip trailer records the uncompressed size
    modulo 2**32.
    """
    compressed = initramfs.stat().st_size
    with initramfs.open("rb") as stream:
        stream.seek(-4, os.SEEK_END)
        unpacked = int.from_bytes(stream.read(4), "little")
    while unpacked < compressed:
        unpacked += 1 << 32
    needed = compressed + 2 * unpacked + VM_MEMORY_HEADROOM
    return f"{-(-needed // (256 * MIB)) * 256}M"


def qemu_boot(
    kernel: Path,
    initramfs: Path,
    memory: str,
    target_arch: str,
) -> None:
    target_arch = normalize_arch(target_arch)
    if memory == "auto":
        memory = initramfs_vm_memory(initramfs)
        print(f"JETOS VM memory: {memory} (sized from {initramfs})", flush=True)
    if target_arch == "x86_64":
        executable = "qemu-system-x86_64"
        console = "ttyS0"
        machine_args: list[str] = []
    else:
        executable = "qemu-system-aarch64"
        console = "ttyAMA0"
        machine_args = [
            "-machine",
            "virt",
            "-cpu",
            "max",
        ]

    qemu = shutil.which(executable)
    if not qemu:
        raise SystemExit(
            f"{executable} is not installed"
        )

    accel = (
        "kvm"
        if Path("/dev/kvm").exists()
        else "tcg"
    )

    os.execvp(
        qemu,
        [
            qemu,
            "-accel",
            accel,
            *machine_args,
            "-m",
            memory,
            "-kernel",
            str(kernel),
            "-initrd",
            str(initramfs),
            "-append",
            (
                f"console={console} "
                "rdinit=/init "
                "panic=-1"
            ),
            "-nic",
            "none",
            "-nographic",
            "-no-reboot",
        ],
    )


def chroot_dry_run(
    rootfs: Path,
) -> None:
    if os.geteuid() != 0:
        raise SystemExit(
            "dry-run currently requires "
            "root for os.chroot()"
        )
    run([
        sys.executable,
        str(Path(__file__).resolve()),
        "_enter-rootfs",
        str(rootfs),
    ])


def enter_rootfs(
    rootfs: Path,
) -> None:
    os.chroot(rootfs)
    os.chdir("/")
    os.environ["PYTHONPATH"] = "/jetos/src"
    os.environ["PYTHONSTARTUP"] = (
        "/jetos/startup.py"
    )
    os.execv(
        "/usr/bin/python3",
        [
            "/usr/bin/python3",
            "-S",
            "-i",
        ],
    )


def defaults() -> tuple[Path, Path]:
    executable = Path(
        sys.executable
    ).resolve()
    version = (
        f"python"
        f"{sys.version_info.major}."
        f"{sys.version_info.minor}"
    )
    candidates = [
        Path("/usr/lib") / version,
        Path(sys.prefix) / "lib" / version,
    ]
    stdlib = next(
        (
            path
            for path in candidates
            if path.is_dir()
        ),
        None,
    )
    if stdlib is None:
        raise SystemExit(
            "could not locate "
            "Python standard library"
        )
    return executable, stdlib


def main() -> int:
    python, stdlib = defaults()
    parser = argparse.ArgumentParser(
        description=(
            "JETOS Python-owned build tool"
        )
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    root = sub.add_parser("rootfs")
    root.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BUILD / "rootfs",
    )
    root.add_argument(
        "--python",
        type=Path,
        default=python,
    )
    root.add_argument(
        "--stdlib",
        type=Path,
        default=stdlib,
    )

    initrd = sub.add_parser("initramfs")
    initrd.add_argument(
        "--rootfs",
        type=Path,
        default=DEFAULT_BUILD / "rootfs",
    )
    initrd.add_argument(
        "--output",
        type=Path,
        default=(
            DEFAULT_BUILD
            / "jetos-initramfs.cpio.gz"
        ),
    )
    initrd.add_argument(
        "--python",
        type=Path,
        default=python,
    )
    initrd.add_argument(
        "--stdlib",
        type=Path,
        default=stdlib,
    )

    dry = sub.add_parser("dry-run")
    dry.add_argument(
        "--rootfs",
        type=Path,
        default=DEFAULT_BUILD / "rootfs",
    )
    dry.add_argument(
        "--python",
        type=Path,
        default=python,
    )
    dry.add_argument(
        "--stdlib",
        type=Path,
        default=stdlib,
    )

    check = sub.add_parser("kernel-check")
    check.add_argument(
        "config",
        type=Path,
    )
    check.add_argument(
        "--arch",
        default=normalize_arch(),
    )

    kernel = sub.add_parser("kernel")
    kernel.add_argument(
        "source",
        type=Path,
    )
    kernel.add_argument(
        "--arch",
        default=normalize_arch(),
    )
    kernel.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
    )
    kernel.add_argument(
        "--config",
        default="defconfig",
    )

    enter = sub.add_parser(
        "_enter-rootfs",
        help=argparse.SUPPRESS,
    )
    enter.add_argument(
        "rootfs",
        type=Path,
    )

    vm = sub.add_parser("vm")
    vm.add_argument(
        "--arch",
        default=normalize_arch(),
    )
    vm.add_argument(
        "--kernel",
        type=Path,
        required=True,
    )
    vm.add_argument(
        "--initramfs",
        type=Path,
        default=(
            DEFAULT_BUILD
            / "jetos-initramfs.cpio.gz"
        ),
    )
    vm.add_argument(
        "--memory",
        default="auto",
        help="guest RAM, e.g. 4G; 'auto' sizes it from the initramfs",
    )

    args = parser.parse_args()

    if args.command == "rootfs":
        make_rootfs(
            args.output,
            args.python,
            args.stdlib,
        )
        print(f"rootfs: {args.output}")
    elif args.command == "initramfs":
        make_rootfs(
            args.rootfs,
            args.python,
            args.stdlib,
        )
        build_initramfs(
            args.rootfs,
            args.output,
        )
    elif args.command == "dry-run":
        make_rootfs(
            args.rootfs,
            args.python,
            args.stdlib,
        )
        chroot_dry_run(args.rootfs)
    elif args.command == "kernel-check":
        check_kernel_config(
            args.config,
            args.arch,
        )
    elif args.command == "kernel":
        kernel_build(
            args.source,
            target_arch=args.arch,
            jobs=args.jobs,
            config=args.config,
        )
    elif args.command == "_enter-rootfs":
        enter_rootfs(args.rootfs)
    elif args.command == "vm":
        qemu_boot(
            args.kernel,
            args.initramfs,
            args.memory,
            args.arch,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
