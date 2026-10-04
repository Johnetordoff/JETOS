"""Small capability-oriented hardware inventory bootstrap."""
from __future__ import annotations
from pathlib import Path
import os
import platform


def snapshot() -> dict[str, object]:
    return {
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "has_sysfs": Path("/sys").is_dir(),
        "has_device_tree": Path("/sys/firmware/devicetree/base").exists(),
        "has_acpi": Path("/sys/firmware/acpi").exists(),
    }
