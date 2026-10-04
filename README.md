# JETOS — John E Tordoff's Operating System

JETOS is a source-oriented, Python-first operating-system project whose long-term goal is to replace the software stack on a target machine rather than merely run as an application inside another operating system.

**Project state:** early bootstrap / architecture / executable experiments.

The current repository is intentionally small. It proves pieces of the design in Docker and in native C/Python tests. It is **not yet a standalone bootable distribution**. The next major milestone is a hypervisor-bootable JETOS image with its own selected Linux kernel, root filesystem, PID 1/bootstrap path, CPython runtime, and console.

---

## 1. What JETOS means by an operating system

JETOS uses an operational definition rather than an academic boundary.

A mature JETOS installation should be able to:

1. replace the previous operating-system installation on supported hardware;
2. own or select the boot path;
3. discover the machine and its capabilities;
4. install only the implementations required for the declared device role;
5. control storage, networking, display, audio, input, containers, and other enabled capabilities;
6. start its own early userspace and Python control plane;
7. account for the files, languages, provenance, dependencies, and exceptions that compose the running system;
8. be reproducibly rebuilt from pinned source inputs;
9. run across x86-64 and AArch64 with the same JETOS-facing behavior where practical.

Gentoo is used as source/build infrastructure and upstream material. It is not JETOS's identity.

---

## 2. What JETOS can do today

The distinction between **implemented now** and **planned architecture** matters.

| Capability | Status | What exists now |
|---|---|---|
| Git source repository | Implemented | Private GitHub repository with ordinary Git history |
| Python-first control code | Implemented, small | `src/jetos/` contains the first JETOS Python modules |
| Hardware snapshot | Implemented, minimal | Reports architecture, CPU count, sysfs, Device Tree, and ACPI presence |
| Native C boundary | Implemented, experimental | First readable C replacement experiment based on a GCC C++ utility |
| Strict C tests | Implemented | C11, warnings-as-errors, pedantic build |
| Sanitizer tests | Implemented | AddressSanitizer + UndefinedBehaviorSanitizer run for the C experiment |
| Dunicode | Implemented, v0.1 | JETOS-native 1:1 character layer over Unicode scalar values |
| Unicode / UTF-8 | Implemented, smoke-tested | Strict UTF-8 round trips, multilingual text, emoji, combining characters, invalid UTF-8 rejection, filesystem cases |
| Docker test image | Implemented | Reproducible userspace/test container |
| Hypervisor boot | Planned | Architecture defined; no bootable VM image yet |
| JETOS-controlled kernel | Planned | Linux is the initial kernel, but no JETOS kernel build/image is committed yet |
| JETOS PID 1 | Planned | Not implemented yet |
| JETOS interactive console | Planned | Not implemented yet |
| Full hardware discovery | Planned | Only a small Python snapshot exists today |
| Master networking OFF switch | Planned | Defined behavior, not implemented |
| File/provenance manifest | Planned | Required architecture, not implemented |
| Capability-driven image composition | Planned | Defined architecture, not implemented |
| Fixed/pinned release graph | Planned | Policy defined; release machinery not implemented |
| Package quarantine | Planned | Policy defined; builder not implemented |
| Python-native package orchestration | Planned | Portage/Gentoo can bootstrap development, but replacement is future work |
| C++ elimination | Active experiment | C++ is migration debt; first C-equivalent component exists |
| Bash elimination from JETOS internals | Planned | Bash may remain a user shell or quarantined build dependency |
| Containers | Planned runtime capability | Docker is currently only a development/test vehicle |
| GUI | Optional / planned | Installed only for device roles that require graphics |
| Audio | Optional / planned | Installed only for device roles that require audio |
| x86-64 | Target | Development/test target |
| AArch64 / ARM64 | Target | Development/test target |
| RISC-V64 | Possible later | Not an initial target |
| Recovery / alternate boot | Planned | Required before physical-machine deployment |
| Signed/atomic updates | Undecided | Update architecture intentionally not frozen yet |

In short, **today JETOS is a tested bootstrap seed, not yet a bootable OS image**.

---

## 3. Language constitution

JETOS has a deliberately restrictive language policy:

> No mysterious files.  
> No mysterious build steps.  
> No mysterious languages.

### JETOS-owned executable logic

1. **Python first.**
2. **C** when Python cannot correctly or reasonably implement a native boundary.
3. **Assembly** only where the architecture itself requires it.
4. Every non-Python JETOS-owned executable source file must be explainable and reviewable.

C++ is not an accepted long-term JETOS implementation language. Existing C++ required by imported toolchains or upstream packages is migration debt.

Bash is not banned from the machine. It may remain:

- an interactive user shell;
- a user scripting tool;
- an imported-package compatibility dependency;
- a quarantined Gentoo/ebuild build dependency;
- an emergency compatibility tool.

JETOS-owned operating-system control logic should not depend on Bash.

Declarative data is allowed when it is genuinely data. Configuration that grows control flow should move to Python.

---

## 4. C++ elimination

The long-term native-language goal is:

> Python for JETOS logic.  
> C for native implementation.  
> Assembly only where architecture demands it.  
> C++ is migration debt.

Readable transformations include:

- classes → structs + functions;
- constructors/destructors → explicit init/create/destroy/free functions;
- RAII → explicit ownership and cleanup paths;
- references → pointers with contracts;
- smart pointers → explicit ownership or reference counting;
- exceptions → explicit results/error codes;
- templates → concrete C specializations or Python-generated simple C;
- inheritance → composition or explicit vtables;
- namespaces → readable prefixes;
- overloads/operators → explicitly named functions;
- lambdas → callbacks + context;
- `std::string` → explicit string/buffer abstractions;
- STL containers → small reviewed C data structures;
- optional values → presence flag + payload;
- variants → tagged unions;
- RTTI → explicit type/interface identifiers;
- move semantics → explicit ownership transfer;
- atomics → C11 atomics where appropriate;
- C++ compile-time metaprogramming → readable Python generation producing simple C.

Generated C is acceptable only when the generator is readable JETOS-owned Python and the generated C remains inspectable and debuggable.

Opaque compiler output, giant numeric state machines, encoded blobs masquerading as source, or macro systems that merely recreate C++ opacity are not acceptable canonical source.

### Current GCC experiment

The first experiment is in:

`ports/gcc/ordered_hash_map_c/`

It is based on GCC's `ordered_hash_map` behavior and the corresponding upstream tests.

Pinned provenance:

- upstream project: GCC;
- upstream repository: `gcc-mirror/gcc`;
- GCC commit: `4bf11aca586c9eef753b6f76d29ae19e1b505694`;
- `gcc/ordered-hash-map.h` blob: `3331394d985820d10ad2150a1c35ceec8f13985b`;
- `gcc/ordered-hash-map-tests.cc` blob: `b033bc5b7c2c7013cd5b54fd0eef3bb43b85ad16`.

The C implementation currently has explicit specializations for the behaviors exercised by the selected GCC tests rather than pretending to be a generic template system.

Observed test result:

```text
ordered_hash_map C port: 91 checks passed
```

The experiment has also passed under AddressSanitizer + UndefinedBehaviorSanitizer.

This **does not yet mean GCC itself uses the replacement**. The next real compiler milestone is converting an actual GCC call path and rebuilding/running GCC's native tests.

The derived GCC experiment remains marked **GPL-3.0-or-later** in its source headers. The standalone license-text copy has intentionally been removed from this private bootstrap repository. Before GPL-derived files are distributed or conveyed to others, the distribution must satisfy the applicable GPL notice/license-source obligations.

---

## 5. Dunicode and Unicode

JETOS supports both **Dunicode** and **Unicode**.

### 5.1 Unicode

Unicode remains the interoperability character repertoire used by normal software, files, protocols, terminals, and Python.

When JETOS controls a textual byte representation, the default encoding is **UTF-8**.

JETOS uses:

- Python `str` for human text;
- Python `bytes` for uninterpreted binary data;
- strict UTF-8 at JETOS-owned text boundaries;
- explicit conversion when an external system requires UTF-16, UTF-32, a legacy code page, or another encoding.

JETOS must not silently destroy data at an encoding boundary.

### 5.2 Dunicode v0.1

Dunicode is the JETOS-native character layer.

For version 0.1, Dunicode is deliberately boring:

- every Dunicode character maps **1:1** to a valid Unicode scalar value;
- Dunicode therefore covers the same scalar range as Unicode;
- a Dunicode scalar may be displayed as `D+XXXX` or `D+XXXXX`;
- Dunicode text serializes to ordinary strict UTF-8;
- converting Unicode → Dunicode → Unicode is lossless;
- Dunicode does not silently normalize text;
- surrogate code points are invalid;
- malformed UTF-8 is rejected rather than silently repaired.

Examples:

```text
Unicode U+0041  <->  Dunicode D+0041   A
Unicode U+00E9  <->  Dunicode D+00E9   é
Unicode U+6F22  <->  Dunicode D+6F22   漢
Unicode U+1F9EA <->  Dunicode D+1F9EA  🧪
```

This gives JETOS its own explicit text abstraction without sacrificing compatibility with the existing Unicode world.

Future Dunicode versions may add JETOS-specific semantics, but version 0.1 must remain fully reversible and Unicode-compatible.

### 5.3 Filesystem bytes

POSIX filenames are fundamentally byte sequences and are not guaranteed to contain valid UTF-8.

Therefore:

- filenames created by JETOS should normally be valid UTF-8;
- normal text paths can be exposed as Unicode/Dunicode text;
- arbitrary imported filename bytes must remain round-trippable;
- JETOS must never silently replace invalid filename bytes and then write back a different path.

### 5.4 Normalization

UTF-8 encoding is separate from Unicode normalization.

JETOS preserves the original Unicode scalar sequence unless a particular protocol explicitly requires NFC, NFD, NFKC, or NFKD.

Exact filenames, hashes, provenance identifiers, and other byte-sensitive data are not silently normalized.

### 5.5 Unicode visibility

Unicode remains valid even when it contains bidirectional controls, zero-width characters, mixed scripts, or confusables.

JETOS inspection/developer tools should make potentially deceptive invisible or direction-changing characters visible rather than globally banning them.

---

## 6. Gentoo relationship

JETOS is not intended to be a renamed precompiled Gentoo distribution.

Gentoo is useful because it provides:

- a source-oriented package ecosystem;
- Portage;
- ebuilds/eclasses;
- architecture support;
- profiles;
- patches;
- package metadata;
- a huge upstream dependency graph that can be inspected and selectively reused.

The development/build side may retain Gentoo capabilities.

The deployed JETOS image should contain only what its device role requires.

Long term, JETOS may replace Gentoo-owned orchestration with Python-native JETOS machinery while continuing to consume upstream source packages.

---

## 7. Imported-code quarantine and release pinning

Imported source does not automatically become trusted JETOS architecture.

A future package/import record should be able to state:

- exact upstream source revision/hash;
- exact dependency versions;
- build flags;
- compiler/toolchain;
- patches;
- licenses;
- source/build languages;
- whether Bash or C++ was required to build it;
- produced runtime files;
- whether it links a C++ runtime;
- whether it is allowed in a production image.

Build environments may temporarily contain languages forbidden in JETOS-owned source.

Only approved outputs are injected into a released image.

A JETOS release should pin its source and dependency graph. Normal runtime operation should not randomly drift compiler, kernel, dependency, patch, or flag versions.

---

## 8. Native boundaries that cannot simply become Python

Ordinary CPython cannot implement the machine from power-on without native substrate.

JETOS initially accepts native/imported boundaries for:

1. CPU reset and earliest architecture entry;
2. firmware;
3. bootloader / EFI / kernel handoff;
4. Linux kernel;
5. architecture-specific kernel code;
6. kernel device drivers;
7. C runtime and dynamic loader;
8. CPython interpreter;
9. CPython native extension boundaries;
10. cryptographic native primitives where required;
11. filesystem implementation;
12. machine-code compilation.

The goal is not to pretend those boundaries are Python. The goal is to make each boundary visible, minimized, and accountable.

---

## 9. Hardware and capability model

JETOS should not install a generic desktop stack onto every machine.

It should discover or declare capabilities such as:

- display;
- touch;
- keyboard;
- pointer;
- speakers;
- microphone;
- camera;
- Ethernet;
- Wi-Fi;
- Bluetooth;
- cellular;
- battery;
- sensors;
- GPU;
- storage;
- virtualization.

JETOS should distinguish:

1. capability exists;
2. an implementation is installed;
3. policy permits it;
4. it is currently active.

Having hardware does not automatically mean JETOS must enable it.

A headless device need not receive a GUI or audio stack. A tablet may require both.

Initial discovery sources can include Linux sysfs/procfs, ACPI, Device Tree, PCI, USB, netlink, and uevents.

---

## 10. Architectures

Initial architecture targets:

- x86-64;
- AArch64 / ARM64.

The intention is one JETOS API and behavior model with separate native builds.

Architecture-specific C/assembly should remain isolated.

RISC-V64 may be added later. Initial 32-bit support is not a goal.

ISA support does not automatically imply support for every device using that ISA.

---

## 11. Networking model

JETOS is intended to have one user-visible master networking switch.

Desired states include:

- ON;
- OFF_VERIFIED;
- OFF_SOFTWARE_ENFORCED;
- OFF_UNVERIFIED;
- ERROR.

When networking is OFF, JETOS should prevent ordinary external communication by:

- blocking new external sockets where practical;
- terminating or isolating existing external connections;
- disabling interfaces/routes;
- enforcing ingress/egress firewall policy;
- disabling controllable radios with rfkill or device-specific mechanisms;
- covering bridges, veth devices, and containers;
- preventing ordinary applications from reversing the state.

Loopback and local Unix-domain IPC may remain available.

The system must report the strength of the guarantee rather than claiming a hardware radio state it cannot actually verify.

This is architecture today, not implemented code.

---

## 12. Filesystem and introspection model

A normal JETOS build should eventually generate an authoritative manifest for every installed file.

Desired metadata includes:

- absolute path;
- file type;
- byte size;
- cryptographic hash;
- ownership;
- upstream project/version;
- source/build provenance;
- license;
- target architecture;
- JETOS-owned vs imported classification;
- source language;
- build rule;
- capability/device reason for inclusion.

JETOS should be able to trace:

```text
source -> build rule -> artifact -> installed file -> image
```

Unknown or unclassified OS files are defects.

Planned inspection surfaces include concepts equivalent to:

```text
files
file <path>
components
source
languages
exceptions
hardware
capabilities
kernel
network
build
```

---

## 13. Runtime composition

The initial runtime substrate is Linux.

A minimal deployed JETOS image is expected to contain some combination of:

- Linux kernel;
- required modules;
- required firmware;
- boot files;
- C runtime / loader;
- CPython + required standard library;
- JETOS bootstrap/supervisor;
- storage/filesystem support;
- hardware/network capability implementation required by the target;
- certificate roots when TLS is enabled;
- recovery/logging support;
- container primitives when requested.

Development environments may additionally contain:

- compilers;
- linkers;
- headers;
- Portage;
- Bash;
- SSH;
- debuggers;
- Docker;
- source trees.

Development and deployment are intentionally different.

---

## 14. Containers

JETOS eventually intends to expose Linux isolation facilities such as:

- namespaces;
- cgroup v2;
- capabilities;
- seccomp;
- OverlayFS;
- veth networking.

Docker is currently a development and compatibility tool, not the permanent JETOS runtime architecture.

A future JETOS-native container controller can be Python-first with explicit native boundaries.

---

## 15. Security and recovery

Long-term requirements include:

- least privilege;
- applications unable to reverse system networking policy;
- explicit capability grants;
- recovery boot path;
- alternate-slot or external-reflash strategy where appropriate;
- verified provenance;
- signing/update design before production deployment.

The final update mechanism—image-based, atomic, package-based, or hybrid—is intentionally undecided.

---

## 16. Docker development image

Docker currently provides the fastest way to exercise the JETOS userspace and tests.

Build:

```bash
git clone https://github.com/Johnetordoff/JETOS.git
cd JETOS
docker build -t jetos:dev .
```

Run:

```bash
docker run --rm -it jetos:dev
```

The Docker build runs:

```bash
python tools/test.py
python tools/test_unicode.py
```

The image sets:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
```

Docker supplies the host Linux kernel. Therefore a successful Docker run proves JETOS userspace behavior, **not JETOS boot ownership**.

---

## 17. Hypervisor / VM milestone

The next major integration target is:

```text
physical computer
        ↓
hardware virtualization / hypervisor
        ↓
virtual firmware
        ↓
JETOS-selected Linux kernel
        ↓
JETOS root filesystem
        ↓
JETOS PID 1 / early bootstrap
        ↓
CPython
        ↓
JETOS Python control plane
        ↓
JETOS console
```

A successful first VM should contain only enough to prove boot ownership:

- kernel;
- boot path;
- root filesystem/initramfs;
- C runtime;
- CPython;
- JETOS modules;
- JETOS native C pieces;
- console;
- virtual disk;
- minimal hardware discovery;
- Dunicode/Unicode tests;
- explicit networking state.

A first console might eventually report:

```text
JETOS 0.1
John E Tordoff's Operating System

architecture: aarch64
kernel: Linux ...
python: 3.x
Dunicode: 0.1
Unicode: supported
encoding: UTF-8
network: OFF
filesystem: mounted

jetos>
```

Potential console capabilities:

```text
hardware
files
languages
exceptions
dunicode
unicode
test
network status
python
reboot
poweroff
```

The exact spelling/UI is not frozen.

Preferred host acceleration includes hardware-assisted virtualization such as HVF/Hypervisor.framework on Apple Silicon, KVM on Linux, or equivalent supported accelerators on other hosts.

> Docker proves JETOS userspace.  
> A hypervisor proves JETOS boot ownership.

---

## 18. Optimization doctrine

JETOS treats measurable unnecessary work as legitimate optimization territory even when the saving is small, provided correctness, security, inspectability, and maintainability remain acceptable.

Useful measurements include:

- boot processes;
- forks/execs;
- subprocesses;
- filesystem reads;
- metadata parsing;
- dependency computations;
- Python interpreter startups/imports;
- syscalls;
- IPC;
- context switches;
- allocations;
- bytes read/written;
- network round trips.

Candidates include persistent Python orchestration, cached metadata, target-specific kernel/module sets, omitted services/tools, resident supervisors, and precompiled Python bytecode.

Measure before and after.

---

## 19. Repository rules

Git is the history format. Hosting is replaceable.

JETOS must not architecturally depend on GitHub.

A bare Git repository, a self-hosted Git service, or another Git-compatible remote can be authoritative.

JETOS-owned hooks should be Python.

Future repository validation should check:

- language policy;
- native-source exception registration;
- provenance;
- generated-manifest freshness;
- secrets;
- forbidden/unclassified binaries;
- protected metadata.

Build-time validation remains authoritative even when hooks exist.

---

## 20. Testing philosophy

System tests eventually define the OS as much as the source does.

Where a capability is advertised on x86-64 and AArch64, behavior-level tests should agree.

Image tests should assert both presence and absence.

Examples:

- Python is present;
- required storage/filesystem support is present;
- requested network support is present;
- GUI is absent on headless targets;
- audio is absent when not requested;
- Bluetooth is absent when not requested;
- compiler is absent from production unless deliberately included;
- every native exception is registered;
- every installed file is classified;
- Dunicode/Unicode round trips pass;
- the generated manifest matches the actual filesystem.

Virtual machines are essential, but selected cheap replaceable physical test hardware should eventually be part of the matrix.

---

## 21. Current repository layout

The intentionally small source tree contains:

```text
Dockerfile
src/jetos/
    __init__.py
    hardware.py
    dunicode.py
tools/
    test.py
    test_unicode.py
ports/gcc/ordered_hash_map_c/
    ordered_hash_map.c
    ordered_hash_map.h
    test_ordered_hash_map.c
README.md
.gitignore
.dockerignore
```

There is deliberately only **one Markdown architecture/documentation file: this README**.

---

## 22. Current test commands

Repository tests:

```bash
python tools/test.py
python tools/test_unicode.py
```

The C test driver compiles with strict C11 warnings-as-errors and repeats under sanitizers.

The Dunicode/Unicode test driver covers:

- ASCII;
- Latin + diacritics;
- Greek;
- Cyrillic;
- Arabic;
- Hebrew;
- Devanagari;
- CJK;
- emoji;
- supplementary-plane characters;
- combining sequences;
- variation selectors;
- zero-width characters;
- strict malformed UTF-8 rejection;
- Unicode filenames;
- arbitrary POSIX filename bytes where supported;
- Dunicode scalar conversion;
- Dunicode `D+...` labels;
- rejection of surrogate and out-of-range Dunicode scalars;
- preservation rather than silent normalization.

---

## 23. Near-term build order

1. Keep Docker tests green.
2. Keep the source tree small and language-classified.
3. Expand Dunicode only through reversible tested behavior.
4. Inventory the minimal Linux kernel features required by CPython + JETOS.
5. Create one VM kernel configuration.
6. Build the smallest root filesystem capable of starting CPython.
7. Implement JETOS early bootstrap / PID 1 in Python with the necessary native handoff.
8. Produce a bootable initramfs/disk artifact.
9. Boot under a hardware-assisted hypervisor.
10. Reach a JETOS console.
11. Run the JETOS tests inside the VM.
12. Implement and verify networking OFF.
13. Repeat for the second architecture.
14. Begin replacing larger imported C++/Bash dependencies only after the boot/test path is reproducible.

---

## 24. Canonical shorthand

> No mysterious files.  
> No mysterious build steps.  
> No mysterious languages.

> Python for JETOS logic.  
> C for native implementation.  
> Assembly only where architecture demands it.  
> Bash may be a shell, not the JETOS control language.  
> C++ is migration debt.

> Imported badness is quarantined.  
> Released dependencies are fixed.  
> Every exception is enumerable.  
> Every translated source remains readable.

> Discover the machine.  
> Declare its role.  
> Bootstrap only what it needs.

> Dunicode is JETOS-native.  
> Unicode is interoperable.  
> UTF-8 is the normal byte representation.  
> Raw bytes remain raw bytes.

> Gentoo is upstream source infrastructure, not JETOS's identity.

> Git is history. Hosting is optional.

> Docker proves JETOS userspace.  
> A hypervisor proves JETOS boot ownership.
