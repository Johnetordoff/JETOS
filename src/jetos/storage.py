"""JETOS persistent-storage encryption policy.

JETOS does not implement novel file encryption in Python.  Ordinary persistent
files are expected to live on a Linux dm-crypt-backed volume so normal open(),
read(), write(), mmap(), and page-cache behavior remain transparent while bytes
at rest are encrypted below the filesystem.

Plaintext in RAM is expected while data is in use.  Plaintext persistent storage
is an explicit, auditable exception and must never be a hidden bypass.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
from typing import Iterable


MEMORY_FILESYSTEMS = frozenset({"tmpfs", "ramfs", "devtmpfs"})
DM_CRYPT_UUID_PREFIXES = ("CRYPT-", "CRYPT-LUKS1-", "CRYPT-LUKS2-")


@dataclass(frozen=True)
class MountRecord:
    mountpoint: str
    filesystem: str
    source: str
    major_minor: str


@dataclass(frozen=True)
class StorageState:
    path: str
    mountpoint: str
    filesystem: str
    source: str
    major_minor: str
    disposition: str
    encrypted: bool
    persistent: bool
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PlaintextException:
    prefix: str
    reason: str
    owner: str = "JETOS"


class StoragePolicyError(RuntimeError):
    pass


def _unescape_mount_field(value: str) -> str:
    # mountinfo escapes space/tab/newline/backslash as octal sequences.
    replacements = {
        "\\040": " ",
        "\\011": "\t",
        "\\012": "\n",
        "\\134": "\\",
    }
    for encoded, decoded in replacements.items():
        value = value.replace(encoded, decoded)
    return value


def parse_mountinfo(text: str) -> tuple[MountRecord, ...]:
    records: list[MountRecord] = []
    for raw in text.splitlines():
        if not raw.strip() or " - " not in raw:
            continue
        left, right = raw.split(" - ", 1)
        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 5 or len(right_fields) < 2:
            continue
        records.append(
            MountRecord(
                mountpoint=_unescape_mount_field(left_fields[4]),
                filesystem=right_fields[0],
                source=_unescape_mount_field(right_fields[1]),
                major_minor=left_fields[2],
            )
        )
    return tuple(records)


def _contains(path: str, prefix: str) -> bool:
    normalized_path = os.path.normpath(path)
    normalized_prefix = os.path.normpath(prefix)
    if normalized_prefix == "/":
        return normalized_path.startswith("/")
    return normalized_path == normalized_prefix or normalized_path.startswith(
        normalized_prefix.rstrip("/") + "/"
    )


def mount_for_path(path: str | os.PathLike[str], records: Iterable[MountRecord]) -> MountRecord:
    absolute = os.path.abspath(os.fspath(path))
    candidates = [record for record in records if _contains(absolute, record.mountpoint)]
    if not candidates:
        raise StoragePolicyError(f"no mount record covers {absolute}")
    return max(candidates, key=lambda record: len(os.path.normpath(record.mountpoint)))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="strict").strip()
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError, UnicodeError):
        return None


def dm_uuid(root: Path, major_minor: str) -> str | None:
    # /sys/dev/block/MAJOR:MINOR is normally a symlink into /sys/devices.  Tests
    # may provide a normal directory with the same observable layout.
    return _read_text(root / "sys/dev/block" / major_minor / "dm/uuid")


def _is_dm_crypt_uuid(value: str | None) -> bool:
    if not value:
        return False
    upper = value.upper()
    return any(upper.startswith(prefix) for prefix in DM_CRYPT_UUID_PREFIXES)


class StoragePolicy:
    """Classify paths and enforce JETOS persistent-encryption rules."""

    def __init__(
        self,
        *,
        root: str | os.PathLike[str] = "/",
        plaintext_exceptions: Iterable[PlaintextException] = (),
    ) -> None:
        self.root = Path(root)
        self.plaintext_exceptions = tuple(plaintext_exceptions)

    def mounts(self) -> tuple[MountRecord, ...]:
        text = _read_text(self.root / "proc/self/mountinfo")
        if text is None:
            raise StoragePolicyError("/proc/self/mountinfo is unavailable")
        return parse_mountinfo(text)

    def _exception_for(self, path: str) -> PlaintextException | None:
        matches = [
            exception
            for exception in self.plaintext_exceptions
            if _contains(path, exception.prefix)
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: len(os.path.normpath(item.prefix)))

    def inspect(self, path: str | os.PathLike[str]) -> StorageState:
        absolute = os.path.abspath(os.fspath(path))
        mount = mount_for_path(absolute, self.mounts())
        evidence = [
            f"mount:{mount.mountpoint}",
            f"filesystem:{mount.filesystem}",
            f"source:{mount.source}",
            f"device:{mount.major_minor}",
        ]

        if mount.filesystem in MEMORY_FILESYSTEMS:
            return StorageState(
                absolute,
                mount.mountpoint,
                mount.filesystem,
                mount.source,
                mount.major_minor,
                "memory-plaintext",
                encrypted=False,
                persistent=False,
                evidence=tuple(evidence + ["ephemeral-memory-filesystem"]),
            )

        uuid = dm_uuid(self.root, mount.major_minor)
        if uuid:
            evidence.append(f"dm-uuid:{uuid}")
        if _is_dm_crypt_uuid(uuid):
            return StorageState(
                absolute,
                mount.mountpoint,
                mount.filesystem,
                mount.source,
                mount.major_minor,
                "encrypted",
                encrypted=True,
                persistent=True,
                evidence=tuple(evidence),
            )

        exception = self._exception_for(absolute)
        if exception is not None:
            evidence.extend(
                [
                    f"plaintext-exception:{exception.prefix}",
                    f"reason:{exception.reason}",
                    f"owner:{exception.owner}",
                ]
            )
            return StorageState(
                absolute,
                mount.mountpoint,
                mount.filesystem,
                mount.source,
                mount.major_minor,
                "plaintext-exception",
                encrypted=False,
                persistent=True,
                evidence=tuple(evidence),
            )

        return StorageState(
            absolute,
            mount.mountpoint,
            mount.filesystem,
            mount.source,
            mount.major_minor,
            "unprotected",
            encrypted=False,
            persistent=True,
            evidence=tuple(evidence),
        )

    def require_safe(self, path: str | os.PathLike[str]) -> StorageState:
        state = self.inspect(path)
        if state.disposition == "unprotected":
            raise StoragePolicyError(
                f"persistent path is not protected by dm-crypt and has no "
                f"explicit plaintext exception: {state.path}"
            )
        return state


def default_policy(root: str | os.PathLike[str] = "/") -> StoragePolicy:
    # The early boot partition may need to remain readable by firmware.  It may
    # contain only non-secret boot artifacts.  Additional exceptions require an
    # explicit policy change; there is intentionally no secret bypass flag.
    return StoragePolicy(
        root=root,
        plaintext_exceptions=(
            PlaintextException(
                "/boot",
                "firmware-readable boot artifacts only; no user secrets",
                owner="JETOS boot policy",
            ),
        ),
    )


def status(path: str | os.PathLike[str] = "/", *, root: str | os.PathLike[str] = "/") -> dict[str, object]:
    return default_policy(root).inspect(path).as_dict()
