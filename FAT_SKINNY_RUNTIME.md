# JETOS Fat/Skinny source and native-runtime contract

Status: **canonical architecture rule**

JETOS has two deployment modes derived from the same source lineage.

## Fat mode

**Fat mode is the portable source universe.** A qualified Fat image carries the complete source material needed to understand, rebuild, retarget, and derive JETOS for the supported machine families. That includes the JETOS-owned source, the selected JETOS Language/CPython source, the selected kernel source, JETOS-owned C-extension source, and the source/provenance closure for imported native runtime dependencies.

Fat mode is not interpreted-only. On the machine that is currently running it, JETOS builds and uses the **current target-native compiled runtime**:

- the current JETOS Language/CPython build is the interpreter used at runtime;
- JETOS-owned C extensions are compiled for the current CPU/ABI and imported by Python;
- performance-critical operations and native/hardware boundaries execute as pure C behind those C-extension objects/functions;
- Python remains the public object model, orchestration, policy, compatibility, and control surface;
- source for other supported targets remains available for rebuilding/retargeting but is not executed merely because it is present.

Therefore Fat mode means **all relevant source is locally available, while the current machine still runs compiled target-native artifacts for speed**.

### Fat source-closure gate

The architectural target is complete source closure, but JETOS must distinguish that target from what the current bootstrap actually proves. The first implementation packages JETOS, JETOS Language/CPython, Linux, and JETOS-owned C-extension source. The current rootfs builder still copies some imported native shared libraries from its build environment.

Until the corresponding source/provenance for libc, dynamic loader, crypto/compression/database/FFI and any other retained native runtime dependencies is pinned and carried or otherwise reproducibly derivable from the Fat source set, the image must report that **complete portable source closure is not yet qualified**. Missing closure is work to finish, not permission to redefine Fat as binary-only.

## Skinny mode

**Skinny mode is the target-resolved runtime.** It is derived from the same Fat source lineage for one selected machine/role.

A Skinny image retains only the runtime material required by that target and declared role, including:

- the target-native compiled JETOS Language runtime;
- the required Python standard library;
- the C-extension binaries compiled for that target/ABI;
- selected kernel/boot/device artifacts;
- required applications/capabilities;
- compact version/provenance/build metadata sufficient to identify the exact Fat source lineage that produced it.

Development-only source trees, alternate-architecture native artifacts, tests, compilers, build intermediates, and unrelated capabilities are omitted unless the target role explicitly requires them.

Skinny is not a different JETOS edition. It is a resolved deployment of the same source/version.

## Native execution rule

The normal high-performance path is:

```text
Python object/API
    -> CPython C extension
        -> pure C operation
            -> kernel / hardware / ABI boundary when required
```

JETOS-owned C should not become a second user-facing application framework. Its normal jobs are:

1. hardware and kernel interfaces that require native access;
2. CPython extension types that turn native handles/state into Python objects;
3. measured hot operations where C materially improves speed or latency;
4. ABI/boot/runtime substrate that Python cannot correctly provide itself.

For equivalent hardware capability, the Python-facing object contract should remain stable even when the native C implementation differs by CPU, board, kernel interface, or driver family.

## Primary hardware objective

JETOS's #1 native-development objective is to discover useful low-level hardware APIs/interfaces and re-express them as Python-native capabilities through C extensions. Native functions, handles, buffers, structures, events, device state, and other hardware-facing concepts should become Python objects/interfaces instead of remaining opaque C-only surfaces.

This work is deliberately incremental. Each hardware binding should be added in small reviewable stages, retain a stable Python contract where practical, and be tested repeatedly across major supported environments rather than being accepted because it works on one developer machine. The initial qualification families are `x86_64`, `armv7` (including the ODROID-HC1), and `arm64`; board-specific C remains isolated behind the shared Python-facing capability model.

Fat mode carries the C-extension source/backends needed to rebuild across those environments. The running Fat machine uses only the extension compiled for its current target. A derived Skinny image carries only the native backend(s) selected for its target and role.

## Source-to-runtime invariant

Both modes obey the same invariant:

> **The running compiled artifact must be traceable to the current selected source.**

Fat keeps that source locally. Skinny may omit the bulk source, but it must retain provenance identifying the exact source revisions/build inputs that produced the runtime.

A stale native extension compiled from a different source/ABI does not satisfy this rule merely because it imports successfully.

## First implementation

JETOS provides a small `_jetos_native` CPython extension as the first runtime spine for this policy. It exposes a native C-backed `NativeBuffer` Python object and a pure-C bytes operation. The purpose is not that these two primitives are themselves the final hardware API; they prove the required build/import/object pattern that hardware bindings will follow incrementally.

The extension source is portable source carried by Fat mode. Both Fat and Skinny packaging compile a target-native extension for the current JETOS Language ABI and place that compiled module in the runtime package. The Python fallback exists for source inspection/development failure diagnostics, but a qualified packaged runtime must report the compiled native extension as active.
