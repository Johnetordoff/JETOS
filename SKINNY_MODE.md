# JETOS Fat Development / Skinny HC1 Runtime

Status: **active architecture rule**

JETOS is developed and qualified in a **Fat Mode** environment, while the ODROID-HC1 is flashed with a deliberately minimized **Skinny Mode** runtime image. **Fat Mode is the workshop. Skinny Mode is the product.**

The canonical native/dependency source workspace is `source/`. Fat Mode owns the complete Linux and CPython-derived JetLang source lineages used to produce the qualified runtime. Skinny Mode does not carry those complete source trees.

## Fat Mode

Fat Mode may contain complete `source/linux` and `source/cpython` trees, shared/ported dependency source, compilers/linkers/headers, diagnostics, broad kernel configuration, exhaustive regression/integration/architecture/hardware tests, build and image tools, benchmarks, exact provenance, and temporary development/accounting material.

Fat Mode is not the production footprint.

## Skinny Mode

A Skinny HC1 image contains only the qualified runtime responsibilities: the JETOS-maintained ARMv7 Linux kernel and device tree/boot files, target-native JetLang runtime, supported Python standard library and native runtime dependencies, early userspace/control logic, required storage/network/SATA/firmware/security/recovery capabilities, and compact provenance identifying the exact Fat source/build revision.

Skinny Mode must **not** contain complete Linux or CPython source trees, `source/` development worktrees, `Temporary Bullshit/` or its generated reports, development compilers/build machinery, or Fat-only regression/fuzz/benchmark/diagnostic material merely because it was used for qualification.

`tools/package.py` explicitly removes temporary development material from a candidate Skinny rootfs. Runtime self-checks remain only when they have a real operational responsibility.

## Python-first reduction gate

Skinny Mode must not become smaller by silently reducing Python/JetLang behavior. Start from the exact recorded source, establish a passing Fat baseline, remove substrate capabilities incrementally, rebuild/boot, rerun applicable qualification, retain only reductions that preserve the required Python-visible surface and device responsibilities, and restore substrate when required behavior regresses.

The optimization target is **the smallest target runtime that preserves the complete qualified JETOS Python capability surface and required hardware responsibilities.**

## Kernel and language ownership

The Skinny kernel is a JETOS-maintained Linux-derived build. JetOS owns the selected revision, target configuration, patches, build rules, capability rationale, and qualification evidence. JetLang is likewise built from the controlled CPython-derived source lineage. Coordinated Linux/JetLang changes are permitted when they produce a simpler, faster, or safer integrated runtime, but runtime-affecting changes must satisfy the integrated qualification in `MANDATE.md` and `ARCHITECTURE.md`.

No promoted kernel or interpreter may come from an unrecorded working tree.

## Source retention versus runtime footprint

Complete development source is Fat-only material. It may exist on build servers, protected source repositories, development disks, and recovery systems, while the Skinny image keeps the completed runtime plus compact provenance sufficient to reproduce it.

## Testing and flashing boundary

Fat Mode should be aggressively tested. Skinny images run the already-qualified result and do not carry the development suite without a specific runtime responsibility.

The physical workflow is:

**Fat source/development environment → build + exhaustive qualification → construct Skinny target image → verify provenance → flash dedicated media → boot target → target qualification → promote or iterate.**

The attached HC1 SATA disk is not build scratch space and must not be formatted or modified during bring-up without explicit authorization.
