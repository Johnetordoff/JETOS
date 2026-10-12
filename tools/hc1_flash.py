#!/usr/bin/env python3
"""Prepare and flash an incremental ODROID-HC1 JETOS SSH bootstrap image.

This is a bring-up bridge, not the final JETOS-owned boot path. It starts from a
known-bootable HC1 Linux image, injects the current JETOS Python userspace,
configures wired DHCP and key-only OpenSSH, and never touches the HC1 SATA disk.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".build" / "jetos-hc1-ssh.img"
COPY_CHUNK = 4 * 1024 * 1024


class HC1Error(RuntimeError):
    """Raised for a bring-up precondition or safety failure."""


def run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, check=True, text=True, capture_output=capture)


def require_linux_root() -> None:
    if sys.platform != "linux":
        raise HC1Error("HC1 image preparation/flashing currently requires Linux")
    if os.geteuid() != 0:
        raise HC1Error("HC1 image preparation/flashing requires root privileges")


def require_commands(*names: str) -> None:
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise HC1Error("missing required host command(s): " + ", ".join(missing))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(COPY_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_reader(path: Path) -> BinaryIO:
    if path.suffix.lower() == ".xz":
        return lzma.open(path, "rb")
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def expand_image(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    temporary.unlink(missing_ok=True)
    try:
        with image_reader(source) as src, temporary.open("wb") as dst:
            while chunk := src.read(COPY_CHUNK):
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def partition_path(device: Path, number: int) -> Path:
    if number < 1:
        raise HC1Error("partition number must be >= 1")
    text = str(device)
    separator = "p" if text[-1:].isdigit() else ""
    return Path(f"{text}{separator}{number}")


def read_authorized_keys(path: Path) -> str:
    keys: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "PRIVATE KEY" in line:
            raise HC1Error("authorized-keys input appears to contain a private key")
        fields = line.split()
        if len(fields) < 2 or not (
            fields[0].startswith("ssh-")
            or fields[0].startswith("ecdsa-")
            or fields[0].startswith("sk-")
        ):
            raise HC1Error(f"unsupported authorized-key line: {line[:40]!r}")
        keys.append(line)
    if not keys:
        raise HC1Error("authorized-keys file contains no public keys")
    return "\n".join(keys) + "\n"


def find_existing(root: Path, candidates: tuple[str, ...], label: str) -> Path:
    for candidate in candidates:
        if (root / candidate.lstrip("/")).exists():
            return Path("/") / candidate.lstrip("/")
    raise HC1Error(f"base image is missing required {label}")


def write_text(root: Path, relative: str, text: str, mode: int = 0o644) -> None:
    path = root / relative.lstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def replace_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def enable_local_unit(root: Path, unit: str) -> None:
    wants = root / "etc/systemd/system/multi-user.target.wants"
    wants.mkdir(parents=True, exist_ok=True)
    link = wants / unit
    link.unlink(missing_ok=True)
    link.symlink_to(f"/etc/systemd/system/{unit}")


def harden_sshd(root: Path) -> None:
    config = root / "etc/ssh/sshd_config"
    if not config.is_file():
        raise HC1Error("base image is missing /etc/ssh/sshd_config")
    original = config.read_text(encoding="utf-8")
    policy = """# JETOS HC1 bootstrap policy; first values win in sshd_config.
AuthenticationMethods publickey
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
"""
    config.write_text(policy + "\n" + original, encoding="utf-8")


def configure_rootfs(root: Path, authorized_keys: str, base_sha256: str, hostname: str) -> None:
    python = find_existing(root, ("/usr/bin/python3", "/bin/python3"), "Python 3")
    sshd = find_existing(root, ("/usr/sbin/sshd", "/usr/bin/sshd"), "OpenSSH sshd")
    ssh_keygen = find_existing(root, ("/usr/bin/ssh-keygen", "/bin/ssh-keygen"), "ssh-keygen")
    networkd = find_existing(
        root,
        ("/usr/lib/systemd/systemd-networkd", "/lib/systemd/systemd-networkd"),
        "systemd-networkd",
    )

    replace_tree(ROOT / "src/jetos", root / "opt/jetos/src/jetos")
    console = f"""#!{python}
from __future__ import annotations
import code
import sys
sys.path.insert(0, '/opt/jetos/src')
import jetos
code.interact(banner='JETOS HC1 bootstrap console', local={{'jetos': jetos}})
"""
    write_text(root, "/usr/local/bin/jetos-console", console, 0o755)

    ssh_dir = root / "root/.ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    ssh_dir.chmod(0o700)
    keys = ssh_dir / "authorized_keys"
    keys.write_text(authorized_keys, encoding="utf-8")
    keys.chmod(0o600)
    harden_sshd(root)

    write_text(
        root,
        "/etc/systemd/network/20-jetos-wired.network",
        """[Match]
Name=eth* en*

[Network]
DHCP=yes
IPv6AcceptRA=yes
""",
    )
    write_text(
        root,
        "/etc/systemd/system/jetos-networkd.service",
        f"""[Unit]
Description=JETOS HC1 wired network bootstrap
DefaultDependencies=no
After=systemd-udevd.service
Before=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart={networkd}
Restart=on-failure

[Install]
WantedBy=multi-user.target
""",
    )
    enable_local_unit(root, "jetos-networkd.service")

    write_text(
        root,
        "/etc/systemd/system/jetos-sshd.service",
        f"""[Unit]
Description=JETOS HC1 SSH bootstrap
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStartPre={ssh_keygen} -A
ExecStart={sshd} -D -e
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
""",
    )
    enable_local_unit(root, "jetos-sshd.service")

    write_text(root, "/etc/hostname", hostname.strip() + "\n")
    write_text(
        root,
        "/etc/jetos/target.json",
        json.dumps(
            {
                "base_image_sha256": base_sha256,
                "board": "odroid-hc1",
                "cpu_arch": "armv7",
                "mode": "incremental-linux-bootstrap",
                "remote_admin": "openssh-key-only",
                "sata_policy": "untouched",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    write_text(
        root,
        "/etc/motd",
        "JETOS HC1 incremental bootstrap\nRun `jetos-console` for the Python control console.\n",
    )


def loop_attach(image: Path) -> Path:
    result = run(["losetup", "--find", "--show", "--partscan", str(image)], capture=True)
    device = Path(result.stdout.strip())
    if not str(device).startswith("/dev/loop"):
        raise HC1Error(f"unexpected loop device: {device}")
    return device


def prepare(base_image: Path, output: Path, keys_path: Path, root_partition: int, hostname: str) -> None:
    require_linux_root()
    require_commands("losetup", "mount", "umount")
    if not base_image.is_file():
        raise HC1Error(f"base image not found: {base_image}")
    if output.resolve() == base_image.resolve():
        raise HC1Error("output image must not overwrite the supplied base image")

    authorized_keys = read_authorized_keys(keys_path)
    base_sha256 = sha256_file(base_image)
    expand_image(base_image, output)

    loop: Path | None = None
    mounted = False
    with tempfile.TemporaryDirectory(prefix="jetos-hc1-") as directory:
        mountpoint = Path(directory)
        try:
            loop = loop_attach(output)
            partition = partition_path(loop, root_partition)
            deadline = time.monotonic() + 10
            while not partition.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            if not partition.exists():
                raise HC1Error(f"root partition did not appear: {partition}")
            run(["mount", "-o", "rw", str(partition), str(mountpoint)])
            mounted = True
            configure_rootfs(mountpoint, authorized_keys, base_sha256, hostname)
            os.sync()
        finally:
            try:
                if mounted:
                    run(["umount", str(mountpoint)])
            finally:
                if loop is not None:
                    run(["losetup", "-d", str(loop)])

    manifest = {
        "base_image": str(base_image),
        "base_image_sha256": base_sha256,
        "output_image": str(output),
        "output_image_sha256": sha256_file(output),
        "root_partition": root_partition,
        "ssh": "root public-key only",
        "target": "odroid-hc1",
    }
    manifest_path = output.with_suffix(output.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"prepared {output}")
    print(f"manifest {manifest_path}")


def mounted_sources() -> set[Path]:
    sources: set[Path] = set()
    path = Path("/proc/self/mountinfo")
    if not path.exists():
        return sources
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        try:
            separator = fields.index("-")
        except ValueError:
            continue
        if len(fields) > separator + 2 and fields[separator + 2].startswith("/dev/"):
            sources.add(Path(fields[separator + 2]).resolve())
    return sources


def device_related(source: Path, device: Path) -> bool:
    source_text, device_text = str(source), str(device)
    if source_text == device_text:
        return True
    if device_text[-1:].isdigit():
        return source_text.startswith(device_text + "p")
    suffix = source_text[len(device_text) :] if source_text.startswith(device_text) else ""
    return bool(suffix and suffix.isdigit())


def block_device_size(device: Path) -> int:
    size_path = Path("/sys/class/block") / device.resolve().name / "size"
    if not size_path.is_file():
        raise HC1Error(f"cannot determine capacity for {device}")
    return int(size_path.read_text(encoding="ascii").strip()) * 512


def validate_flash_device(device: Path, image: Path, confirmation: str) -> Path:
    resolved = device.resolve()
    try:
        mode = resolved.stat().st_mode
    except FileNotFoundError as error:
        raise HC1Error(f"flash device does not exist: {device}") from error
    if not stat.S_ISBLK(mode):
        raise HC1Error(f"refusing non-block-device target: {resolved}")
    if confirmation != str(resolved):
        raise HC1Error(f"confirmation must exactly match resolved device: {resolved}")
    related = [source for source in mounted_sources() if device_related(source, resolved)]
    if related:
        raise HC1Error("refusing mounted target: " + ", ".join(map(str, related)))
    if image.stat().st_size > block_device_size(resolved):
        raise HC1Error("image is larger than target device")
    return resolved


def flash(image: Path, device: Path, confirmation: str) -> None:
    require_linux_root()
    if not image.is_file():
        raise HC1Error(f"prepared image not found: {image}")
    target = validate_flash_device(device, image, confirmation)
    print(f"ERASING AND WRITING {target} from {image}", flush=True)
    with image.open("rb") as src, target.open("wb", buffering=0) as dst:
        while chunk := src.read(COPY_CHUNK):
            dst.write(chunk)
        os.fsync(dst.fileno())
    print(f"flash complete: {target}")


def print_plan(base: Path | None, output: Path, keys: Path | None, device: Path | None) -> None:
    print("JETOS ODROID-HC1 SSH bootstrap plan")
    print("  1. Start from a known-bootable HC1 Linux image (temporary boot substrate).")
    print("  2. Inject current JETOS Python userspace and an armv7/HC1 target marker.")
    print("  3. Configure wired DHCP and key-only OpenSSH; no password login.")
    print("  4. Produce a raw image plus SHA-256 provenance manifest.")
    print("  5. Flash only an explicitly confirmed, unmounted block device.")
    print("  6. Never modify or format the HC1 SATA disk.")
    if base:
        print(f"  base image: {base}")
    print(f"  output: {output}")
    if keys:
        print(f"  authorized keys: {keys}")
    if device:
        print(f"  flash target: {device}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Prepare/flash an ODROID-HC1 JETOS SSH bootstrap image")
    sub = result.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="show the non-destructive bring-up plan")
    plan.add_argument("--base-image", type=Path)
    plan.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    plan.add_argument("--authorized-keys", type=Path)
    plan.add_argument("--device", type=Path)

    prep = sub.add_parser("prepare", help="create a JETOS-injected HC1 image")
    prep.add_argument("--base-image", type=Path, required=True)
    prep.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    prep.add_argument("--authorized-keys", type=Path, required=True)
    prep.add_argument("--root-partition", type=int, default=2)
    prep.add_argument("--hostname", default="jetos-hc1")

    write = sub.add_parser("flash", help="destructively write a prepared image to microSD")
    write.add_argument("--image", type=Path, default=DEFAULT_OUTPUT)
    write.add_argument("--device", type=Path, required=True)
    write.add_argument(
        "--confirm-device",
        required=True,
        help="must exactly match the resolved /dev block device",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "plan":
            print_plan(args.base_image, args.output, args.authorized_keys, args.device)
        elif args.command == "prepare":
            prepare(args.base_image, args.output, args.authorized_keys, args.root_partition, args.hostname)
        elif args.command == "flash":
            flash(args.image, args.device, args.confirm_device)
    except (HC1Error, OSError, subprocess.CalledProcessError) as error:
        print(f"hc1-flash: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
