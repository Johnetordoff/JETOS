#!/usr/bin/env python3
"""Contract checks for the Green-Gate dependency/minimization ledger."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/runtime-dependencies.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["schema"] == 1
    policy = data["policy"]
    assert "JETOS_STDLIB_QUALIFICATION=PASS" in policy["baseline"]
    assert "one candidate removal at a time" in policy["minimization"]

    names = {
        entry["name"]
        for group in ("kernel_facilities", "early_userspace", "etc_files")
        for entry in data[group]
    }
    expected = {
        "CONFIG_UNIX98_PTYS", "CONFIG_SHMEM", "CONFIG_INET", "CONFIG_FUTEX", "CONFIG_EPOLL",
        "devpts", "/dev/shm", "loopback", "/tmp mode 1777", "libgcc_s.so.1",
        "/etc/passwd", "/etc/group", "/etc/hosts", "/etc/nsswitch.conf", "/etc/services", "/etc/protocols",
    }
    assert expected <= names
    for group in ("kernel_facilities", "early_userspace", "etc_files"):
        for entry in data[group]:
            assert entry["reason"]
            assert entry["status"] == "bringup-required-candidate"
    print(f"runtime dependency manifest: PASS ({len(names)} candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
