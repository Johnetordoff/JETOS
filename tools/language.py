#!/usr/bin/env python3
"""Create, patch, build, and test the editable JETOS Language fork.

JETOS owns this orchestration in Python. CPython's existing configure/make
machinery is imported bootstrap infrastructure until it is replaced.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess

UPSTREAM_REPOSITORY = "https://github.com/python/cpython.git"
UPSTREAM_VERSION = "3.14.8"
UPSTREAM_COMMIT = "8e6e75d9102e39bed2a2b279203a396741180f12"
FORK_BRANCH = "jetos-language"
JETOS_LANGUAGE_VERSION = "0.2"


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def require_source_tree(source: Path) -> None:
    required = [
        source / "Python/sysmodule.c",
        source / "Include/patchlevel.h",
        source / "configure",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(
            "not a complete CPython source tree; missing: "
            + ", ".join(missing)
        )


def patch_source(source: Path) -> list[Path]:
    """Apply the first interpreter-owned JETOS identity changes."""
    require_source_tree(source)

    changed: list[Path] = []
    header = source / "Include/jetos.h"
    header_content = (
        "#ifndef Py_JETOS_H\n"
        "#define Py_JETOS_H\n"
        "\n"
        "/* JETOS Language fork identity. */\n"
        f'#define JETOS_LANGUAGE_VERSION "{JETOS_LANGUAGE_VERSION}"\n'
        f'#define JETOS_CPYTHON_VERSION "{UPSTREAM_VERSION}"\n'
        f'#define JETOS_CPYTHON_BASE "{UPSTREAM_COMMIT}"\n'
        "\n"
        "#endif /* Py_JETOS_H */\n"
    )
    if not header.exists() or header.read_text(encoding="utf-8") != header_content:
        header.write_text(header_content, encoding="utf-8")
        changed.append(header)

    sysmodule = source / "Python/sysmodule.c"
    text = sysmodule.read_text(encoding="utf-8")

    if '#include "jetos.h"' not in text:
        needle = '#include "Python.h"\n'
        if needle not in text:
            raise SystemExit("cannot locate Python.h include in Python/sysmodule.c")
        text = text.replace(
            needle,
            needle + '#include "jetos.h"          // JETOS Language identity\n',
            1,
        )

    # Python 3.14.x defines the implementation identity as NAME in sysmodule.c.
    old_impl = '#define NAME "cpython"'
    new_impl = '#define NAME "jetos"'
    if old_impl in text:
        text = text.replace(old_impl, new_impl, 1)
    elif new_impl not in text:
        raise SystemExit("cannot locate CPython implementation name in Python/sysmodule.c")

    version_marker = '    SET_SYS_FROM_STRING("version", Py_GetVersion());'
    jetos_lines = (
        version_marker
        + '\n    SET_SYS_FROM_STRING("jetos_language_version", JETOS_LANGUAGE_VERSION);'
        + '\n    SET_SYS_FROM_STRING("jetos_python_base_version", JETOS_CPYTHON_VERSION);'
    )
    if 'SET_SYS_FROM_STRING("jetos_language_version"' not in text:
        if version_marker not in text:
            raise SystemExit("cannot locate sys.version initialization")
        text = text.replace(version_marker, jetos_lines, 1)

    current = sysmodule.read_text(encoding="utf-8")
    if current != text:
        sysmodule.write_text(text, encoding="utf-8")
        changed.append(sysmodule)

    return changed


def clone_fork(destination: Path, *, upstream: str = UPSTREAM_REPOSITORY) -> None:
    if destination.exists():
        raise SystemExit(f"destination already exists: {destination}")

    run(["git", "clone", "--no-checkout", upstream, str(destination)])
    run(["git", "checkout", "--detach", UPSTREAM_COMMIT], cwd=destination)
    run(["git", "switch", "-c", FORK_BRANCH], cwd=destination)

    changed = patch_source(destination)
    run(
        ["git", "add", *[str(path.relative_to(destination)) for path in changed]],
        cwd=destination,
    )
    run(
        [
            "git",
            "-c", "user.name=JETOS Bootstrap",
            "-c", "user.email=jetos@localhost",
            "commit",
            "-m", f"Start JETOS Language from Python {UPSTREAM_VERSION}",
        ],
        cwd=destination,
    )
    print(f"editable JETOS Language fork: {destination}")
    print(f"stable Python base: {UPSTREAM_VERSION} ({UPSTREAM_COMMIT})")
    print(f"branch: {FORK_BRANCH}")


def source_status(source: Path) -> None:
    require_source_tree(source)
    head = run(["git", "rev-parse", "HEAD"], cwd=source, capture=True).stdout.strip()
    branch = run(
        ["git", "branch", "--show-current"],
        cwd=source,
        capture=True,
    ).stdout.strip()
    text = (source / "Python/sysmodule.c").read_text(encoding="utf-8")
    implementation_is_jetos = '#define NAME "jetos"' in text
    identity_header_exists = (source / "Include/jetos.h").exists()
    print(f"head: {head}")
    print(f"branch: {branch or '(detached)'}")
    print(f"stable Python base: {UPSTREAM_VERSION}")
    print(f"JETOS implementation name: {'yes' if implementation_is_jetos else 'no'}")
    print(f"JETOS identity header: {'yes' if identity_header_exists else 'no'}")


def configure_and_build(
    source: Path,
    build: Path,
    *,
    prefix: Path,
    jobs: int,
    free_threaded: bool,
) -> None:
    require_source_tree(source)
    build.mkdir(parents=True, exist_ok=True)
    configure = source.resolve() / "configure"
    command = [
        str(configure),
        f"--prefix={prefix.resolve()}",
        "--with-ensurepip=no",
    ]
    if free_threaded:
        command.append("--disable-gil")
    run(command, cwd=build)
    run(["make", f"-j{jobs}"], cwd=build)
    print(f"JETOS Language build: {build / 'python'}")


def smoke(build: Path) -> None:
    python = build / "python"
    if not python.exists():
        raise SystemExit(f"built interpreter not found: {python}")
    code = (
        "import sys; "
        "assert sys.implementation.name == 'jetos', sys.implementation; "
        "assert sys.jetos_language_version == '0.2'; "
        f"assert sys.jetos_python_base_version == '{UPSTREAM_VERSION}'; "
        "assert sys.version_info[:3] == (3, 14, 8), sys.version_info; "
        "assert sys.version_info.releaselevel == 'final'; "
        "assert sys.implementation.supports_isolated_interpreters; "
        "from concurrent import interpreters; "
        "i = interpreters.create(); "
        "i.exec('assert 6 * 7 == 42'); "
        "i.close(); "
        "print('implementation:', sys.implementation.name); "
        "print('cache tag:', sys.implementation.cache_tag); "
        "print('language version:', sys.jetos_language_version); "
        "print('stable Python base:', sys.jetos_python_base_version); "
        "print('isolated interpreters: PASS'); "
        "print('runtime:', sys.version)"
    )
    run([str(python), "-c", code])


def install(build: Path) -> None:
    if not (build / "Makefile").exists():
        raise SystemExit(f"configured build tree not found: {build}")
    run(["make", "install"], cwd=build)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JETOS editable CPython-derived language fork"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fork = sub.add_parser(
        "fork",
        help="clone the pinned latest stable CPython and create JETOS Language",
    )
    fork.add_argument("destination", type=Path)
    fork.add_argument("--upstream", default=UPSTREAM_REPOSITORY)

    patch = sub.add_parser(
        "patch",
        help="apply JETOS identity to an existing stable CPython source tree",
    )
    patch.add_argument("source", type=Path)

    status = sub.add_parser("status", help="show JETOS Language source identity")
    status.add_argument("source", type=Path)

    build = sub.add_parser("build", help="configure and compile JETOS Language")
    build.add_argument("source", type=Path)
    build.add_argument("--build", type=Path, default=Path(".build/jetos-language"))
    build.add_argument("--prefix", type=Path, default=Path(".build/jetos-language-install"))
    build.add_argument("--jobs", type=int, default=None)
    build.add_argument(
        "--free-threaded",
        action="store_true",
        help="configure CPython's optional --disable-gil build mode",
    )

    test = sub.add_parser("smoke", help="verify the built interpreter identifies as JETOS")
    test.add_argument("--build", type=Path, default=Path(".build/jetos-language"))

    inst = sub.add_parser("install", help="install the configured JETOS Language build")
    inst.add_argument("--build", type=Path, default=Path(".build/jetos-language"))

    args = parser.parse_args()

    if args.command == "fork":
        clone_fork(args.destination, upstream=args.upstream)
    elif args.command == "patch":
        changed = patch_source(args.source)
        for path in changed:
            print(path)
        if not changed:
            print("JETOS Language patch already applied")
    elif args.command == "status":
        source_status(args.source)
    elif args.command == "build":
        configure_and_build(
            args.source,
            args.build,
            prefix=args.prefix,
            jobs=args.jobs or (os.cpu_count() or 1),
            free_threaded=args.free_threaded,
        )
    elif args.command == "smoke":
        smoke(args.build)
    elif args.command == "install":
        install(args.build)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
