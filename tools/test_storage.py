#!/usr/bin/env python3
"""Tests for JETOS transparent persistent-storage encryption policy."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos.storage import (  # noqa: E402
    PlaintextException,
    PlaintextMemoryCache,
    StoragePolicy,
    StoragePolicyError,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write(
            root / "proc/self/mountinfo",
            "\n".join(
                [
                    "20 1 253:1 / / rw,relatime - ext4 /dev/mapper/jetos-root rw",
                    "21 20 0:5 / /tmp rw,nosuid,nodev - tmpfs tmpfs rw",
                    "22 20 8:1 / /boot rw,relatime - ext4 /dev/vda1 rw",
                    "23 20 8:2 / /plaintext rw,relatime - ext4 /dev/vda2 rw",
                    "24 20 0:1 / /run/initramfs rw - rootfs rootfs rw",
                ]
            )
            + "\n",
        )
        write(root / "sys/dev/block/253:1/dm/uuid", "LVM-deadbeef\n")
        write(root / "sys/dev/block/253:1/slaves/dm-0/dev", "253:0\n")
        write(root / "sys/dev/block/253:0/dm/uuid", "CRYPT-LUKS2-deadbeef-jetos\n")

        policy = StoragePolicy(
            root=root,
            plaintext_exceptions=(
                PlaintextException("/boot", "firmware boot files"),
                PlaintextException("/plaintext", "explicit test exception"),
            ),
        )

        encrypted = policy.inspect("/home/user/file.txt")
        check(encrypted.encrypted, "stacked root volume should be encrypted")
        check(encrypted.disposition == "encrypted", "encrypted disposition")
        check(any("CRYPT-LUKS2" in item for item in encrypted.evidence), "dm-crypt evidence")
        checks += 3

        memory = policy.inspect("/tmp/cache.bin")
        check(not memory.persistent, "tmpfs should be memory-only")
        check(memory.disposition == "memory-plaintext", "memory disposition")
        checks += 2

        initramfs = policy.inspect("/run/initramfs/state")
        check(not initramfs.persistent, "rootfs should be memory-only")
        check(initramfs.disposition == "memory-plaintext", "rootfs disposition")
        checks += 2

        boot = policy.inspect("/boot/vmlinuz")
        check(boot.disposition == "plaintext-authorized", "boot exception")
        checks += 1

        plain = policy.inspect("/plaintext/export.bin")
        check(plain.disposition == "plaintext-authorized", "explicit plaintext exception")
        checks += 1

        strict = StoragePolicy(root=root)
        unsafe = strict.inspect("/boot/vmlinuz")
        check(unsafe.disposition == "unprotected", "unprotected mount detection")
        checks += 1
        try:
            strict.require_safe("/boot/vmlinuz")
        except StoragePolicyError:
            checks += 1
        else:
            raise AssertionError("unprotected persistent storage was accepted")

        check(policy.require_safe("/home/user/file.txt").encrypted, "encrypted safe path")
        check(not policy.require_safe("/tmp/cache.bin").persistent, "RAM safe path")
        checks += 2

        cache = PlaintextMemoryCache()
        cache.put("document", b"secret plaintext")
        check(cache.get("document") == b"secret plaintext", "memory cache read")
        cache.drop("document")
        check(cache.get("document") is None, "memory cache drop")
        checks += 2

    print(f"JETOS storage encryption policy: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
