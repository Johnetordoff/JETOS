# JETOS Source Brain

Status: **active Fat-mode architecture contract**

Source Brain is the JETOS-owned Fat-mode source workspace for the two large native codebases that define the Gen 2 Python/kernel boundary:

- `source-brain/linux` — the Linux kernel source lineage used to build the JETOS kernel;
- `source-brain/cpython` — the CPython source lineage used to build the JETOS language/runtime.

These are not ordinary opaque vendor dependencies. JETOS treats them as coupled source material that can be deliberately modified together to improve Python-visible operating-system behavior while preserving compatibility and correctness.

## Exact source-to-runtime identity

Every JETOS kernel or CPython runtime accepted for a Fat build must be reproducible from the exact Source Brain revisions recorded by that JETOS Git revision.

The source revision used to build an artifact and the artifact's reported/build provenance must agree. A JETOS commit must never silently build a kernel or interpreter from an unrecorded working tree.

Published or promoted build artifacts therefore have a traceable chain:

```text
JETOS Git revision
    -> exact Source Brain Linux revision
    -> exact Source Brain CPython revision
    -> recorded build configuration/tool inputs
    -> qualified kernel + JETOS Python runtime
```

The Source Brain revisions are part of the Fat source graph. Updating them is a source-governance change, not an incidental package refresh.

## Fat and Skinny split

**Fat Mode owns source. Skinny Mode owns qualified runtime artifacts.**

Fat Mode contains, as needed:

- complete Linux source;
- complete CPython source;
- JETOS modifications to either tree;
- compilers, linkers, headers and build tools;
- exhaustive repository, language, kernel, integration, architecture and hardware qualification tests;
- benchmarks, tracing, diagnostics and comparison manifests;
- provenance needed to prove which source produced which artifact.

Skinny Mode must not contain the complete Linux source tree, the CPython source tree, Source Brain development worktrees, compiler/build bulk, or the Fat development test suite. It contains the completed qualified kernel, target-native JETOS Python runtime and standard library, required native runtime dependencies, boot/device material, JETOS runtime control logic, and only the operational data needed for that target.

Tests are a Fat responsibility. Skinny production images may contain runtime self-checks that are genuinely required for safe operation, but they do not carry the development/qualification suite merely because it existed during construction.

## Linux and CPython are co-designed

JETOS deliberately controls both sides of the boundary. Source Brain work may therefore modify Linux and CPython together when doing so produces a simpler, faster or safer Python-facing operating system.

Examples include reducing syscall choreography, adding narrow kernel primitives that match Python standard-library operations, improving process construction, file-copy semantics, directory walking, event waiting, shared-memory lifetime and temporary-object creation.

The governing rule remains:

> Python semantics are the contract. Optimization may change the implementation path, not silently reduce Python behavior.

A change is accepted only when its normal Linux/Python fallback or compatibility behavior is understood and the protected qualification surface remains intact.

## Source Brain Weaver

JETOS assigns a dedicated **Source Brain Weaver** responsibility to continuously examine the Linux and CPython trees as one coupled system.

The Weaver's job is to:

1. find expensive, duplicated or awkward transitions between CPython and Linux;
2. propose the smallest reviewable change on the correct side of the boundary, or coordinated changes on both sides;
3. preserve architecture-neutral JETOS behavior wherever possible;
4. isolate x86-64, ARMv7 and ARM64 implementation details at genuine machine boundaries;
5. measure before/after behavior rather than accepting optimization by intuition;
6. retain normal compatibility/fallback paths until a JETOS-native path is proven;
7. reject changes that weaken language semantics merely to improve a benchmark;
8. produce enough provenance that every accepted binary can be traced back to its exact source revisions.

The ordinary bounded Work Server improver is not automatically authorized to mutate Source Brain. Source Brain modifications require the stronger Source Brain qualification path because a mistake can cross the language/kernel boundary.

## Qualification standard

Source Brain changes are held to operating-system-level qualification, not a small unit-test gate. The Fat suite should grow toward the broadest practical combination of:

- JETOS repository unit and integration tests;
- CPython regression tests and standard-library surface inventories;
- Linux kernel build/self-tests that apply to the changed subsystem;
- boot tests and repeated boot/reboot tests;
- syscall/API semantic comparison tests;
- filesystem, process, networking, memory, IPC, signal, timer, device and error-path tests;
- sanitizer/static-analysis runs where applicable;
- fuzz/property tests where they meaningfully exercise parsers, interfaces or binary boundaries;
- performance and regression benchmarks;
- architecture-specific x86-64, ARMv7 and ARM64 builds/tests;
- QEMU/emulated qualification where useful;
- physical-board qualification for hardware-specific work, with the ODROID-HC1 as the current ARMv7 reference target;
- negative/failure-injection tests, interrupted-operation tests, resource exhaustion and recovery tests;
- reproducibility checks proving the recorded source/configuration produces the expected artifacts.

A passing Skinny image is the product of this Fat qualification. The Skinny image does not need to carry the qualification machinery itself.

## Upstream relationship

JETOS is free to diverge from upstream Linux and CPython where Python/kernel co-design requires it. Upstream remains valuable for security fixes, hardware support, architecture work and broadly useful correctness improvements.

Gentoo is advisory source/build intelligence, not the identity of JETOS and not a requirement that JETOS mirror every Gentoo version change. Relevant Gentoo kernel configuration, patch, hardware-driver or build knowledge may be evaluated and imported when it improves JETOS. Changes are accepted because they are useful and pass JETOS qualification, not merely because Gentoo carries them.

Upstream intake must never overwrite a JETOS Source Brain change blindly. Rebase/merge decisions must preserve provenance and rerun the appropriate Fat qualification gates.

## Current bootstrap note

The present Source Brain entries begin from pinned upstream Linux and CPython revisions. Moving from upstream seed revisions to long-lived JETOS-owned fork revisions is an explicit next source-governance step. The architecture in this document applies to those JETOS-owned revisions: once JETOS carries a native source modification, the recorded Source Brain commit must be the source of the built artifact.
