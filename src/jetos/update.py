"""Git-backed live userspace updates for a running JETOS machine."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys


def repository_path() -> Path:
    configured = os.environ.get("JETOS_REPO")
    candidates = [
        Path(configured) if configured else None,
        Path("/state/jetos"),
        Path(__file__).resolve().parents[2],
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / ".git").exists():
            return candidate
    raise SystemExit("JETOS live Git repository was not found")


def git(repo: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=capture,
    )


def working_tree_clean(repo: Path) -> bool:
    return not git(repo, "status", "--porcelain", capture=True).stdout.strip()


def current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current", capture=True).stdout.strip()


def run_validation(repo: Path) -> None:
    subprocess.run(
        [sys.executable, "jetos.py", "test"],
        cwd=repo,
        check=True,
        text=True,
    )


def pull(
    *,
    remote: str = "origin",
    branch: str | None = None,
    validate: bool = True,
    restart: bool = False,
) -> tuple[str, str]:
    repo = repository_path()
    if not working_tree_clean(repo):
        raise SystemExit(
            "JETOS update refused: live repository has local changes; "
            "commit/stash/review them first"
        )
    branch = branch or current_branch(repo)
    if not branch:
        raise SystemExit("JETOS update refused: repository is in detached HEAD state")

    before = git(repo, "rev-parse", "HEAD", capture=True).stdout.strip()
    git(repo, "fetch", "--prune", remote, branch)
    git(repo, "merge", "--ff-only", f"{remote}/{branch}")
    after = git(repo, "rev-parse", "HEAD", capture=True).stdout.strip()

    if validate:
        try:
            run_validation(repo)
        except Exception:
            if after != before:
                git(repo, "reset", "--hard", before)
            raise

    if restart:
        request_userspace_restart()
    return before, after


def request_userspace_restart() -> None:
    os.kill(1, signal.SIGHUP)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update running JETOS from its Git repository")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch")
    parser.add_argument("--no-test", action="store_true")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()

    before, after = pull(
        remote=args.remote,
        branch=args.branch,
        validate=not args.no_test,
        restart=args.restart,
    )
    if before == after:
        print(f"JETOS already current at {after[:12]}")
    else:
        print(f"JETOS updated {before[:12]} -> {after[:12]}")
        if not args.restart:
            print("Run again with --restart to restart JETOS userspace into the new source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
