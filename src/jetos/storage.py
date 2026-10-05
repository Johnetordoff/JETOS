"""JETOS persistent-storage encryption policy.

Persistent encryption is a policy of the storage domain, not a Python file
format.  Normal JETOS I/O stays ordinary; dm-crypt/LUKS is the initial native
implementation beneath the filesystem.

The global policy defaults to encryption ON.  It may be deliberately turned
OFF for a development/test system, and individual path scopes may override the
global choice in either direction.  Every override is explicit and auditable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os
from typing import Iterable


MEMORY_FILESYSTEMS = frozenset({"tmpfs", "ramfs", "rootfs", "devtmpfs"})
DM_CRYPT_UUID_PREFIXES = ("CRYPT-",)


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
    encryption_required: bool
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EncryptionOverride:
    """Explicit per-scope override of the global encryption requirement."""

    prefix: str
    enabled: bool
    reason: str
    owner: str = "JETOS"


@dataclass(frozen=True)
class PlaintextException:
    """Compatibility spelling for an explicit encryption-disabled scope."""

    prefix: str
    reason: str
    owner: str = "JETOS"

    def as_override(self) -> EncryptionOverride:
        return EncryptionOverride(
            prefix=self.prefix,
            enabled=False,
            reason=self.reason,
            owner=self.owner,
        )


class StoragePolicyError(RuntimeError):
    pass


class PlaintextMemoryCache:
    """Best-effort in-memory cache for decrypted disposable bytes.

    Values are process-memory only.  bytearray permits overwriting this cache's
    own buffers before release, but CPython/the allocator/kernel/hardware may
    have retained copies.  This is not a cryptographic memory-erasure guarantee.
    """

    def __init__(self) -> None:
        self._values: dict[str, bytearray] = {}

    def put(self, key: str, value: bytes | bytearray | memoryview) -> None:
        self.drop(key)
        self._values[key] = bytearray(value)

    def get(self, key: str) -> bytes | None:
        value = self._values.get(key)
        return None if value is None else bytes(value)

    def drop(self, key: str) -> None:
        value = self._values.pop(key, None)
        if value is not None:
            value[:] = b"\x00" * len(value)

    def clear(self) -> None:
        for key in tuple(self._values):
            self.drop(key)

    def __enter__(self) -> "PlaintextMemoryCache":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.clear()


def _unescape_mount_field(value: str) -> str:
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


def _children(path: Path) -> tuple[Path, ...]:
    try:
        return tuple(sorted(path.iterdir(), key=lambda item: item.name))
    except (FileNotFoundError, PermissionError, NotADirectoryError, OSError):
        return ()


def _is_dm_crypt_uuid(value: str | None) -> bool:
    return bool(value and value.upper().startswith(DM_CRYPT_UUID_PREFIXES))


def encryption_chain(root: Path, major_minor: str) -> tuple[bool, tuple[str, ...]]:
    """Walk stacked Linux block devices looking for a dm-crypt layer."""
    seen: set[str] = set()
    evidence: list[str] = []

    def walk(device: str) -> bool:
        if device in seen:
            return False
        seen.add(device)
        path = root / "sys/dev/block" / device
        uuid = _read_text(path / "dm/uuid")
        if uuid:
            evidence.append(f"dm-uuid:{device}:{uuid}")
            if _is_dm_crypt_uuid(uuid):
                return True

        encrypted = False
        for slave in _children(path / "slaves"):
            slave_device = _read_text(slave / "dev")
            if slave_device:
                evidence.append(f"slave:{device}->{slave_device}")
                encrypted = walk(slave_device) or encrypted
            else:
                slave_uuid = _read_text(slave / "dm/uuid")
                if slave_uuid:
                    evidence.append(f"slave-dm-uuid:{device}:{slave.name}:{slave_uuid}")
                    encrypted = _is_dm_crypt_uuid(slave_uuid) or encrypted
        return encrypted

    return walk(major_minor), tuple(evidence)


def parse_encryption_mode(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"on", "true", "yes", "1", "required"}:
        return True
    if normalized in {"off", "false", "no", "0", "disabled"}:
        return False
    raise ValueError(f"invalid encryption mode: {value!r}")


def encryption_from_cmdline(text: str, default: bool = True) -> bool:
    enabled = default
    for item in text.split():
        if item.startswith("jetos.encryption="):
            enabled = parse_encryption_mode(item.split("=", 1)[1])
    return enabled


class StoragePolicy:
    """Classify paths and enforce a global+scoped encryption policy."""

    def __init__(
        self,
        *,
        root: str | os.PathLike[str] = "/",
        encryption_enabled: bool = True,
        overrides: Iterable[EncryptionOverride] = (),
        plaintext_exceptions: Iterable[PlaintextException] = (),
    ) -> None:
        self.root = Path(root)
        self.encryption_enabled = bool(encryption_enabled)
        self.overrides = tuple(overrides) + tuple(
            exception.as_override() for exception in plaintext_exceptions
        )

    def mounts(self) -> tuple[MountRecord, ...]:
        text = _read_text(self.root / "proc/self/mountinfo")
        if text is None:
            raise StoragePolicyError("/proc/self/mountinfo is unavailable")
        return parse_mountinfo(text)

    def _override_for(self, path: str) -> EncryptionOverride | None:
        matches = [override for override in self.overrides if _contains(path, override.prefix)]
        if not matches:
            return None
        return max(matches, key=lambda item: len(os.path.normpath(item.prefix)))

    def inspect(self, path: str | os.PathLike[str]) -> StorageState:
        absolute = os.path.abspath(os.fspath(path))
        mount = mount_for_path(absolute, self.mounts())
        override = self._override_for(absolute)
        required = self.encryption_enabled if override is None else override.enabled
        evidence = [
            f"mount:{mount.mountpoint}",
            f"filesystem:{mount.filesystem}",
            f"source:{mount.source}",
            f"device:{mount.major_minor}",
            f"global-encryption:{'on' if self.encryption_enabled else 'off'}",
        ]
        if override is not None:
            evidence.extend(
                [
                    f"override:{override.prefix}:{'on' if override.enabled else 'off'}",
                    f"reason:{override.reason}",
                    f"owner:{override.owner}",
                ]
            )

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
                encryption_required=False,
                evidence=tuple(evidence + ["ephemeral-memory-filesystem"]),
            )

        encrypted, chain_evidence = encryption_chain(self.root, mount.major_minor)
        evidence.extend(chain_evidence)
        if encrypted:
            return StorageState(
                absolute,
                mount.mountpoint,
                mount.filesystem,
                mount.source,
                mount.major_minor,
                "encrypted",
                encrypted=True,
                persistent=True,
                encryption_required=required,
                evidence=tuple(evidence),
            )

        if not required:
            return StorageState(
                absolute,
                mount.mountpoint,
                mount.filesystem,
                mount.source,
                mount.major_minor,
                "plaintext-authorized",
                encrypted=False,
                persistent=True,
                encryption_required=False,
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
            encryption_required=True,
            evidence=tuple(evidence),
        )

    def require_safe(self, path: str | os.PathLike[str]) -> StorageState:
        state = self.inspect(path)
        if state.disposition == "unprotected":
            raise StoragePolicyError(
                "persistent path requires encryption but no dm-crypt layer was found: "
                f"{state.path}"
            )
        return state


def default_overrides() -> tuple[EncryptionOverride, ...]:
    return (
        EncryptionOverride(
            "/boot",
            enabled=False,
            reason="firmware-readable boot artifacts only; no user secrets",
            owner="JETOS boot policy",
        ),
    )


def default_policy(
    root: str | os.PathLike[str] = "/",
    *,
    encryption_enabled: bool = True,
    overrides: Iterable[EncryptionOverride] = (),
) -> StoragePolicy:
    return StoragePolicy(
        root=root,
        encryption_enabled=encryption_enabled,
        overrides=(*default_overrides(), *tuple(overrides)),
    )


def policy_from_cmdline(root: str | os.PathLike[str] = "/") -> StoragePolicy:
    root_path = Path(root)
    cmdline = _read_text(root_path / "proc/cmdline") or ""
    return default_policy(
        root=root,
        encryption_enabled=encryption_from_cmdline(cmdline, default=True),
    )


def load_policy(path: str | os.PathLike[str], *, root: str | os.PathLike[str] = "/") -> StoragePolicy:
    """Load explicit global/scoped policy from a small JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise StoragePolicyError("storage policy JSON must be an object")
    enabled = parse_encryption_mode(data.get("encryption", True))
    raw_overrides = data.get("overrides", [])
    if not isinstance(raw_overrides, list):
        raise StoragePolicyError("storage policy overrides must be a list")
    overrides: list[EncryptionOverride] = []
    for item in raw_overrides:
        if not isinstance(item, dict):
            raise StoragePolicyError("each storage override must be an object")
        try:
            prefix = os.fspath(item["prefix"])
            override_enabled = parse_encryption_mode(item["encryption"])
            reason = str(item["reason"])
        except KeyError as error:
            raise StoragePolicyError(f"missing storage override field: {error.args[0]}") from error
        overrides.append(
            EncryptionOverride(
                prefix=prefix,
                enabled=override_enabled,
                reason=reason,
                owner=str(item.get("owner", "JETOS storage policy")),
            )
        )
    return default_policy(root=root, encryption_enabled=enabled, overrides=overrides)


def status(
    path: str | os.PathLike[str] = "/",
    *,
    root: str | os.PathLike[str] = "/",
    encryption_enabled: bool = True,
) -> dict[str, object]:
    return default_policy(root, encryption_enabled=encryption_enabled).inspect(path).as_dict()
