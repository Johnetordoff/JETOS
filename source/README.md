# JetOS source

`source/` is the canonical home for external/native source lineages and dependency source used to build or qualify JetOS.

Current layout:

- `source/linux/` — Linux lineage used for the JetOS kernel;
- `source/cpython/` — CPython-derived JetLang lineage;
- `source/shared/` — native source deliberately shared across the integrated JetOS/JetLang runtime;
- `source/ports/` — ported or adapted dependency/native source kept under JetOS source control.

Additional dependency source belongs under this directory rather than in new root-level source buckets.

Upstream repositories remain provenance and update sources. Record exact URLs, commits/tags, licenses, and imported-version metadata. The long-term target is one outer JETOS repository with ordinary tracked source directories and no nested Git metadata; current gitlinks are transitional until the pinned working trees are safely absorbed.
