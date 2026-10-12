"""Canonical JETOS deployment-mode policy."""
from __future__ import annotations

from dataclasses import dataclass

FAT = "fat"
SKINNY = "skinny"
MODES = (FAT, SKINNY)


@dataclass(frozen=True)
class ModePolicy:
    name: str
    carries_complete_source: bool
    target_resolved: bool
    requires_compiled_native_runtime: bool
    can_derive_skinny: bool


FAT_POLICY = ModePolicy(
    name=FAT,
    carries_complete_source=True,
    target_resolved=False,
    requires_compiled_native_runtime=True,
    can_derive_skinny=True,
)

SKINNY_POLICY = ModePolicy(
    name=SKINNY,
    carries_complete_source=False,
    target_resolved=True,
    requires_compiled_native_runtime=True,
    can_derive_skinny=False,
)


def normalize(value: str) -> str:
    selected = value.strip().lower()
    if selected not in MODES:
        raise ValueError(f"unknown JETOS mode: {value!r}")
    return selected


def policy(value: str) -> ModePolicy:
    return FAT_POLICY if normalize(value) == FAT else SKINNY_POLICY
