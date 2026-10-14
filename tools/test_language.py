#!/usr/bin/env python3
"""Tests for the JETOS language-fork source transformation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "jetos_language_tool",
    ROOT / "tools/language.py",
)
assert SPEC and SPEC.loader
language = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(language)

# Matches the pinned CPython 3.14.8 sys.implementation layout.
UPSTREAM_SYSMODULE_314_FIXTURE = """\
#include "Python.h"

/* sys.implementation values */
#define NAME "cpython"
const char *_PySys_ImplName = NAME;
#define MAJOR Py_STRINGIFY(PY_MAJOR_VERSION)
#define MINOR Py_STRINGIFY(PY_MINOR_VERSION)
#define TAG NAME "-" MAJOR MINOR

static int init_sys(void)
{
    SET_SYS_FROM_STRING("version", Py_GetVersion());
    return 0;
}
"""

# Newer CPython source uses _PY_IMPL_NAME. Keep that layout supported too.
UPSTREAM_SYSMODULE_MODERN_FIXTURE = """\
#include "Python.h"

/* sys.implementation values */
#ifndef _PY_IMPL_NAME
#define _PY_IMPL_NAME "cpython"
#endif

static int init_sys(void)
{
    SET_SYS_FROM_STRING("version", Py_GetVersion());
    return 0;
}
"""

UPSTREAM_PATCHLEVEL_FIXTURE = """\
#define PY_MAJOR_VERSION 3
#define PY_MINOR_VERSION 14
#define PY_VERSION "3.14.8"
"""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_source(root: Path, sysmodule_text: str) -> None:
    (root / "Python").mkdir()
    (root / "Include").mkdir()
    (root / "Python/sysmodule.c").write_text(sysmodule_text, encoding="utf-8")
    (root / "Include/patchlevel.h").write_text(
        UPSTREAM_PATCHLEVEL_FIXTURE,
        encoding="utf-8",
    )
    (root / "configure").write_text("#!/bin/sh\n", encoding="utf-8")


def main() -> int:
    checks = 0

    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)
        make_source(source, UPSTREAM_SYSMODULE_314_FIXTURE)

        changed = language.patch_source(source)
        check(len(changed) == 2, "expected header + sysmodule changes")
        checks += 1

        header = (source / "Include/jetos.h").read_text(encoding="utf-8")
        sysmodule = (source / "Python/sysmodule.c").read_text(encoding="utf-8")

        check(
            f'#define JETOS_LANGUAGE_VERSION "{language.JETOS_LANGUAGE_VERSION}"'
            in header,
            "language version missing",
        )
        check(
            f'#define JETOS_CPYTHON_BASE "{language.UPSTREAM_COMMIT}"' in header,
            "upstream base missing",
        )
        check(
            f'#define JETOS_CPYTHON_VERSION "{language.UPSTREAM_VERSION}"' in header,
            "upstream Python version missing",
        )
        check(language.UPSTREAM_VERSION == "3.14.8", "Python base must remain 3.14.8")
        check('#include "jetos.h"' in sysmodule, "JETOS header not included")
        check('#define NAME "jetos"' in sysmodule, "3.14 implementation not renamed")
        check('const char *_PySys_ImplName = NAME;' in sysmodule, "implementation binding changed unexpectedly")
        check('#define TAG NAME "-" MAJOR MINOR' in sysmodule, "cache-tag identity no longer follows NAME")
        check(
            'SET_SYS_FROM_STRING("jetos_language_version", JETOS_LANGUAGE_VERSION);'
            in sysmodule,
            "sys.jetos_language_version not installed",
        )
        check(language.implementation_is_jetos(sysmodule), "3.14 JetLang identity not recognized")
        checks += 10

        changed_again = language.patch_source(source)
        check(changed_again == [], "3.14 patch is not idempotent")
        check(sysmodule.count('#define NAME "jetos"') == 1, "duplicate 3.14 implementation identity")
        check(sysmodule.count("jetos_language_version") == 1, "duplicate JETOS sys field")
        checks += 3

    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)
        make_source(source, UPSTREAM_SYSMODULE_MODERN_FIXTURE)
        changed = language.patch_source(source)
        modern = (source / "Python/sysmodule.c").read_text(encoding="utf-8")
        check(len(changed) == 2, "modern layout expected header + sysmodule changes")
        check('#define _PY_IMPL_NAME "jetos"' in modern, "modern implementation not renamed")
        check(language.implementation_is_jetos(modern), "modern JetLang identity not recognized")
        check(language.patch_source(source) == [], "modern patch is not idempotent")
        checks += 4

    print(f"JETOS language fork tooling: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
