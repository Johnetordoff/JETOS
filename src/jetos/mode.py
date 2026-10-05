"""Canonical JETOS deployment modes.

Fat and Skinny are two deployment personalities of the same JETOS version.
They share runtime APIs and source lineage. Fat is the general-purpose developer
system; Skinny is a target-specific application/runtime image derived from Fat.
"""
from __future__ import annotations

from dataclasses import dataclass

FAT = "fat"
SKINNY = "skinny"
MODES = (FAT, SKINNY)
LEGACY_ALIASES = {"full": FAT, "lean": SKINNY}
CLI_CHOICES = (*MODES, *LEGACY_ALIASES)


@dataclass(frozen=True)
class ModePolicy:
    name: str
    general_purpose_app_host: bool
    carries_development_source: bool
    carries_kernel_source: bool
    can_derive_skinny_images: bool
    application_model: str


FAT_POLICY = ModePolicy(
    name=FAT,
    general_purpose_app_host=True,
    carries_development_source=True,
    carries_kernel_source=True,
    can_derive_skinny_images=True,
    application_model="general-purpose compatible applications",
)

SKINNY_POLICY = ModePolicy(
    name=SKINNY,
    general_purpose_app_host=False,
    carries_development_source=False,
    carries_kernel_source=False,
    can_derive_skinny_images=False,
    application_model="explicit target application/capability set",
)


def normalize(value: str) -> str:
    """Return the canonical Fat/Skinny spelling for a CLI/profile value."""
    normalized = value.strip().lower()
    normalized = LEGACY_ALIASES.get(normalized, normalized)
    if normalized not in MODES:
        raise ValueError(f"unknown JETOS mode: {value!r}")
    return normalized


def policy(value: str) -> ModePolicy:
    """Return the immutable deployment policy for a mode or legacy alias."""
    return FAT_POLICY if normalize(value) == FAT else SKINNY_POLICY


def carries_development_source(value: str) -> bool:
    return policy(value).carries_development_source


def carries_kernel_source(value: str) -> bool:
    return policy(value).carries_kernel_source


def can_derive_skinny_images(value: str) -> bool:
    return policy(value).can_derive_skinny_images


def description(value: str) -> str:
    selected = policy(value)
    if selected.name == FAT:
        return (
            "personal-computer/developer mode: general-purpose applications, editable "
            "JETOS/JETOS Language/Linux source, tests, inspection surfaces, and build "
            "tools are retained; this mode can derive target-specific Skinny images"
        )
    return (
        "device/application mode: development source/tools may be omitted and execution "
        "is constrained to the target application/capability set, while runtime APIs, "
        "diagnostics, version identity, and reproducible provenance are retained"
    )
