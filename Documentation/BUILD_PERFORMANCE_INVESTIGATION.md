# JetOS build-performance investigation

Status: current finding; behavior change intentionally deferred unless separately approved.

## Finding

The current Fat development path is intentionally clean-revision oriented rather than incremental across ordinary Git commits.

`tools/dev.py::prepare_revision_build()` compares the current JetOS Git revision with `.build/.jetos-build-revision`. Whenever the revision differs, it calls `clear_build_directory()`, which removes every child under `.build`, including the prepared Linux tree, compiled kernel image, JetLang build/install trees, rootfs, and qualification artifacts.

That means a normal repository commit invalidates the whole build workspace even when the Linux source lineage itself did not change.

The Docker development path compounds this. `jetos.py dev` runs the development image with `docker run --rm` and bind-mounts the repository at `/jetos`. The image declares `/jetos/.build` as a Docker volume. The resulting build storage is deliberately Docker-native rather than the macOS bind mount, but the current command does not name a persistent build volume. Therefore a normal development-container lifecycle does not provide a durable cross-run build tree that JetOS can rely on.

## Consequence

A clean Linux build after an unrelated JetOS revision change is expected under the current implementation. This is why small project changes can still produce a large ARM64 compile.

## Deferred proposals

The owner explicitly deferred both of these ideas for separate consideration:

1. preserving the complete build tree across runs/revisions and relying on Make dependency tracking;
2. splitting ordinary fast tests from the authoritative full qualification path.

This investigation does **not** implement either proposal.

## Approved low-risk acceleration direction

Independent caches may be added when their correctness can be established by complete input fingerprinting and conservative invalidation. Reusing a final kernel artifact is acceptable only when every kernel-relevant input represented by the cache key is identical; otherwise JetOS must rebuild it.

Kernel-configuration reduction must be incremental and conservative. A reduction is not considered qualified merely because the kernel compiles: the newly built kernel must pass the integrated JetLang/standard-library qualification required by `MANDATE.md` before the reduction can be treated as proven.
