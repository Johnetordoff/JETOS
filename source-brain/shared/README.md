# JetOS shared Langkernel source

`source-brain/shared/` is the explicitly shared source area for code used by both sides of the integrated JetOS/JetLang runtime:

- `source-brain/linux/` — the kernel lineage used to build the JetOS kernel;
- `source-brain/cpython/` — the CPython-derived lineage being improved into JetLang.

JetLang is an improved CPython descendant; **CPython 2** is a useful informal mental model, while **JetLang** is the formal project name. These trees are not separate products.

`JETLANG_ARCHITECTURE.md` is canonical for language identity and the one-repository rule.

## Repository boundary

The target source-control layout is one outer JETOS repository containing ordinary tracked `linux/`, `cpython/`, and `shared/` trees. No Source Brain tree should remain a Git submodule or nested Git repository after migration. Upstream Git URLs and commit IDs are provenance, not nested repository ownership.

During the temporary bootstrap transition, do not delete a gitlink until its pinned working tree has been absorbed as ordinary outer-repository content. `tools/absorb_source_brain.py` performs that native-Git migration.

## Purpose

Move code here only when Linux-side and JetLang-side responsibilities genuinely share the same implementation or contract. The first objective is small, reviewable deduplication: identify duplicated or semantically equivalent native helpers, extract one coherent implementation, have both sides consume it, and prove that the complete integrated runtime still builds and behaves correctly.

Do not use this directory as a miscellaneous `utils` bucket. Shared modules must have a clear responsibility and ownership boundary.

## Required acceptance path for runtime changes

A native consolidation is not considered qualified merely because an isolated unit test passes or because old upstream components still build. For changes affecting the integrated runtime, the target qualification path is:

1. modify the JetOS-owned source;
2. build the resulting **new JetOS kernel** from the tracked Linux lineage plus JetOS changes;
3. build the resulting **new JetLang interpreter/runtime** from the tracked CPython-derived lineage plus JetLang changes;
4. launch that newly built JetLang runtime on/with the newly built JetOS runtime where the environment supports it;
5. run relevant CPython-derived regression tests as a JetLang compatibility corpus;
6. run JetLang-native, JetOS-native and same-runtime integration tests;
7. exercise representative runtime behavior, including networking where practical;
8. record exact outer-repository revision, upstream provenance, build configuration, results and blockers.

Testing only upstream Linux, stock/prebuilt CPython, or isolated source trees does not satisfy the integrated-runtime qualification goal.

## Metrics must not block engineering

Source inventory, bytes, file-type enumeration, tree capture and LOC accounting are required engineering measurements, but incomplete global metrics must never stop useful source work. If a total inventory is temporarily unavailable, document why, measure changed files accurately, continue bounded engineering, and keep full inventory work separately tracked.

Prefer local checkout traversal, Git-native listings or batched recursive APIs over one remote request per source file. Once the source trees are ordinary tracked content in the unified checkout, inventory and LOC accounting should be deterministic and repeatable.

## Convergence direction

The canonical physical layout is:

```text
source-brain/
  linux/
  cpython/   # CPython-derived JetLang lineage
  shared/
```

All three directories belong to the same outer Git repository. The goal is increasing shared ownership where it genuinely simplifies JetOS/JetLang—not directory movement for its own sake.
