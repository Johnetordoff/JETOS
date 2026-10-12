# JETOS Fat Development / Skinny HC1 Runtime

Status: **active architecture rule**

## Core rule

JETOS is developed and qualified in a **Fat Mode** environment, but the ODROID-HC1 is flashed with a deliberately minimized **Skinny Mode** runtime image.

**Fat Mode is the workshop. Skinny Mode is the product.**

The purpose of Fat Mode is to make JETOS easy to build, inspect, test, instrument, debug, compare, co-design, and reduce. The purpose of Skinny Mode is to preserve the maximum useful Python capability surface with the minimum kernel/userspace/runtime material required to support it on the target.

The canonical native source workspace is `source-brain/`. Fat Mode owns the complete Linux and CPython source lineages used to produce the qualified runtime. Skinny Mode does not carry those complete source trees.

## Fat Mode

Fat Mode may include development-only material such as:

- the complete Source Brain Linux source tree;
- the complete Source Brain CPython source tree;
- JETOS modifications that co-design the kernel and CPython together;
- compilers, linkers, headers, build tools, diagnostics, tracing, debuggers, profilers, sanitizers, fuzzers and static-analysis tools;
- broad kernel configuration used to establish a capability baseline;
- exhaustive repository, CPython, kernel, integration, architecture, emulation and physical-hardware tests;
- extensive test fixtures and qualification tooling;
- image-generation and flashing tools;
- benchmark and comparison manifests for optimization/reduction experiments;
- exact source/configuration provenance for every promoted kernel and runtime artifact.

Fat Mode is not the target footprint for the HC1 or another production device.

## Skinny Mode

The flashed HC1 image should contain only what the qualified runtime needs, including:

- the completed qualified JETOS-maintained HC1/ARMv7 Linux kernel;
- the HC1 device tree and required boot files;
- the completed target-native JETOS Python runtime derived from the qualified Source Brain CPython revision;
- the supported Python standard library and required native extension/shared-library runtime dependencies;
- JETOS early userspace/control logic;
- storage/filesystem support needed by the target;
- Ethernet, IP, routing, DHCP/DNS, and authorized remote administration support;
- safe SATA discovery support;
- required firmware, certificate roots, logging/recovery pieces, and other capabilities that survive qualification;
- compact provenance sufficient to identify the exact Fat source/build revision that produced the image.

Skinny Mode must **not** contain:

- the complete Linux source tree;
- the CPython source tree;
- Source Brain development worktrees;
- development-only compilers, linkers, headers or package/build machinery;
- Fat-mode test fixtures, regression suites, fuzz corpora, benchmark harnesses or build diagnostics merely because they were used to qualify the image.

A runtime self-check may remain only when it is itself part of safe normal operation. The development test suite belongs to Fat Mode.

## Python-first reduction gate

Skinny Mode is not allowed to become smaller by silently reducing Python.

The reduction process is:

1. build a broad/fat target-capable kernel and target-native JETOS Python runtime from the exact Source Brain revisions recorded by the JETOS revision;
2. run the full JETOS standard-library, CPython, kernel and Python↔OS qualification suite;
3. record the passing behavior and source/build provenance as the baseline;
4. remove one Linux kernel/userspace/runtime capability family at a time from the candidate Skinny image;
5. rebuild and boot the candidate image;
6. rerun the applicable qualification suite against that candidate on emulated and/or physical target hardware;
7. keep the reduction only when the required Python-visible capability surface and target responsibilities remain intact;
8. restore the removed substrate when the reduction causes a required capability to regress.

Therefore the optimization target is:

> **the smallest target runtime that preserves the complete qualified JETOS Python capability surface and required hardware responsibilities.**

## Kernel and language ownership

The Skinny kernel is a **JETOS-maintained Linux-derived kernel build**, not a clean-room replacement kernel. JETOS owns the selected source revision, target configuration, JETOS patches, build rules, capability rationale, and qualification evidence.

The Skinny Python runtime is likewise the completed result of the qualified JETOS CPython source lineage. Linux and CPython may be modified together in Source Brain where a coordinated change produces a simpler, faster or safer Python-facing operating system.

For both components, the source revision represented by the Fat JETOS commit must be the source used to produce the promoted artifact. No promoted kernel or interpreter may come from an unrecorded working tree.

## Source retention versus runtime footprint

Complete Linux and CPython source are **Fat-only development material**. They may exist on build servers, protected source repositories, development disks and archival/recovery systems, but they are intentionally removed from the Skinny runtime image.

The Skinny image retains the completed kernel/runtime plus compact provenance identifying their exact source/build lineage. Reconstructing or modifying the kernel or language is a Fat-mode operation.

## Testing boundary

Fat Mode should be aggressively over-tested. The qualification suite may be large, slow and redundant when that increases confidence across subsystem, instruction-set, emulation and physical-hardware boundaries.

Skinny production images do not carry that development suite. Their job is to run the already-qualified result. Any tests retained in Skinny must have a specific operational health/safety responsibility rather than being retained as development bulk.

## Flashing model

The normal physical workflow is:

**Fat development/Source Brain environment → build + exhaustive qualify → construct Skinny target image → verify source/artifact provenance → flash dedicated media → boot target → target qualification → promote or iterate.**

The attached HC1 SATA disk is not a build scratch disk and must not be formatted or modified during bring-up without explicit authorization.

See `source-brain/README.md` for the Linux↔CPython co-design and Source Brain Weaver contract.
