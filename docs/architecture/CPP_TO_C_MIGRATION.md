# JETOS C++ Elimination Program

**Version:** 0.4  
**Date:** 2026-10-03  
**Status:** Long-term architectural migration plan

## 1. Target language boundary

JETOS-owned executable logic is Python.

Native substrate is C.

Architecture-specific irreducibles may use assembly, and every such file must be registered and justified.

C++ is not an accepted JETOS-owned implementation language. It is migration debt.

Bash may remain available:
- as an interactive shell;
- for user scripts;
- inside quarantined imported-package build environments;
- for Gentoo compatibility while migration is incomplete.

But JETOS-owned internal operating-system logic should not be Bash. Existing internal Bash dependencies should be rewritten in Python over time.

## 2. Package quarantine

Imported packages may require languages JETOS does not accept internally.

Each package build environment should be isolated and record:
- exact source revision;
- source hash;
- exact dependency versions;
- build flags;
- compiler/toolchain version;
- patches;
- licenses;
- source languages;
- build languages;
- whether Bash is required;
- whether C++ is required;
- produced runtime files;
- whether produced binaries link a C++ runtime.

Only approved build outputs are injected into the released JETOS image.

## 3. Fixed dependencies per release

Each JETOS release should use a pinned dependency graph.

For one release:
- source revisions do not drift;
- dependency versions do not drift;
- compiler versions do not drift;
- kernel version/configuration do not drift;
- build flags do not drift;
- patches do not drift.

Upstream updates enter through a later reviewed JETOS release.

The eventual update mechanism may be image-based, atomic, package-based, or hybrid. That decision remains open.

## 4. C++ -> C policy

C++ should be translated into readable, maintainable C.

The goal is behavioral equivalence, not mechanical syntax substitution.

A translation is acceptable only when:
- the C is human-readable;
- ownership is explicit;
- object lifetime is explicit;
- error handling is explicit;
- control flow is explicit;
- source mapping back to upstream is preserved;
- tests demonstrate intended equivalent behavior.

Opaque generated blobs, giant machine-generated state machines, encoded byte arrays, and unreadable transpiler output do not count as acceptable source.

Generated C is allowed only when:
- the generator is readable JETOS-owned Python;
- generation is deterministic;
- generated output remains inspectable and debuggable.

## 5. Standard translation patterns

### Classes
Translate to structs plus functions.

```c
typedef struct {
    int fd;
} jos_device;

int jos_device_init(jos_device *device, int fd);
void jos_device_destroy(jos_device *device);
int jos_device_read(jos_device *device);
```

### Constructors / destructors
Use explicit `_init`, `_create`, `_destroy`, and `_free` functions.

### RAII
Use explicit cleanup paths and ownership rules.

### References
Use pointers with documented nullability.

### Smart pointers
Use explicit ownership transfer or reviewed reference counting.

### Exceptions
Prefer explicit error codes, result structs, and cleanup paths.

### Templates
Use:
1. concrete specializations;
2. Python code generation;
3. simple C macros where justified;
4. type-erased interfaces only when appropriate.

Complex compile-time metaprogramming should move into Python generation tooling where possible.

### Virtual methods / inheritance
Use composition and explicit vtables.

### Namespaces
Use stable prefixes such as `jos_net_*`, `jos_fs_*`, `jos_device_*`.

### Function overloading
Use explicit names.

### Operator overloading
Use named functions.

### Lambdas
Use named callbacks plus context pointers.

### `std::string`
Use a reviewed JETOS C string/buffer abstraction with explicit length, capacity, and ownership.

### STL containers
Replace with a small reviewed JETOS C container library rather than recreating a separate container framework in every port.

### `std::optional`
Use explicit `has_value` plus payload structs.

### `std::variant`
Use tagged unions.

### RTTI / `dynamic_cast`
Use explicit type tags or interface IDs.

### Move semantics
Use explicit ownership-transfer functions.

### Atomics
Use C11 atomics where appropriate.

### `constexpr`
Use C constants, generated tables, or Python-generated static data.

## 6. Migration records

For each translated component preserve:
- upstream version/revision;
- original source paths;
- mapping from original C++ symbols/files to C replacements;
- translation notes;
- semantic differences;
- known deviations;
- tests;
- benchmark results;
- security-sensitive review notes.

The project should be able to answer:
- Which C file replaced this C++ file?
- Which C function implements this original C++ behavior?

## 7. Migration states

Every C++ component gets one status:

- `DISCOVERED`
- `QUARANTINED`
- `MAPPED`
- `PARTIAL`
- `C_EQUIVALENT`
- `REPLACED`
- `REMOVED`

## 8. Priority

### Priority 0 — inventory
Before translating code, generate the exact C++ dependency closure for the selected JETOS build.

Classify:
- build-only C++;
- runtime C++;
- linked C++ standard-library dependencies;
- optional C++;
- unavoidable bootstrap C++.

### Priority 1 — runtime C++
Any C++ library linked into the production JETOS image has higher priority than build-only C++ tooling.

### Priority 2 — compiler/bootstrap C++
The compiler toolchain is a dedicated long-term project.

The key question is:

> What is the smallest compiler/toolchain JETOS needs to rebuild its selected Linux kernel, C runtime, CPython, and JETOS C code for x86-64 and AArch64?

That may lead to:
- a reduced compiler;
- extending a smaller C compiler;
- a Python-fronted compiler project;
- or a GCC-to-C port.

Do not assume a line-for-line GCC rewrite is automatically the best route.

### Priority 3 — selected graphics/audio backends
Only the backends actually required by supported JETOS hardware matter.

### Priority 4 — optional applications
Containerized or optional applications do not need immediate translation unless they become part of the trusted JETOS base.

## 9. GCC warning

Modern GCC is a large C++ codebase and a GCC-to-C conversion is a major independent compiler project.

A mechanical translation is not enough.

Correctness must eventually be demonstrated by:
- compiler bootstrap tests;
- Linux kernel builds;
- CPython builds;
- C-runtime builds;
- x86-64 output tests;
- AArch64 output tests;
- ABI tests;
- optimizer correctness tests;
- debug-info tests;
- linker/object compatibility tests.

Compiler bugs can silently miscompile the operating system, so the verification bar is much higher than for ordinary application ports.

## 10. Alternative to rewriting all of GCC

The long-term no-C++ toolchain does not have to be GCC translated line by line.

Possible path:
1. quarantine GCC initially;
2. measure exactly which GNU C features the JETOS source closure uses;
3. reduce unnecessary compiler-specific extensions where practical;
4. adopt or build a smaller compiler using approved languages;
5. support x86-64;
6. support AArch64;
7. validate it against the JETOS kernel, C runtime, CPython, and native extensions;
8. remove GCC/C++ from the bootstrap closure.

This may be substantially easier to maintain than a permanent GCC translation fork.

## 11. Human-readable C rule

Canonical C source must remain understandable to a human.

Do not accept as canonical source:
- byte arrays that encode program logic;
- mangled numeric identifiers replacing meaningful names;
- huge generated state machines with no mapping;
- macro systems that recreate C++ more opaquely than the original;
- compiler output disguised as source.

Prefer:
- meaningful names;
- ordinary structs;
- small functions;
- explicit ownership;
- explicit lifetime;
- explicit errors;
- normal comments where translation is non-obvious.

## 12. CPython relationship

The intended long-term stack is approximately:

```text
firmware / boot
        ↓
Linux kernel (C + assembly)
        ↓
C runtime / minimal native substrate
        ↓
CPython
        ↓
JETOS Python control plane
        ↓
JETOS APIs / services / applications
```

The goal is for Python to be the language in which the operating system is normally understood and changed.

## 13. Upstream synchronization after translation

Once a component has been translated to C, future upstream C++ changes should be handled deliberately.

For each upstream release:
1. inspect upstream diffs;
2. identify semantic changes;
3. port relevant behavior into the JETOS C implementation;
4. update tests;
5. benchmark;
6. record upstream version/commit correspondence.

Do not blindly regenerate the C tree from upstream C++ and overwrite human-maintained source.

Python tooling may assist with mapping, comparison, and change detection.

## 14. Definition of done for one component

A C++ component is removed from the JETOS trusted base only when:
- JETOS no longer requires its C++ implementation;
- no production runtime binary links its C++ runtime;
- normal JETOS builds no longer require the C++ implementation;
- a readable C/Python/approved-assembly replacement exists;
- behavioral tests pass;
- architecture tests pass where applicable;
- provenance is documented;
- the generated dependency/language report shows the C++ dependency is gone.

## 15. Current strategy

For now:

1. quarantine Gentoo/GCC/Bash build tooling;
2. pin dependencies per release;
3. inventory the full language and linkage closure;
4. introduce no new JETOS-owned C++;
5. rewrite JETOS-owned Bash control logic in Python;
6. eliminate production-runtime C++ first;
7. work backward into build/bootstrap C++;
8. treat the compiler as a separate long-term migration project.

## 16. Canonical shorthand

> Python for JETOS logic.  
> C for native implementation.  
> Assembly only where the architecture demands it.  
> Bash may be a shell, not the JETOS control language.  
> C++ is migration debt.

> Imported badness is quarantined.  
> Released dependencies are fixed.  
> Every exception is enumerable.  
> Every translated source remains readable.