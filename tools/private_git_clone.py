#!/usr/bin/env python3
"""Clone a private JetOS repository using native Git and ephemeral credentials.

Credentials are read from the environment and are never embedded in the remote URL,
written to Git config, or printed. This helper exists for worker/bootstrap hosts that
must use native Git against the private repository.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

DEFAULT_REPOSITORY = "https://github.com/Johnetordoff/JETOS.git"
TOKEN_VARIABLES = ("JETOS_GIT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")


def token_from_environment() -> str | None:
    for name in TOKEN_VARIABLES:
        value = os.environ.get(name)
        if value:
            return value
    return None


def clone(repository: str, destination: Path, depth: int | None) -> None:
    token = token_from_environment()
    if not token:
        raise SystemExit(
            "private Git authentication unavailable: set JETOS_GIT_TOKEN, GH_TOKEN, "
            "or GITHUB_TOKEN in the worker secret environment"
        )

    username = os.environ.get("JETOS_GIT_USERNAME", "x-access-token")
    with tempfile.TemporaryDirectory(prefix="jetos-git-auth-") as temporary:
        askpass = Path(temporary) / "askpass.py"
        askpass.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "prompt = ' '.join(sys.argv[1:]).lower()\n"
            "if 'username' in prompt:\n"
            "    print(os.environ.get('JETOS_GIT_USERNAME', 'x-access-token'))\n"
            "elif 'password' in prompt:\n"
            "    print(os.environ['JETOS_GIT_TOKEN'])\n"
            "else:\n"
            "    print('')\n",
            encoding="utf-8",
        )
        askpass.chmod(0o700)
        environment = os.environ.copy()
        environment["JETOS_GIT_TOKEN"] = token
        environment["JETOS_GIT_USERNAME"] = username
        environment["GIT_ASKPASS"] = str(askpass)
        environment["GIT_TERMINAL_PROMPT"] = "0"

        command = ["git", "clone"]
        if depth:
            command += ["--depth", str(depth)]
        command += [repository, str(destination)]
        subprocess.run(command, check=True, env=environment)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--depth", type=int, default=1)
    arguments = parser.parse_args()
    clone(arguments.repository, arguments.destination, arguments.depth)
    return 0


if __name__ == "__main__":
    sys.exit(main())
