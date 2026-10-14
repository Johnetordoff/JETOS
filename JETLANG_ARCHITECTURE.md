# JetLang architecture and repository identity

Status: **canonical current architecture**

This file supersedes older wording anywhere in the repository that conflicts with it.

## JetLang identity

JetLang is the JetOS language/runtime. It is an improved, deliberately diverging descendant of CPython.

A useful informal mental model is **"CPython 2"**: start from CPython, preserve Python language and standard-library semantics as the compatibility contract, then improve the implementation as JetOS and JetLang co-design make better approaches possible. The formal project name is **JetLang**.

Therefore:

- Do not describe JetLang as unrelated to CPython.
- Do not describe JetLang as merely stock CPython under another name.
- CPython is JetLang's source lineage and compatibility foundation.
- JetLang may modify, replace, consolidate, or remove CPython implementation details when the resulting behavior remains correct under the JetLang/JetOS contract.
- CPython regression tests are a primary compatibility corpus for JetLang, supplemented by JetLang-native and JetOS same-runtime tests.

## JetOS and Linux/Gentoo

JetOS is the system being developed. The Linux source lineage is controlled source material used to build and improve the JetOS kernel/runtime boundary. Gentoo is valuable source/build/configuration intelligence; it is not JetOS's identity.

The Linux-side and CPython-derived JetLang-side C responsibilities are components of one integrated JetOS/JetLang runtime, not independent products.

## One Git repository

The canonical source-control architecture is **one outer JETOS Git repository**.

The repository must contain ordinary tracked source trees for:

```text
source-brain/
  linux/
  cpython/    # CPython-derived JetLang source lineage
  shared/
```

There must be no Git submodules for these trees and no nested Git repositories or nested `.git` files/directories beneath them.

Upstream Git repositories remain provenance and update sources only. Their commit IDs, URLs, licenses, and imported-version metadata must be recorded as data inside the outer JETOS repository. Upstream repository metadata is not part of the working JetOS source tree.

The desired invariant is:

> One checkout, one `.git`, one auditable JetOS/JetLang source graph.

## Migration rule

Until the current Linux and CPython gitlinks have been safely absorbed as ordinary tracked files, do **not** simply delete the gitlinks or `.gitmodules`; doing so would discard the source rather than unify it.

The migration must:

1. verify the currently pinned Linux and CPython revisions;
2. snapshot their working trees while excluding nested `.git` metadata;
3. replace both gitlinks with ordinary tracked directories in the outer repository;
4. remove `.gitmodules`;
5. remove leftover nested submodule Git metadata from the outer `.git/modules` area;
6. record exact upstream URLs and source commit IDs in repository-owned provenance metadata;
7. verify that no nested `.git` exists below `source-brain/`;
8. update build/test tooling so it reads provenance from the outer repository rather than running `git -C source-brain/...`;
9. run repository, CPython/JetLang, kernel, and same-runtime integration qualification before calling the migration complete.

## Governing engineering direction

Current optimization work should make JetLang and the JetOS kernel smaller, cleaner, more shared, and better tested. Deduplication and shared runtime code are encouraged where responsibilities are genuinely identical. Source-size reduction must come from real simplification, not metric tricks.
