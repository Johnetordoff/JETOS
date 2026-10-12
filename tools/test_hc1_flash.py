#!/usr/bin/env python3
"""Fast tests for the ODROID-HC1 SSH bootstrap tooling."""
from __future__ import annotations

import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hc1_flash  # noqa: E402


class HC1FlashTests(unittest.TestCase):
    def test_partition_path(self) -> None:
        self.assertEqual(hc1_flash.partition_path(Path("/dev/sdb"), 2), Path("/dev/sdb2"))
        self.assertEqual(hc1_flash.partition_path(Path("/dev/mmcblk0"), 2), Path("/dev/mmcblk0p2"))
        self.assertEqual(hc1_flash.partition_path(Path("/dev/loop7"), 2), Path("/dev/loop7p2"))

    def test_partition_path_rejects_zero(self) -> None:
        with self.assertRaises(hc1_flash.HC1Error):
            hc1_flash.partition_path(Path("/dev/sdb"), 0)

    def test_authorized_keys_accepts_public_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys"
            path.write_text(
                "# comment\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest user@example\n",
                encoding="utf-8",
            )
            self.assertEqual(
                hc1_flash.read_authorized_keys(path),
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest user@example\n",
            )

    def test_authorized_keys_rejects_private_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys"
            path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n", encoding="utf-8")
            with self.assertRaises(hc1_flash.HC1Error):
                hc1_flash.read_authorized_keys(path)

    def test_device_related(self) -> None:
        self.assertTrue(hc1_flash.device_related(Path("/dev/sdb2"), Path("/dev/sdb")))
        self.assertTrue(hc1_flash.device_related(Path("/dev/mmcblk0p2"), Path("/dev/mmcblk0")))
        self.assertFalse(hc1_flash.device_related(Path("/dev/sdc1"), Path("/dev/sdb")))

    def test_configure_rootfs_installs_jetos_and_key_only_ssh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "usr/bin/python3",
                "usr/sbin/sshd",
                "usr/bin/ssh-keygen",
                "usr/lib/systemd/systemd-networkd",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"")
            (root / "etc/ssh/sshd_config.d").mkdir(parents=True)

            hc1_flash.configure_rootfs(
                root,
                "ssh-ed25519 AAAATEST user@example\n",
                "a" * 64,
                "jetos-hc1",
            )

            marker = json.loads((root / "etc/jetos/target.json").read_text(encoding="utf-8"))
            self.assertEqual(marker["board"], "odroid-hc1")
            self.assertEqual(marker["cpu_arch"], "armv7")
            self.assertEqual(marker["sata_policy"], "untouched")

            keys = root / "root/.ssh/authorized_keys"
            self.assertEqual(stat.S_IMODE(keys.stat().st_mode), 0o600)
            ssh_config = (root / "etc/ssh/sshd_config.d/99-jetos-bootstrap.conf").read_text(encoding="utf-8")
            self.assertIn("PasswordAuthentication no", ssh_config)
            self.assertIn("PermitRootLogin prohibit-password", ssh_config)
            network = (root / "etc/systemd/network/20-jetos-wired.network").read_text(encoding="utf-8")
            self.assertIn("DHCP=yes", network)
            self.assertTrue((root / "opt/jetos/src/jetos/init.py").is_file())
            self.assertTrue((root / "usr/local/bin/jetos-console").is_file())
            self.assertTrue((root / "etc/systemd/system/multi-user.target.wants/jetos-sshd.service").is_symlink())


if __name__ == "__main__":
    unittest.main(verbosity=2)
