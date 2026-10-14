# JetOS shared Langkernel source

`source-brain/shared/` is the first explicitly shared source area for code used by both of JetOS's native source lineages:

- `source-brain/linux/` — the kernel lineage used to build the JetOS kernel;
- `source-brain/cpython/` — the CPython-derived lineage used to build JetLang.

These are not separate products. They are source components of one JetOS/JetLang runtime.

## Purpose

Move code here only when Linux-side and JetLang-side responsibilities genuinely share the same implementation or contract. The first objective is small, reviewable deduplication: identify duplicated or semantically equivalent native helpers, extract one coherent implementation, have both sides consume it, and prove that the complete integrated runtime still builds and behaves correctly.

Do not use this directory as a miscellaneous `utils` bucket. Shared modules must have a clear responsibility and ownership boundary.

## Required acceptance path for runtime changes

A native consolidation is not considered qualified merely because an isolated unit test passes or because the old upstream kernel/interpreter still builds. For any change that affects the integrated runtime, the target qualification path is:

1. modify the JetOS-owned source;
2. build the resulting **new JetOS kernel** from the current recorded Linux lineage plus JetOS changes;
3. build the resulting **new JetLang interpreter/runtime** from the current recorded CPython-derived lineage plus JetOS changes;
4. launch that newly built JetLang interpreter on/with the newly built JetOS runtime where the available environment supports it;
5. run the relevant JetLang/CPython-derived regression tests through the newly built interpreter;
6. run JetOS native and same-runtime integration tests;
7. exercise representative real runtime behavior, including networking; where practical, launch a small web server and verify that a browser/client can reach it;
8. record exact source revisions, build configuration, results, and blockers.

Testing only the old upstream Linux kernel, an old/prebuilt interpreter, or two isolated source trees does not satisfy the integrated-runtime qualification goal.

## Metrics must not block engineering

Source inventory, total bytes, file-type enumeration, full file-tree capture, and LOC accounting are required engineering measurements, but incomplete global metrics must never stop useful source work. If a total inventory is temporarily unavailable, document the reason, measure the changed files/PR delta accurately, continue with bounded engineering, and keep the full inventory work as a separate tracked task.

Do not make one GitHub API request per source file merely to build an inventory. Prefer local checkout traversal, Git-native recursive listings, recursive tree APIs, or other batched mechanisms. Once the full Linux and CPython-derived source trees are locally available, LOC and file-type accounting should be deterministic and repeatable.

## Convergence direction

The current physical layout remains:

```text
source-brain/
  linux/
  cpython/
  shared/
```

The long-term goal is increasing shared ownership where it genuinely simplifies JetOS. Code may move from the Linux or CPython-derived lineages into `shared/` only in small, testable steps. The final architecture may eventually converge further, but directory movement is not itself the objective: a smaller, clearer, integrated JetOS/JetLang runtime is.
