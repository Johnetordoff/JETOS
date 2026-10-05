#!/usr/bin/env python3
"""Fast structural tests for the Raspberry Pi image definition."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jetos_pi", ROOT / "tools/pi.py")
assert SPEC and SPEC.loader
pi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pi)

checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


check(set(pi.MODEL_SPECS) == {"pi4", "pi5"}, "Pi 4 and Pi 5 should be explicit targets")
check("kernel8.img" in pi.config_text("pi4"), "Pi 4 config should select kernel8.img")
check("kernel_2712.img" in pi.config_text("pi5"), "Pi 5 config should select kernel_2712.img")
check("jetos.network=off" in pi.cmdline_text("off"), "network-off policy should be explicit")
check("ip=dhcp" not in pi.cmdline_text("off"), "network-off boot must not request DHCP")
check("jetos.network=on" in pi.cmdline_text("on"), "network-on policy should be explicit")
check("ip=dhcp" in pi.cmdline_text("on"), "network-on boot should request kernel DHCP")

mbr = pi.mbr_bytes(
    boot_first_lba=2048,
    boot_sectors=524288,
    state_first_lba=526336,
    state_sectors=100000,
)
check(len(mbr) == 512, "MBR must be one sector")
check(mbr[510:512] == b"\x55\xaa", "MBR boot signature missing")
boot = struct.unpack("<B3sB3sII", mbr[446:462])
state = struct.unpack("<B3sB3sII", mbr[462:478])
check(boot[0] == 0x80 and boot[2] == 0x0C, "boot partition should be bootable FAT32 LBA")
check(boot[4] == 2048 and boot[5] == 524288, "boot partition LBA geometry wrong")
check(state[0] == 0 and state[2] == 0x83, "state partition should be Linux/ext4")
check(state[4] == 526336 and state[5] == 100000, "state partition LBA geometry wrong")

print(f"JETOS Raspberry Pi image definition: {checks} checks passed")
