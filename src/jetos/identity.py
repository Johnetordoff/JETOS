"""JETOS session identity derived from the effective operating-system user."""
from __future__ import annotations

from dataclasses import dataclass
import getpass
import os

try:
    import pwd
except ImportError:  # Windows host previews do not provide pwd.
    pwd = None  # type: ignore[assignment]


@dataclass(frozen=True)
class UserIdentity:
    """The account whose permissions govern the current JETOS command context."""

    name: str
    uid: int | None
    gid: int | None
    source: str

    @property
    def label(self) -> str:
        return self.name

    def describe(self) -> str:
        identifiers: list[str] = []
        if self.uid is not None:
            identifiers.append(f"uid={self.uid}")
        if self.gid is not None:
            identifiers.append(f"gid={self.gid}")
        suffix = f" ({', '.join(identifiers)})" if identifiers else ""
        return self.name + suffix


def current_user() -> UserIdentity:
    """Resolve the effective permission identity without inventing a display user."""
    uid = os.geteuid() if hasattr(os, "geteuid") else None
    gid = os.getegid() if hasattr(os, "getegid") else None

    if uid is not None and pwd is not None:
        try:
            record = pwd.getpwuid(uid)
        except KeyError:
            record = None
        if record is not None and record.pw_name:
            return UserIdentity(record.pw_name, uid, gid, "effective uid")

    # Minimal initramfs images may have no passwd database. UID 0 still has a
    # well-defined Linux permission meaning, so preserve that conventional name.
    if uid == 0:
        return UserIdentity("root", uid, gid, "effective uid fallback")

    try:
        name = getpass.getuser().strip()
    except (ImportError, KeyError, OSError):
        name = ""
    if name:
        return UserIdentity(name, uid, gid, "host account")

    if uid is not None:
        return UserIdentity(f"uid{uid}", uid, gid, "numeric effective uid")
    return UserIdentity("unknown-user", None, gid, "unresolved")
