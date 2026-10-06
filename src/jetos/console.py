"""Shared JETOS interactive-console prompt behavior."""
from __future__ import annotations

import code
from contextlib import contextmanager
import sys
from typing import Iterator

from jetos.identity import UserIdentity, current_user


def primary_prompt(user: UserIdentity | None = None) -> str:
    identity = user or current_user()
    return f"{identity.label}@jetos> "


def continuation_prompt(user: UserIdentity | None = None) -> str:
    identity = user or current_user()
    return f"{identity.label}@jetos...> "


@contextmanager
def python_prompts(user: UserIdentity | None = None) -> Iterator[UserIdentity]:
    """Temporarily install JETOS user-attributed prompts for code.interact()."""
    identity = user or current_user()
    missing = object()
    old_ps1 = getattr(sys, "ps1", missing)
    old_ps2 = getattr(sys, "ps2", missing)
    sys.ps1 = primary_prompt(identity)
    sys.ps2 = continuation_prompt(identity)
    try:
        yield identity
    finally:
        if old_ps1 is missing:
            delattr(sys, "ps1")
        else:
            sys.ps1 = old_ps1
        if old_ps2 is missing:
            delattr(sys, "ps2")
        else:
            sys.ps2 = old_ps2


def interact(
    *,
    namespace: dict[str, object],
    user: UserIdentity | None = None,
    banner: str = "JETOS Language console",
    exitmsg: str = "Leaving JETOS Language console",
) -> None:
    identity = user or current_user()
    namespace.setdefault("user", identity)
    with python_prompts(identity):
        code.interact(banner=banner, local=namespace, exitmsg=exitmsg)
