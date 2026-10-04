#!/usr/bin/env python3
"""Synthetic-filesystem tests for JETOS capability discovery."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jetos import apps, hardware  # noqa: E402


def write(root: Path, relative: str, text: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def directory(root: Path, relative: str) -> None:
    (root / relative).mkdir(parents=True, exist_ok=True)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        write(root, "proc/meminfo", "MemTotal:       1048576 kB\n")
        write(root, "sys/class/net/lo/operstate", "unknown\n")
        write(root, "sys/class/net/eth0/operstate", "up\n")
        write(root, "sys/class/net/wlan0/operstate", "down\n")
        directory(root, "sys/class/net/wlan0/wireless")
        directory(root, "sys/class/ieee80211/phy0")

        write(root, "sys/class/drm/card0-HDMI-A-1/status", "connected\n")
        write(root, "sys/class/drm/card0-HDMI-A-1/modes", "1920x1080\n1280x720\n")
        directory(root, "sys/class/sound/card0")
        directory(root, "sys/class/input/input0")
        write(root, "sys/block/nvme0n1/size", "2000000\n")
        write(root, "sys/class/power_supply/BAT0/type", "Battery\n")
        write(root, "sys/class/power_supply/BAT0/capacity", "83\n")
        write(root, "sys/class/power_supply/BAT0/status", "Discharging\n")
        directory(root, "sys/class/bluetooth/hci0")
        directory(root, "sys/class/tty/ttyS0")
        write(root, "dev/video0", "")
        write(root, "dev/kvm", "")

        snap = hardware.discover(root)
        caps = snap["capabilities"]
        assert isinstance(caps, dict)

        for name in (
            "display",
            "network",
            "wireless",
            "bluetooth",
            "audio",
            "storage",
            "input",
            "camera",
            "battery",
            "virtualization",
            "serial",
        ):
            check(bool(caps[name]["present"]), f"{name} not detected")
            checks += 1

        check(bool(caps["network"]["active"]), "active Ethernet not detected")
        check(not bool(caps["wireless"]["active"]), "down Wi-Fi marked active")
        check(snap["memory_bytes"] == 1073741824, "memory conversion")
        checks += 3

        display_evidence = tuple(caps["display"]["evidence"])
        check(
            "mode:card0-HDMI-A-1:1920x1080" in display_evidence,
            "display mode evidence missing",
        )
        checks += 1

        titles = {app.title for app in apps.available(snap)}
        for title in (
            "Terminal",
            "System",
            "Display",
            "Network",
            "Wireless",
            "Bluetooth",
            "Storage",
            "Audio",
            "Input",
            "Camera",
            "Power",
            "Virtualization",
            "Serial",
        ):
            check(title in titles, f"{title} app missing")
            checks += 1

    with tempfile.TemporaryDirectory() as temp:
        empty = hardware.discover(Path(temp))
        titles = [app.title for app in apps.available(empty)]
        check(titles == ["Terminal", "System"], "empty machine app registry")
        checks += 1

    print(f"JETOS capabilities: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
