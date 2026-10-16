# JetOS source

`source/` is the canonical home of the source used to build JetOS.

Current layout:

- `source/linux/` — JetOS-owned Linux kernel lineage;
- `source/cpython/` — CPython-derived JetLang lineage;
- `source/shared/` — native source deliberately shared across the integrated JetOS/JetLang runtime;
- `source/ports/` — ported or adapted dependency/native source kept under JetOS source control.

JetOS is its own source-built Linux distribution. Gentoo, Debian, and other Linux distributions are not canonical build or runtime bases.

The target repository state is one outer JETOS repository with ordinary tracked source directories and no nested Git metadata. The current Linux and CPython gitlinks are transitional provenance/bootstrap mechanisms only until their exact pinned working trees are absorbed. After absorption, those trees are JetOS-owned source and are changed deliberately inside JetOS rather than automatically tracking upstream releases.

Upstream repositories remain provenance and reference sources. Record exact URLs, commits/tags, licenses, and imported-version metadata. Upstream movement alone does not replace the vendored JetOS trees.

Additional dependency source belongs under this directory rather than in new root-level source buckets.
