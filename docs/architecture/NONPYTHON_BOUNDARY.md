# JETOS Bootstrap and Non-Python Boundary

**Version:** 0.3  
**Date:** 2026-10-03  
**Status:** Working architecture / review document

## 1. Practical definition of JETOS

JETOS does not need to obey a narrow academic definition of "operating system."

For this project, JETOS is the software system that can replace the previously installed operating system on a supported machine and then becomes responsible for bringing that machine back into a usable state.

A native JETOS deployment is expected to:

1. arrive from outside the target machine or be preloaded for that exact machine;
2. establish a boot path;
3. identify the machine/board/device profile and relevant hardware capabilities;
4. install or select the kernel, drivers, firmware, filesystems, networking support, graphics support, audio support, and other capabilities required for the target;
5. install the JETOS Python runtime and JETOS control plane;
6. make itself independently bootable;
7. reboot into JETOS;
8. thereafter own the software policy of the device.

JETOS may use Linux, Gentoo sources, firmware, boot firmware, C libraries, and other native components underneath this contract. Those components are substrate, not the conceptual boundary of JETOS.

## 2. Two installation modes

### 2.1 Prebuilt / drop-in image

For a known hardware target, JETOS may be constructed ahead of time as a complete image.

Examples:

- a raw SSD/NVMe/eMMC image;
- an SD-card image;
- an EFI System Partition plus root filesystem image;
- a board-specific flash image.

For ordinary UEFI PCs, replacing the drive contents can be sufficient when the drive contains the required EFI boot files and root filesystem and the firmware will boot them.

For many phones, tablets, and embedded systems, storage replacement alone is not enough. Their boot ROM, secure-boot policy, bootloader, device tree, firmware, or signed boot chain may live outside the replaceable root filesystem.

### 2.2 Bootstrap installer

JETOS may also boot a small installer environment from outside the installed operating system.

Possible entry mechanisms include:

- USB;
- removable SD;
- PXE/network boot;
- UEFI removable-media boot;
- U-Boot;
- vendor flashing/recovery protocols;
- another explicitly supported device-specific boot path.

The bootstrap environment then:

1. inventories the target;
2. resolves a JETOS device profile;
3. validates support;
4. partitions/formats storage;
5. installs the target kernel/modules/firmware;
6. installs the JETOS runtime;
7. installs target capabilities;
8. configures the target's boot method;
9. verifies the installation;
10. reboots into JETOS.

The bootstrapper should be Python-first after the smallest required native launch layer is running.

## 3. Strict source-language rule

### 3.1 JETOS-owned executable logic

New executable program logic owned by JETOS is Python.

### 3.2 C exception

C is allowed only when Python cannot correctly or reasonably provide the required native boundary.

### 3.3 Assembly exception

Assembly is allowed only for the small architecture-specific operations for which C is insufficient or inappropriate.

### 3.4 C++ rule

C++ is **not** an approved JETOS-owned implementation language.

Any C++ required during early bootstrap is a temporary imported-toolchain exception and must be registered.

The deployed JETOS runtime should target **zero required C++ components** unless a future explicit JETOS decision changes this rule.

### 3.5 Other languages

Shell, Perl, Ruby, Rust, Go, JavaScript, Java, Lua, etc. are not approved JETOS-owned implementation languages.

Imported upstream source may temporarily contain them. Such source must be classified as imported and should not silently expand the JETOS language policy.

Declarative formats remain allowed.

---

# 4. Things that cannot simply be ordinary Python under the CPython/Linux design

This is the review list.

"Cannot be Python" below means that ordinary CPython source cannot itself perform the job from power-on without some lower native layer. It does **not** mean the component can never be redesigned, minimized, moved to userspace, or replaced.

## 4.1 CPU reset / earliest machine entry

**Required native form:** machine instructions / firmware / assembly-level entry.

At reset there is no CPython interpreter, Python heap, process model, filesystem, or Python import system.

JETOS can minimize how much code it owns here, but the processor must begin by executing native instructions.

**JETOS policy:** imported platform firmware or tiny registered architecture-specific native layer.

## 4.2 Platform firmware

Examples:

- UEFI;
- board firmware;
- boot ROM;
- secure-boot firmware.

This normally exists before JETOS and may not live on the operating-system disk.

**JETOS policy:** treat as hardware/platform substrate and record it in the device profile.

## 4.3 Bootloader / kernel loader / EFI handoff

Something must load the kernel before Python exists.

JETOS may avoid a large conventional bootloader on suitable UEFI systems by booting a Linux EFI-stub kernel/UKI-style artifact directly, but that artifact is still native code.

**Likely languages:** C + assembly / generated machine code.

## 4.4 Linux kernel

The initial JETOS kernel is Linux.

The Linux kernel's normal implementation is native code, predominantly C with architecture-specific assembly. Kernel documentation explicitly describes assembly as necessary for some architecture/platform operations and recommends C when possible.

**JETOS policy:** C + registered architecture assembly. Configure out optional language ecosystems JETOS does not approve where possible.

A conventional CPython program cannot replace the kernel because CPython itself requires kernel services in order to run.

## 4.5 Earliest architecture-specific kernel code

Examples:

- CPU entry;
- exception/interrupt entry;
- context-switch details;
- low-level atomic/ordering operations;
- syscall entry/return;
- architecture-specific boot handoff.

**Likely language:** assembly plus C.

These are expected registered exceptions.

## 4.6 Kernel device drivers

To access storage, networking, USB, PCIe, display hardware, input, and other hardware early enough to boot, JETOS initially depends on Linux kernel drivers.

**Likely language:** primarily C, plus small architecture/device-specific native portions.

Some future drivers may move to userspace, where Python can own more policy, but JETOS should not require rewriting mature kernel drivers merely to claim that hardware support is Python.

## 4.7 C runtime / dynamic loader

CPython and many native components require a C ABI/runtime and loader.

Candidate JETOS choices include glibc or a smaller C library such as musl, subject to compatibility testing.

**Likely language:** C + architecture-specific assembly.

## 4.8 CPython interpreter

Python source does not execute by itself.

CPython's executable entry point and interpreter runtime are native C code. JETOS may modify or specialize CPython, but some native interpreter implementation must exist unless JETOS later adopts a different Python implementation model.

**JETOS policy:** CPython is an explicitly blessed native substrate component.

## 4.9 CPython extension boundary

Some kernel APIs, ioctls, memory mapping, hardware APIs, performance-critical operations, or ABI interactions may not have an adequate standard-library binding.

**Preferred order:**

1. Python standard library;
2. Python direct facilities such as `os`, `socket`, `mmap`, `ctypes`;
3. small C extension;
4. assembly only when necessary.

Every JETOS-owned extension is registered.

## 4.10 Cryptographic native primitives

Correct cryptographic protocols can be orchestrated in Python, but high-quality deployed crypto libraries commonly use C and architecture-specific assembly for performance and constant-time primitives.

JETOS should initially treat a vetted C/assembly crypto implementation as substrate rather than attempt an immediate pure-Python cryptographic rewrite.

## 4.11 Filesystem implementation

An ext4 root filesystem requires the kernel filesystem implementation during normal operation.

**Kernel side:** C.

Utilities such as formatting/checking tools may initially remain imported C utilities and can be reconsidered separately.

## 4.12 Machine-code compilation

Producing native executables ultimately requires something that emits machine code and object files.

The compiler program could theoretically be written in Python. There is no law requiring a compiler implementation to be C or C++.

However, the compiler must correctly implement enough of the C language, ABI, assembler/object format, linker interaction, and compiler extensions required by Linux, CPython, and chosen upstream code.

Therefore this is not intrinsically "non-Python"; it is an enormous engineering project if JETOS replaces the production compiler.

---

# 5. Gentoo-specific non-Python areas we inherit today

## 5.1 Ebuilds and eclasses — Bash

Gentoo's ebuild format is executable Bash. The Gentoo developer manual states that all ebuild scripts are written in Bash.

Therefore, if JETOS wants to remain directly compatible with unmodified Gentoo package recipes, the **development/build side requires Bash**.

This is not required on the deployed runtime if packages/images are built elsewhere.

### Elimination path

JETOS can eventually:

1. define a Python-native package recipe model;
2. port only the recipes in the JETOS dependency closure;
3. keep a quarantined Gentoo/Bash compatibility builder for unported packages;
4. progressively reduce that compatibility closure.

Automatically converting arbitrary ebuilds is not guaranteed because ebuilds can execute arbitrary shell logic.

## 5.2 Gentoo bootstrap script — shell

Gentoo's current repository includes shell bootstrap machinery.

**JETOS plan:** replace JETOS bootstrap orchestration with Python rather than adopting these scripts as JETOS-owned code.

## 5.3 OpenRC — C + POSIX shell

OpenRC reports that its core is C99 and its surrounding service layer uses POSIX shell scripts.

**JETOS plan:** OpenRC may be a temporary bootstrap service manager, but JETOS should replace service definitions/supervision with the Python JETOS supervisor if practical.

## 5.4 Standard Gentoo command-line base

The Gentoo base profile includes many traditional native command-line packages: Bash, Make, GCC, binutils, coreutils, archive tools, filesystem tools, networking tools, etc.

JETOS does not need to retain all of these in the deployed runtime.

The build system should distinguish:

- bootstrap dependency;
- development dependency;
- recovery dependency;
- deployed runtime dependency.

---

# 6. C++ inventory: the important current Gentoo/JETOS blockers

A truly exhaustive list of "all C++ in Gentoo" depends on which packages are selected. Gentoo is a repository of recipes for a very large number of independently developed upstream projects, many of which are C++ applications and libraries.

Therefore JETOS should define "all C++" against a **pinned dependency closure**.

For the initial minimal Gentoo-derived bootstrap, these are the major known C++ points that matter immediately.

## 6.1 GCC — unavoidable in the normal Gentoo source bootstrap

**Status:** major C++ bootstrap dependency.

Gentoo's base profile includes `sys-devel/gcc`.

Gentoo's base policy currently forces GCC's `cxx` feature because modern GCC needs C++ to bootstrap.

Current GCC requires an ISO C++14 compiler to bootstrap.

### Consequence

A normal current source-built Gentoo development environment cannot satisfy a strict "no C++ anywhere in the toolchain" rule without changing the compiler bootstrap strategy.

### JETOS choices

**Choice A — temporary quarantined bootstrap exception**

Use current GCC to build JETOS, but:

- mark GCC/C++ as imported development-only;
- omit GCC and libstdc++ from deployed images unless required;
- prohibit JETOS-owned C++ source.

This is the recommended first bootstrap.

**Choice B — replace GCC with Clang/LLVM**

Does **not** eliminate C++.

LLVM's own documentation says most LLVM source is C++ and building LLVM requires a modern C++ compiler and standard library.

**Choice C — replace the production toolchain**

Long-term JETOS could create/adopt a compiler whose implementation is Python + C and that emits code for x86-64 and AArch64.

For it to replace GCC/Clang for JETOS self-hosting it would need to compile, at minimum:

- the selected Linux kernel configuration;
- the selected C library;
- CPython;
- JETOS C extensions;
- all required C upstream substrate;
- architecture assembly;
- ELF objects;
- shared libraries;
- enough GNU C extensions used by the selected source base.

This is feasible in principle but is a major compiler project.

**Choice D — translate modern GCC C++ implementation to C**

Possible in the abstract, but this is a very large and ongoing fork burden. Every upstream GCC change would need continued translation/maintenance.

It is not a sensible Phase-1 blocker.

## 6.2 libstdc++

If GCC is built with C++ support, its C++ standard library is normally part of the toolchain.

**Runtime policy:** omit it from a deployed JETOS image if nothing in that image links against it.

## 6.3 LLVM/Clang and LLVM-based packages

Any decision to use LLVM/Clang introduces a large C++ codebase.

JETOS should not select an LLVM Gentoo profile if the objective is minimizing C++ in the bootstrap closure.

Some graphics stacks or language toolchains may optionally pull LLVM in; the JETOS profile must audit and block those paths unless deliberately approved.

## 6.4 Optional upstream applications/libraries

Any selected upstream package may itself be C++.

Therefore the authoritative C++ answer must come from the JETOS build manifest, not from a static prose list.

For every target build, JETOS should generate:

```text
jetos inspect languages --closure
```

conceptually reporting:

```text
Python       JETOS-owned
C            approved native/substrate
Assembly     approved architecture/substrate
C++          imported exceptions: [exact package/file list]
Shell        Gentoo compatibility exceptions: [exact recipe/tool list]
Other        [exact package/file list]
```

A production target whose policy is `cxx_allowed = false` fails the build if the installed runtime closure contains C++ artifacts or an unapproved C++ source dependency.

---

# 7. Things we can realistically move to Python

These areas do not fundamentally need to remain traditional Unix command programs.

## High-priority Python replacements

- installer/bootstrap orchestration;
- hardware inventory;
- device-profile resolution;
- storage-layout policy;
- mount orchestration after kernel support exists;
- service supervision;
- logging policy;
- network configuration;
- route configuration via netlink;
- network master ON/OFF coordinator;
- firewall policy generation/control;
- DHCP client;
- DNS configuration;
- package/image manifest handling;
- package dependency resolver;
- source acquisition;
- build orchestration;
- update client;
- system configuration;
- user/account policy;
- container orchestration;
- cgroup policy;
- namespace creation/orchestration;
- application permissions;
- capability broker;
- system introspection;
- test harness;
- Git hooks;
- provenance scanner;
- language scanner;
- image composition;
- first-boot setup.

## Possible but lower priority

- filesystem creation/checking utilities;
- archive utilities;
- basic file/core utilities;
- process-listing tools;
- network diagnostic tools;
- simple shell-like administrative interface;
- package recipe language replacement.

These can be Python implementations, but replacing mature C tools should be justified by JETOS simplicity/introspection or measurable improvement.

---

# 8. Graphics without C++

JETOS does not need a desktop stack merely to draw.

A minimal graphical target can conceptually use:

1. Linux DRM/KMS kernel drivers — C;
2. a small JETOS C binding where Python lacks adequate ioctls/memory mappings;
3. Python JETOS graphics policy/API;
4. direct buffers/software rendering initially;
5. later a selected accelerated backend.

This gives JETOS a path to a screen without making Qt, KDE, GNOME, X11, or a C++ GUI framework part of the operating-system definition.

A sophisticated accelerated GPU stack may introduce additional native-language dependencies. Those must be audited per hardware target.

---

# 9. Audio without C++

A minimal audio target can conceptually use:

1. Linux kernel sound driver — C;
2. ALSA or a smaller direct backend — C;
3. Python JETOS audio API/control;
4. optional higher-level audio service only when required.

C++ is not intrinsically required for basic audio support.

---

# 10. Networking without shell-heavy userspace

The kernel TCP/IP stack remains native C.

JETOS can move much of the user-facing networking control into Python:

- enumerate links;
- configure addresses;
- manipulate routes;
- control network namespaces;
- control nftables/netfilter through an appropriate binding/backend;
- coordinate rfkill;
- implement DHCP/DNS client behavior;
- enforce the JETOS master network switch.

Wi-Fi security, Bluetooth, and cellular bring substantial protocol/device complexity. Imported C daemons may be retained initially and later replaced only if doing so improves JETOS.

---

# 11. Optimization doctrine: one saved operation counts

JETOS explicitly values removal of unnecessary work.

An optimization is valid even if it saves only one operation, provided it does not damage correctness, inspectability, security, or maintainability.

Measure at least:

- boot-time process creation;
- `fork`/`exec` count;
- subprocess count;
- filesystem reads;
- metadata parsing;
- package dependency computations;
- Python interpreter startups;
- module imports;
- syscalls;
- IPC round trips;
- context switches;
- memory allocations where practical;
- bytes read/written;
- network round trips.

Candidate early Gentoo/JETOS improvements:

1. move shell orchestration into persistent Python processes to avoid repeated `fork`/`exec`;
2. cache parsed package metadata;
3. cache resolved dependency graphs with correct invalidation;
4. avoid re-reading unchanged configuration;
5. avoid starting services the target does not use;
6. eliminate runtime utilities when Python already provides the operation;
7. build target-specific kernels/modules instead of probing impossible hardware forever;
8. keep the long-lived JETOS supervisor resident rather than repeatedly starting Python for trivial system operations;
9. precompile Python bytecode where useful;
10. profile before and after every optimization and record the delta.

"Faster" must be measurable.

---

# 12. Proposed language states

## Phase 1 — JETOS runtime

Target:

- Python: yes;
- C: approved substrate/bindings;
- assembly: approved architecture-specific substrate;
- C++: **no runtime dependency unless explicitly discovered and registered**;
- shell: no normal JETOS runtime control plane;
- other executable languages: no.

## Phase 1 — JETOS development builder

Temporary target:

- Python: JETOS orchestration;
- C: substrate;
- assembly: substrate;
- C++: **GCC bootstrap exception**;
- shell: **Gentoo ebuild/eclass compatibility exception**;
- other languages: only if pulled by an explicitly approved build dependency.

This is intentionally less pure than the deployed system.

## Long-term self-hosting goal

- Python JETOS build system;
- Python-native JETOS package recipes;
- C/assembly native substrate;
- no C++;
- no shell-required JETOS build logic;
- compiler strategy that itself satisfies the language constitution or is the last explicitly quarantined bootstrap exception.

---

# 13. Required generated reports

Every JETOS target build should eventually emit:

## `FILES.json`

Every installed file, hash, owner, provenance, purpose.

## `LANGUAGES.json`

Every source-language occurrence in the dependency/build/runtime closure.

## `EXCEPTIONS.json`

Every non-Python JETOS-owned executable-source exception.

## `UPSTREAM.json`

Every imported upstream component, version, revision, source, license.

## `HARDWARE.json`

The intended/detected hardware capabilities for the image/device.

## `CAPABILITIES.json`

Which hardware capabilities have software implementations installed, which are permitted, and which are active.

## `BUILD_GRAPH.json`

Trace from sources and rules to final installed artifacts.

## `BOOT_TRACE.json`

Measured boot sequence, startup processes/services, timings, and relevant operations.

---

# 14. Immediate architectural conclusion

The strict JETOS rule can be stated as:

> **JETOS logic is Python. Native substrate is C. Architecture irreducibles are assembly. Everything else is an exception to eliminate, quarantine, or explicitly approve.**

The biggest immediate violations inherited from a normal Gentoo development system are:

1. **Bash** — because Gentoo ebuilds/eclasses are Bash;
2. **C++** — because current GCC needs C++ to bootstrap;
3. **POSIX shell around OpenRC** if OpenRC is used;
4. miscellaneous build-system languages/scripts pulled by upstream packages.

These do not need to survive into the deployed runtime.

The build system must make them visible and measurable so the exception set can shrink rather than silently grow.