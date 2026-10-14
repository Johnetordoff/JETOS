# JETOS Source Brain

Status: **active Fat-mode architecture contract**

`JETLANG_ARCHITECTURE.md` is the canonical identity/repository rule and supersedes conflicting older wording.

Source Brain is the JETOS-owned Fat-mode source workspace for the native source that defines the JetOS/JetLang runtime boundary:

- `source-brain/linux` — the Linux kernel lineage used to build and improve the JetOS kernel;
- `source-brain/cpython` — the CPython-derived source lineage that is being improved into JetLang;
- `source-brain/shared` — coherent native responsibilities that genuinely belong to both sides of the integrated runtime.

These are not separate products. They are components of one JetOS/JetLang runtime and, after the one-repository migration is complete, ordinary tracked directories in one outer JETOS Git repository.

## JetLang is an improved CPython lineage

JetLang is not unrelated to CPython. JetLang starts from CPython and deliberately improves/diverges from it while keeping Python behavior and the supported standard-library surface as the compatibility contract. An informal mental model is **CPython 2**; the formal project name is **JetLang**.

CPython source, tests, algorithms, and upstream changes therefore remain first-class input to JetLang engineering. JetLang is nevertheless free to replace implementation details, share code with the JetOS kernel, and develop JetLang-native interfaces when those changes are correctly qualified.

## One Git repository

The canonical source-control end state is one checkout and one `.git` at the JETOS repository root. Linux and CPython/JetLang source must not remain Git submodules or nested repositories.

The current bootstrap checkout may still contain temporary gitlinks while the source is being absorbed. Do not remove those gitlinks before copying the pinned source trees into the outer repository. The migration is complete only when:

1. `.gitmodules` is gone;
2. `source-brain/linux` and `source-brain/cpython` are ordinary tracked trees in JETOS;
3. there are no nested `.git` files/directories beneath `source-brain/`;
4. upstream URLs and exact imported commits are retained in repository-owned provenance metadata;
5. build/test tooling no longer depends on `git submodule` or `git -C source-brain/... rev-parse`;
6. the unified checkout passes the relevant qualification gates.

`tools/absorb_source_brain.py` is the bounded migration tool for a native Git checkout with the currently pinned submodules initialized.

## Exact source-to-runtime identity

Every accepted JetOS kernel and JetLang runtime must be reproducible from the exact source state recorded by the outer JETOS revision.

After source absorption the provenance chain is:

```text
JETOS Git revision
    -> ordinary tracked source-brain/linux tree
    -> ordinary tracked source-brain/cpython JetLang lineage
    -> ordinary tracked source-brain/shared tree
    -> recorded upstream provenance/import commits
    -> recorded build configuration/tool inputs
    -> qualified JetOS kernel + JetLang runtime
```

Upstream commit identifiers are provenance, not nested repository identity.

## Fat and Skinny split

**Fat Mode owns source. Skinny Mode owns qualified runtime artifacts.**

Fat Mode contains, as needed:

- complete Linux source;
- complete CPython-derived JetLang source;
- shared JetOS/JetLang native source;
- compilers, linkers, headers and build tools;
- exhaustive repository, language, kernel, integration, architecture and hardware qualification tests;
- benchmarks, tracing, diagnostics and comparison manifests;
- provenance needed to prove which source produced which artifact.

Skinny Mode must not contain the complete Linux source tree, the complete JetLang development source tree, compiler/build bulk, or the Fat development test suite. It contains completed qualified runtime artifacts and only operational data needed by that target.

## Linux and JetLang are co-designed

JETOS deliberately controls both sides of the boundary. Source Brain work may modify Linux and the CPython-derived JetLang implementation together when doing so produces a simpler, faster or safer Python-facing system.

Examples include reducing syscall choreography, adding narrow kernel primitives that match Python standard-library operations, improving process construction, file-copy semantics, directory walking, event waiting, shared-memory lifetime and temporary-object creation.

The governing rule remains:

> Python semantics are the compatibility contract. Optimization may change the implementation path, not silently reduce behavior.

## Source Brain Weaver

The Source Brain Weaver continuously examines the Linux, JetLang and shared trees as one integrated system. It should:

1. find duplicated, expensive or awkward responsibilities across the boundary;
2. propose the smallest reviewable shared or coordinated change;
3. preserve architecture-neutral behavior wherever practical;
4. isolate x86-64, ARMv7 and ARM64 details at genuine machine boundaries;
5. measure before/after behavior;
6. retain compatibility/fallback behavior until a JetOS-native path is proven;
7. reject semantic reductions made solely for benchmark or LOC wins;
8. preserve source/build provenance.

## Qualification standard

Source Brain changes require operating-system-level qualification, including as applicable:

- JETOS repository unit and integration tests;
- CPython regression tests as a JetLang compatibility corpus;
- JetLang-native tests;
- Linux kernel build/self-tests for changed subsystems;
- boot and repeated boot/reboot tests;
- syscall/API semantic comparison tests;
- filesystem, process, networking, memory, IPC, signal, timer, device and error-path tests;
- sanitizer/static-analysis and useful fuzz/property tests;
- performance/regression benchmarks when performance is claimed;
- x86-64, ARMv7 and ARM64 builds/tests;
- QEMU/emulated qualification where useful;
- ODROID-HC1 physical qualification for relevant ARMv7 work;
- reproducibility checks proving the outer JETOS revision produces the expected artifacts.

## Upstream relationship

JetLang remains an improved CPython lineage and should continue to ingest useful upstream CPython changes deliberately. JetOS may likewise ingest useful Linux changes. Upstream updates must never blindly overwrite JetOS/JetLang work.

Gentoo remains advisory source/build/configuration intelligence, not JetOS's identity. Relevant Gentoo knowledge may be imported when useful and must pass JetOS qualification.
