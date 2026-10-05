#!/usr/bin/env python3
"""Build a flashable Raspberry Pi JETOS image with live Git-backed userspace."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
PI_LINUX = BUILD / "pi-linux"
PI_FIRMWARE = BUILD / "pi-firmware"
ROOTFS = BUILD / "pi-rootfs"
INITRAMFS = BUILD / "jetos-pi-initramfs.cpio.gz"
STATE_TREE = BUILD / "pi-state"
BOOT_TREE = BUILD / "pi-boot"

PI_LINUX_REPOSITORY = "https://github.com/raspberrypi/linux.git"
PI_LINUX_COMMIT = "43c132e8863c3bff3647033b6a7d2bf87b15501c"
PI_FIRMWARE_REPOSITORY = "https://github.com/raspberrypi/firmware.git"
PI_FIRMWARE_COMMIT = "cdb0453d483cc220b53b96e24bc6d361fc511733"

MODEL_SPECS = {
    "pi4": {
        "defconfig": "bcm2711_defconfig",
        "dtb": "arch/arm64/boot/dts/broadcom/bcm2711-rpi-4-b.dtb",
        "kernel": "kernel8.img",
    },
    "pi5": {
        "defconfig": "bcm2712_defconfig",
        "dtb": "arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dtb",
        "kernel": "kernel_2712.img",
    },
}

PI_REQUIRED_KERNEL = {
    "CONFIG_EXT4_FS": "y",
    "CONFIG_MMC": "y",
    "CONFIG_MMC_BLOCK": "y",
    "CONFIG_MMC_SDHCI": "y",
    "CONFIG_MMC_SDHCI_PLTFM": "y",
    "CONFIG_MMC_SDHCI_BRCMSTB": "y",
    "CONFIG_BCMGENET": "y",
    "CONFIG_INET": "y",
    "CONFIG_IP_PNP": "y",
    "CONFIG_IP_PNP_DHCP": "y",
    "CONFIG_VT": "y",
    "CONFIG_VT_CONSOLE": "y",
    "CONFIG_FRAMEBUFFER_CONSOLE": "y",
    "CONFIG_DRM": "y",
    "CONFIG_DRM_VC4": "y",
    "CONFIG_USB": "y",
    "CONFIG_USB_XHCI_HCD": "y",
    "CONFIG_USB_XHCI_PLATFORM": "y",
    "CONFIG_HID": "y",
    "CONFIG_USB_HID": "y",
}


def load_tool(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "tools" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load_tool("build.py", "jetos_build")
image_tool = load_tool("image.py", "jetos_image")
dev = load_tool("dev.py", "jetos_dev")


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def require_arm64() -> None:
    machine = platform.machine().lower()
    if machine not in {"aarch64", "arm64"}:
        raise SystemExit(
            "Raspberry Pi image construction currently requires an ARM64 Linux "
            "environment. `python tools/pi_host.py` launches one with Docker."
        )
    if platform.system() != "Linux":
        raise SystemExit("Raspberry Pi image construction currently runs on Linux")


def ensure_checkout(
    url: str,
    commit: str,
    destination: Path,
    *,
    sparse: tuple[str, ...] = (),
) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "init", str(destination)])
    run(["git", "remote", "add", "origin", url], cwd=destination)
    if sparse:
        run(["git", "config", "core.sparseCheckout", "true"], cwd=destination)
        info = destination / ".git/info"
        info.mkdir(parents=True, exist_ok=True)
        (info / "sparse-checkout").write_text(
            "".join(f"{value}\n" for value in sparse),
            encoding="utf-8",
        )
    run(
        [
            "git",
            "fetch",
            "--depth",
            "1",
            "--filter=blob:none",
            "origin",
            commit,
        ],
        cwd=destination,
    )
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)


def patch_values(config: Path, values: dict[str, str]) -> None:
    lines = config.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key: str | None = None
        if line.startswith("CONFIG_") and "=" in line:
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
        if key in values:
            if key not in seen:
                output.append(f"{key}={values[key]}")
                seen.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    config.write_text("\n".join(output) + "\n", encoding="utf-8")


def check_values(config: Path, values: dict[str, str]) -> None:
    actual = build.read_kernel_config(config)
    failures = [
        f"{key}={actual.get(key, 'missing')} (need {value})"
        for key, value in values.items()
        if actual.get(key) != value
    ]
    if failures:
        raise SystemExit(
            "Raspberry Pi kernel profile failed:\n  " + "\n  ".join(failures)
        )


def build_pi_kernel(model: str, jobs: int) -> tuple[Path, Path]:
    spec = MODEL_SPECS[model]
    ensure_checkout(PI_LINUX_REPOSITORY, PI_LINUX_COMMIT, PI_LINUX)
    run(["make", "ARCH=arm64", spec["defconfig"]], cwd=PI_LINUX)
    config = PI_LINUX / ".config"
    build.patch_kernel_config(config, "arm64")
    patch_values(config, PI_REQUIRED_KERNEL)
    run(["make", "ARCH=arm64", "olddefconfig"], cwd=PI_LINUX)
    build.check_kernel_config(config, "arm64")
    check_values(config, PI_REQUIRED_KERNEL)
    run(
        ["make", "ARCH=arm64", f"-j{jobs}", "Image", "dtbs"],
        cwd=PI_LINUX,
    )
    kernel = PI_LINUX / "arch/arm64/boot/Image"
    dtb = PI_LINUX / spec["dtb"]
    if not kernel.exists() or not dtb.exists():
        raise SystemExit("Raspberry Pi kernel build did not produce Image + target DTB")
    return kernel, dtb


def prepare_language() -> tuple[Path, Path]:
    dev.ensure_checkout(
        dev.CPYTHON_REPOSITORY,
        dev.CPYTHON_COMMIT,
        dev.LANGUAGE_SOURCE,
        "jetos-language",
    )
    run([sys.executable, "tools/language.py", "patch", str(dev.LANGUAGE_SOURCE)])
    return dev.build_language()


def copy_binary_with_dependencies(binary: Path, rootfs: Path) -> None:
    build.copy_absolute(binary, rootfs)
    try:
        dependencies = build.parse_ldd(binary)
    except subprocess.CalledProcessError:
        dependencies = []
    for dependency in dependencies:
        build.copy_absolute(dependency, rootfs)


def install_git_runtime(rootfs: Path) -> None:
    git = shutil.which("git")
    if not git:
        raise SystemExit("git is required in the ARM64 image-build environment")
    copy_binary_with_dependencies(Path(git), rootfs)

    git_core = Path("/usr/lib/git-core")
    if git_core.exists():
        build.copy_absolute(git_core, rootfs)
        for path in git_core.rglob("*"):
            if path.is_file() and os.access(path, os.X_OK):
                try:
                    for dependency in build.parse_ldd(path):
                        build.copy_absolute(dependency, rootfs)
                except (OSError, subprocess.CalledProcessError):
                    pass

    for source in (
        Path("/usr/share/git-core"),
        Path("/etc/ssl/certs"),
        Path("/etc/nsswitch.conf"),
        Path("/etc/hosts"),
        Path("/etc/services"),
    ):
        if source.exists():
            build.copy_absolute(source, rootfs)

    for base in (Path("/lib"), Path("/usr/lib")):
        if not base.exists():
            continue
        for candidate in base.glob("*/libnss_*.so.2"):
            build.copy_absolute(candidate, rootfs)


def build_initramfs(profile: str) -> Path:
    runtime, stdlib = prepare_language()
    build.make_rootfs(ROOTFS, runtime, stdlib)
    (ROOTFS / "init").write_text(
        "#!/usr/bin/python3\n"
        "import sys\n"
        "sys.path.insert(0, '/jetos/src')\n"
        "from jetos.bootstrap import main\n"
        "main()\n",
        encoding="utf-8",
    )
    (ROOTFS / "init").chmod(0o755)
    install_git_runtime(ROOTFS)
    if profile == "lean":
        image_tool.compact_stdlib(ROOTFS, stdlib)
    build.build_initramfs(ROOTFS, INITRAMFS)
    return INITRAMFS


def prepare_firmware() -> Path:
    ensure_checkout(
        PI_FIRMWARE_REPOSITORY,
        PI_FIRMWARE_COMMIT,
        PI_FIRMWARE,
        sparse=("boot/",),
    )
    return PI_FIRMWARE / "boot"


def source_origin_url() -> str:
    result = run(["git", "remote", "get-url", "origin"], capture=True)
    return result.stdout.strip()


def prepare_state_tree() -> Path:
    if STATE_TREE.exists():
        shutil.rmtree(STATE_TREE)
    STATE_TREE.mkdir(parents=True)
    destination = STATE_TREE / "jetos"
    run(["git", "clone", "--local", "--no-hardlinks", str(ROOT), str(destination)])
    origin = source_origin_url()
    run(["git", "remote", "set-url", "origin", origin], cwd=destination)
    return STATE_TREE


def config_text(model: str) -> str:
    spec = MODEL_SPECS[model]
    return (
        "[all]\n"
        "arm_64bit=1\n"
        "enable_uart=1\n"
        "disable_overscan=1\n"
        "dtoverlay=vc4-kms-v3d\n"
        f"kernel={spec['kernel']}\n"
        "initramfs jetos-pi-initramfs.cpio.gz followkernel\n"
    )


def cmdline_text(network: str) -> str:
    fields = [
        "console=serial0,115200",
        "console=tty1",
        "rdinit=/init",
        "panic=-1",
        "jetos.state=/dev/mmcblk0p2",
        f"jetos.network={network}",
    ]
    if network == "on":
        fields.append("ip=dhcp")
    return " ".join(fields) + "\n"


def prepare_boot_tree(
    model: str,
    kernel: Path,
    dtb: Path,
    initramfs: Path,
    network: str,
) -> Path:
    firmware_boot = prepare_firmware()
    if BOOT_TREE.exists():
        shutil.rmtree(BOOT_TREE)
    shutil.copytree(firmware_boot, BOOT_TREE, symlinks=True)

    for candidate in BOOT_TREE.glob("kernel*.img"):
        candidate.unlink(missing_ok=True)
    for candidate in BOOT_TREE.glob("initramfs*"):
        if candidate.is_file():
            candidate.unlink()

    spec = MODEL_SPECS[model]
    shutil.copy2(kernel, BOOT_TREE / spec["kernel"])
    shutil.copy2(dtb, BOOT_TREE / dtb.name)
    shutil.copy2(initramfs, BOOT_TREE / INITRAMFS.name)
    (BOOT_TREE / "config.txt").write_text(config_text(model), encoding="utf-8")
    (BOOT_TREE / "cmdline.txt").write_text(cmdline_text(network), encoding="utf-8")
    return BOOT_TREE


def partition_entry(
    *,
    bootable: bool,
    partition_type: int,
    first_lba: int,
    sectors: int,
) -> bytes:
    status = 0x80 if bootable else 0x00
    chs = b"\xfe\xff\xff"
    return struct.pack(
        "<B3sB3sII",
        status,
        chs,
        partition_type,
        chs,
        first_lba,
        sectors,
    )


def mbr_bytes(
    *,
    boot_first_lba: int,
    boot_sectors: int,
    state_first_lba: int,
    state_sectors: int,
) -> bytes:
    sector = bytearray(512)
    sector[446:462] = partition_entry(
        bootable=True,
        partition_type=0x0C,
        first_lba=boot_first_lba,
        sectors=boot_sectors,
    )
    sector[462:478] = partition_entry(
        bootable=False,
        partition_type=0x83,
        first_lba=state_first_lba,
        sectors=state_sectors,
    )
    sector[510:512] = b"\x55\xaa"
    return bytes(sector)


def require_image_tools() -> None:
    missing = [
        name
        for name in ("mformat", "mcopy", "mke2fs")
        if shutil.which(name) is None
    ]
    if missing:
        raise SystemExit("missing image tools: " + ", ".join(missing))


def build_disk_image(
    output: Path,
    boot_tree: Path,
    state_tree: Path,
    *,
    size_mib: int,
    boot_mib: int = 256,
) -> None:
    require_image_tools()
    if size_mib <= boot_mib + 64:
        raise SystemExit("image is too small for boot + persistent state partitions")

    sector_size = 512
    first_lba = 2048
    boot_sectors = boot_mib * 1024 * 1024 // sector_size
    state_first_lba = first_lba + boot_sectors
    total_sectors = size_mib * 1024 * 1024 // sector_size
    state_sectors = total_sectors - state_first_lba

    boot_fs = BUILD / "jetos-pi-boot.fat"
    state_fs = BUILD / "jetos-pi-state.ext4"
    for path in (boot_fs, state_fs, output):
        path.unlink(missing_ok=True)

    with boot_fs.open("wb") as stream:
        stream.truncate(boot_sectors * sector_size)
    run(["mformat", "-F", "-i", str(boot_fs), "::"])
    for entry in sorted(boot_tree.iterdir()):
        run(["mcopy", "-s", "-i", str(boot_fs), str(entry), "::"])

    with state_fs.open("wb") as stream:
        stream.truncate(state_sectors * sector_size)
    run(
        [
            "mke2fs",
            "-F",
            "-q",
            "-t",
            "ext4",
            "-L",
            "JETOS_STATE",
            "-d",
            str(state_tree),
            str(state_fs),
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as disk:
        disk.truncate(size_mib * 1024 * 1024)
        disk.seek(0)
        disk.write(
            mbr_bytes(
                boot_first_lba=first_lba,
                boot_sectors=boot_sectors,
                state_first_lba=state_first_lba,
                state_sectors=state_sectors,
            )
        )
        disk.seek(first_lba * sector_size)
        with boot_fs.open("rb") as source:
            shutil.copyfileobj(source, disk, length=1024 * 1024)
        disk.seek(state_first_lba * sector_size)
        with state_fs.open("rb") as source:
            shutil.copyfileobj(source, disk, length=1024 * 1024)

    print(f"flashable JETOS Raspberry Pi image: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build flashable JETOS Raspberry Pi image")
    parser.add_argument("command", choices=("build",))
    parser.add_argument("--model", choices=tuple(MODEL_SPECS), default="pi4")
    parser.add_argument("--profile", choices=("lean", "full"), default="lean")
    parser.add_argument("--network", choices=("on", "off"), default="off")
    parser.add_argument("--size-mib", type=int, default=1024)
    parser.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    require_arm64()
    output = args.output or BUILD / f"jetos-{args.model}.img"
    kernel, dtb = build_pi_kernel(args.model, args.jobs)
    initramfs = build_initramfs(args.profile)
    state = prepare_state_tree()
    boot = prepare_boot_tree(
        args.model,
        kernel,
        dtb,
        initramfs,
        args.network,
    )
    build_disk_image(
        output,
        boot,
        state,
        size_mib=args.size_mib,
    )
    print(f"model: {args.model}")
    print(f"network policy: {args.network}")
    print("live JETOS Git checkout: partition 2 /state/jetos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
