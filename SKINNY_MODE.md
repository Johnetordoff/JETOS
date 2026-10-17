# JETOS Fat Development / Transition / Skinny Production

Status: **active architecture rule**

JETOS recognizes one source estate and one operating system, but it deliberately moves through **three operational environments** on the way from active development to a finished target image:

1. **Fat Development Environment** — the full workshop;
2. **Transition Environment** — a compact, target-specific pre-runtime used to prove that the production projection still works after development bulk is removed;
3. **Skinny Production Environment** — the final target runtime.

This is not three different JetOS products. It is one controlled reduction pipeline. The transition environment exists because the development environment is intentionally much larger and more instrumented than the final production image, and JetOS does not want to jump directly from an enormous workshop to a minimal production image without testing the reduction boundary.

The canonical native/dependency source workspace is `source/`. Fat Mode owns the complete Linux and CPython-derived JetLang source lineages used to produce the qualified runtime. Transition and Skinny production images do not carry those complete source trees unless a target responsibility explicitly requires them.

## 1. Fat Development Environment

Fat is the **authoritative workshop and qualification environment**.

It may contain complete `source/linux` and `source/cpython` trees, shared/ported dependency source, compilers/linkers/headers, diagnostics, broad kernel configuration, exhaustive regression/integration/architecture/hardware tests, build and image tools, benchmarks, source inventory, exact provenance, temporary development material, debugging tools, and other instrumentation needed to understand or repair JetOS.

Fat is where JetOS is changed. Runtime-affecting work is not considered qualified merely because it compiles there; the newly built kernel and newly built JetLang must run together and pass the required integrated qualification.

Fat is **not** the production footprint and must not be used as an excuse to ship development bulk.

## 2. Transition Environment

The Transition Environment is the **pre-runtime reduction gate** between Fat and production.

It is deliberately smaller than Fat but may still retain limited qualification, inspection, recovery, and comparison machinery that is not intended to remain in the final production image. Its purpose is to answer one question:

> After removing the workshop, do the exact kernel, JetLang runtime, standard library, native runtime dependencies, target configuration, and required device capabilities still behave correctly as a coherent target system?

A Transition image should normally contain:

- the exact candidate production kernel, device tree/boot files, and target configuration;
- the exact candidate JetLang runtime and supported standard library;
- the exact native runtime libraries and firmware required by that target;
- early userspace/control logic;
- compact provenance and build identity;
- target-specific networking/storage/security/recovery pieces needed for qualification;
- a **small, intentional qualification/diagnostic layer** sufficient to prove the production projection before promotion.

A Transition image should normally omit:

- complete Linux and CPython/JetLang source worktrees;
- compilers, linkers, headers, and general build toolchains unless the target explicitly needs self-hosted development;
- broad fuzzing/benchmark suites;
- source inventories and temporary development reports;
- unrelated developer utilities;
- host/container bootstrap machinery.

The Transition Environment is allowed to be somewhat larger than final production because its job is to prove the reduction safely. It should nevertheless be much closer to the production filesystem, dependency graph, kernel configuration, and runtime behavior than to Fat.

## 3. Skinny Production Environment

Skinny is the **promoted production runtime**.

A Skinny target contains only runtime responsibilities that have survived Fat qualification and Transition qualification. For the HC1, that means the JETOS-maintained ARMv7 Linux kernel and device tree/boot files, target-native JetLang runtime, supported Python standard library and native runtime dependencies, early userspace/control logic, required storage/network/SATA/firmware/security/recovery capabilities, and compact provenance identifying the exact source/build revision from which it was produced.

Skinny must **not** contain complete Linux or CPython source trees, `source/` development worktrees, `Temporary Bullshit/` or its generated reports, development compilers/build machinery, host/container bootstrap tooling, or broad Fat/Transition-only regression/fuzz/benchmark/diagnostic material merely because it was useful during qualification.

Runtime self-checks may remain only when they have a real operational responsibility in production.

## Promotion rule

The canonical promotion path is:

**Fat source/development → integrated build + exhaustive qualification → Transition candidate → target qualification → Skinny production image → production/physical qualification.**

Promotion is one-way for artifacts, not for source ownership: failures discovered in Transition or Skinny are repaired back in the Fat source estate, then rebuilt and requalified through the pipeline.

A production image must never be patched ad hoc and then treated as authoritative source.

## Python-first reduction gate

Neither Transition nor Skinny may become smaller by silently reducing Python/JetLang behavior. Start from the exact recorded source and a passing Fat baseline, remove substrate capabilities incrementally, rebuild/boot, rerun applicable qualification, retain only reductions that preserve the required Python-visible surface and device responsibilities, and restore substrate when required behavior regresses.

The optimization target is **the smallest target runtime that preserves the complete qualified JETOS Python capability surface and required hardware responsibilities.**

## Kernel and language ownership

The production kernel is a JETOS-maintained Linux-derived build. JetOS owns the selected source, target configuration, patches, build rules, capability rationale, and qualification evidence. JetLang is likewise built from the controlled CPython-derived source lineage. Coordinated Linux/JetLang changes are permitted when they produce a simpler, faster, or safer integrated runtime, but runtime-affecting changes must satisfy the integrated qualification in `MANDATE.md` and `ARCHITECTURE.md`.

No promoted kernel or interpreter may come from an unrecorded working tree.

## Source retention versus runtime footprint

Complete development source is Fat material. It may exist on build servers, protected source repositories, development disks, and recovery systems. Transition and Skinny images retain only the runtime and compact provenance appropriate to their responsibilities.

Vendoring the Linux and JetLang source into the outer JETOS repository does **not** mean those full source trees belong in the production image. Source ownership and runtime footprint are separate concerns.

## Container/tooling boundary

Docker is currently an acceptable way to provide a familiar, reproducible build/test harness while JetOS is being developed. It is not part of the JetOS runtime architecture. Equivalent OCI-style runners such as Podman may be supported later through the same simple external-tooling boundary.

The container or bootstrap image must never become the source of the JetOS kernel or JetLang runtime. Those come from the JETOS source estate. The long-term direction is to make native/self-hosted JetOS build paths increasingly independent of any particular container implementation.

## Testing and flashing boundary

Fat should be aggressively tested. Transition should run the compact but decisive tests that prove the candidate production projection. Skinny runs the promoted runtime and only the production checks that have a continuing operational responsibility.

For physical targets, the attached data disk is not build scratch space and must not be formatted or modified during bring-up without explicit authorization.
