"""Canonical JETOS deployment modes.

Fat and Skinny are two packaging personalities of the same operating system.
They share runtime APIs and behavior; the difference is how much development
source/tooling is carried on the machine.
"""
from __future__ import annotations

FAT = "fat"
SKINNY = "skinny"
MODES = (FAT, SKINNY)
LEGACY_ALIASES = {"full": FAT, "lean": SKINNY}
CLI_CHOICES = (*MODES, *LEGACY_ALIASES)


def normalize(value: str) -> str:
    """Return the canonical Fat/Skinny spelling for a CLI/profile value."""
    normalized = value.strip().lower()
    normalized = LEGACY_ALIASES.get(normalized, normalized)
    if normalized not in MODES:
        raise ValueError(f"unknown JETOS mode: {value!r}")
    return normalized


def carries_development_source(value: str) -> bool:
    """Whether this mode carries editable JETOS + JETOS Language source."""
    return normalize(value) == FAT


def description(value: str) -> str:
    mode = normalize(value)
    if mode == FAT:
        return (
            "personal-computer/developer mode: editable JETOS and JETOS Language "
            "source, tests, inspection surfaces, and development tools are retained"
        )
    return (
        "device/runtime mode: development-only source/tests/tools may be omitted, "
        "while runtime APIs, diagnostics, and reproducible provenance are retained"
    )
