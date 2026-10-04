# JETOS — John E Tordoff's Operating System

JETOS is a source-oriented, Python-first operating-system project whose long-term goal is to replace the software stack on a target machine rather than merely run as an application inside another operating system.

**Project state:** early bootstrap with a clone-to-build development environment, an editable JETOS language fork, Python-built root filesystem/initramfs, and a working language-shell dry run.

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
| Editable language fork tooling | Implemented | Python can create, patch, build, install, and smoke-test a pinned CPython-derived JETOS language source tree |
| Hardware snapshot | Implemented, minimal | Reports architecture, CPU count, sysfs, Device Tree, and ACPI presence |
| Native C boundary | Implemented, experimental | First readable C replacement experiment based on a GCC C++ utility |
| Strict C tests | Implemented | C11, warnings-as-errors, pedantic build |
| Sanitizer tests | Implemented | AddressSanitizer + UndefinedBehaviorSanitizer run for the C experiment |
| Dunicode | Implemented, v0.2 | Unicode-compatible scalar layer plus reversible character retirement/removal policy |
| Unicode / UTF-8 | Implemented, smoke-tested | Strict UTF-8 round trips, multilingual text, emoji, combining characters, invalid UTF-8 rejection, filesystem cases |
| Docker test image | Implemented | Reproducible userspace/test container |\n| Portable development environment | Implemented | `python jetos.py dev` builds the development container, pinned language/kernel sources, rootfs/initramfs, and launches QEMU |\n| Host setup tooling | Implemented | Python can plan/install prerequisites on macOS, common Linux distributions, and Windows |\n| Repository text export | Implemented | `python jetos.py text` prints every tracked UTF-8 JETOS source/spec file |
| Python rootfs builder | Implemented | CPython assembles the root filesystem and native runtime dependencies |
| Python initramfs writer | Implemented | CPython writes the newc CPIO archive and deterministic gzip stream |
| First CPython-shell dry run | Passed | Assembled rootfs enters a `jetos>` CPython interpreter |
| Hypervisor boot | Tooling implemented, execution pending | Python QEMU launcher exists; this environment has no QEMU binary |
| JETOS kernel profile | Implemented for first x86-64 boot | Python validates and patches boot-critical Linux Kconfig values |
| JETOS kernel build orchestration | Implemented | Python drives imported Linux Kbuild and produces `bzImage` |
| JETOS PID 1 | Implemented, VM proof pending | `/init` is Python and execs CPython so the interpreter remains PID 1 |
| JETOS interactive console | Implemented in dry run | The first shell is CPython itself, with `jetos>` prompt and Dunicode preloaded |
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

The stronger rule is:

> **If it can be done correctly in CPython, JETOS does it in CPython.**

That includes the OS shell, root-filesystem assembly, initramfs construction, early userspace/bootstrap, kernel configuration and build orchestration, services, package orchestration, tests, developer tooling, image construction, and administration.

1. **CPython first, every time it is technically available.**
2. **C** only where CPython cannot execute or cannot correctly provide the required native boundary.
3. **Assembly** only where the architecture itself requires it.
4. Every non-Python JETOS-owned executable source file must be explainable and reviewable.

CPython is not merely a favored application language in JETOS. It is intended to be the operating system's normal control language and interactive shell. JETOS may eventually carry its own CPython fork, but the architectural rule is already the same: Python is the default implementation environment, not an add-on.

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

> If CPython can do it correctly, CPython does it.  
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

### 5.2 Dunicode v0.2

Dunicode is the JETOS-native character layer.

Dunicode keeps Unicode interoperability while allowing the active encoding convention to become smaller or stricter over time.

Version 0.2 rules:

- every Dunicode character maps **1:1** to a valid Unicode scalar value;
- a Dunicode scalar may be displayed as `D+XXXX` or `D+XXXXX`;
- Dunicode text serializes to ordinary strict UTF-8;
- converting Unicode → Dunicode → Unicode is lossless;
- a current Dunicode encoder may **retire/remove a scalar from new canonical encoding**;
- historical bytes containing a retired scalar still decode to the same original scalar;
- retirement never silently reassigns the scalar to a different meaning or presentation;
- character identity and rendering/presentation policy are separate;
- Dunicode does not silently normalize text;
- surrogate code points are invalid;
- malformed UTF-8 is rejected rather than silently repaired.

That removal rule is important: Dunicode can stop emitting a character in a newer convention without corrupting old data and without pretending the old character has become a different character.

Examples:

```text
Unicode U+0041  <->  Dunicode D+0041   A
Unicode U+00E9  <->  Dunicode D+00E9   é
Unicode U+6F22  <->  Dunicode D+6F22   漢
Unicode U+1F9EA <->  Dunicode D+1F9EA  🧪
```

This gives JETOS its own explicit text abstraction without sacrificing compatibility with the existing Unicode world.

Future Dunicode versions may add more registry/policy behavior, but historical decoding must remain reversible. Dunicode v0.2 does **not** claim that its UTF-8 bytes are magically shorter than UTF-8; the intended compactness is that JETOS can maintain a smaller active repertoire/implementation without carrying every Unicode policy decision as immutable active convention.

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

There is one unavoidable bootstrapping fact: ordinary CPython cannot run *inside* the Linux kernel before the kernel exists, because CPython itself depends on kernel facilities such as virtual memory, processes, files, and system calls. Therefore the initial Linux kernel remains imported native C/assembly substrate. JETOS still owns its **kernel selection, required feature profile, configuration patching, build orchestration, image selection, and boot orchestration in Python**. Any kernel-adjacent job that can move out of native kernel space into CPython should do so.

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
python tools/test_language.py
```

The image sets:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
```

Docker supplies the host Linux kernel. Therefore a successful Docker run proves JETOS userspace behavior, **not JETOS boot ownership**.

---

## 17. Python-first boot path and hypervisor milestone

JETOS now has Python-owned targets for:

```text
python tools/build.py rootfs
python tools/build.py initramfs
python tools/build.py kernel-check <linux .config>
python tools/build.py kernel <linux-source-tree>
python tools/build.py dry-run
python tools/build.py vm --kernel <bzImage>
```

The rootfs target copies the selected CPython runtime, standard library, native loader/library dependencies, and JETOS Python source. The initramfs target writes the kernel's newc CPIO format directly in Python and gzip-compresses it deterministically. No JETOS-owned shell script, Makefile, BusyBox init, or systemd is part of this first boot path.

The kernel target is also Python-owned orchestration. Linux's Kbuild/`make` remains an imported native build dependency for the imported Linux kernel itself; JETOS's policy/configuration logic is Python.

The next integration boundary is the hypervisor boot.

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
Dunicode: 0.2
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

## 21. First dry run

The first root-filesystem dry run has been executed successfully. It used the same assembled CPython runtime that the initramfs contains, entered it with `chroot`, and opened CPython as the JETOS shell:

```text
CPython is JETOS's first shell. `dunicode` is preloaded.
FIRST JETOS DRY RUN
D+1F9EA
42
Python 3.13.5 ... on linux
jetos>
```

Measured artifact sizes from that run:

- assembled root filesystem: **81,948,873 bytes**;
- regular files in assembled root filesystem: **1,344**;
- gzip initramfs: **28,231,806 bytes**.

An installed Debian Linux 6.12 x86-64 kernel configuration also passed the JETOS first-boot profile, including ELF/script execution, initramfs+gzip, devtmpfs, serial console, procfs, sysfs, tmpfs, and Unix sockets. Virtio PCI/block/network and ext4 were present as built-in or modules.

This proves the Python-built filesystem and CPython-first shell path. It does **not yet prove a full kernel/QEMU boot**; the execution environment used for this work does not contain QEMU and cannot download it. The `vm` target is ready for a host that has `qemu-system-x86_64`.

---

## 22. Current repository layout

The intentionally small source tree contains:

```text
Dockerfile
src/jetos/
    __init__.py
    hardware.py
    dunicode.py
    init.py
    startup.py
tools/
    build.py
    language.py
    test.py
    test_language.py
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

## 23. Current test commands

Repository tests and first-boot targets:

```bash
python tools/test.py
python tools/test_unicode.py
python tools/build.py rootfs
python tools/build.py initramfs
python tools/build.py kernel-check /path/to/linux/.config
python tools/build.py kernel /path/to/linux-source
python tools/build.py dry-run
python tools/build.py vm --kernel /path/to/bzImage
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
- preservation rather than silent normalization;
- Dunicode removal/retirement from new encoding while historical decoding remains stable.

---

## 24. Near-term build order

Completed in this PR stack:

1. define the first x86-64 kernel feature profile;
2. build the root filesystem in Python;
3. implement Python early bootstrap;
4. make CPython the first JETOS shell;
5. write the initramfs/CPIO archive in Python;
6. validate a real Linux kernel config against the JETOS profile;
7. execute the assembled rootfs and reach `jetos>`.

Next:

1. run the initramfs with a real kernel under QEMU/HVF/KVM;
2. confirm CPython is actually PID 1 in the VM;
3. mount procfs/sysfs/devtmpfs from Python;
4. add Python poweroff/reboot handling;
5. make the kernel build reproducible from a pinned upstream source revision;
6. minimize the imported CPython/rootfs byte footprint;
7. implement and verify networking OFF;
8. reproduce the boot on AArch64;
9. begin larger C++/Bash elimination only after the boot path is reproducible.

---

## 25. Canonical shorthand

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


---

## 26. Editable JETOS language fork

CPython is no longer treated as an untouchable runtime dependency.

JETOS treats the interpreter, parser, compiler pipeline, bytecode machinery, object model, garbage collector, standard library, and runtime as source that the project may fork and change. Compatibility with Python is useful during bootstrap, but it is not a permanent constitutional requirement. If JETOS evolves far enough, this becomes a distinct programming language descended from CPython rather than "Python with some OS scripts."

The currently pinned upstream ancestor is:

```text
repository: https://github.com/python/cpython.git
commit: 9d22a5334bd5273962adceeb697a1337e9a0ca21
upstream branch at selection time: main
upstream language version at that commit: 3.16.0a0
```

JETOS owns `tools/language.py`, which can create a local editable Git fork from that exact ancestor:

```bash
python tools/language.py fork ../jetos-language
```

That command:

1. clones upstream CPython;
2. checks out the exact pinned ancestor;
3. creates a `jetos-language` Git branch;
4. adds `Include/jetos.h`;
5. changes the interpreter implementation identity from `cpython` to `jetos`;
6. gives the runtime a JETOS-specific bytecode cache tag through `sys.implementation`;
7. adds `sys.jetos_language_version`;
8. commits the initial fork mutation locally.

The fork is then normal source code. Nothing about the parser, compiler, VM, Unicode implementation, object representation, garbage collector, import system, or standard library is considered sacred.

Build it using Python-owned orchestration:

```bash
python tools/language.py build ../jetos-language \
    --build .build/jetos-language \
    --prefix .build/jetos-language-install

python tools/language.py smoke --build .build/jetos-language
python tools/language.py install --build .build/jetos-language
```

The smoke test requires the **interpreter itself** to report:

```text
sys.implementation.name == "jetos"
sys.jetos_language_version == "0.1"
```

Because the implementation name changes, its normal bytecode cache tag becomes JETOS-specific rather than pretending to be ordinary CPython.

The installed fork can then be supplied to the JETOS root-filesystem builder:

```bash
python tools/build.py rootfs \
    --python .build/jetos-language-install/bin/python3.16 \
    --stdlib .build/jetos-language-install/lib/python3.16
```

### Bootstrap build machinery

The upstream CPython `configure` script and Makefile are temporarily imported bootstrap machinery. JETOS does not claim those files are Python. JETOS's decisions and orchestration are Python-owned; replacing upstream shell/make build machinery is a later migration task.

The same rule applies to the native compiler toolchain. GCC/other compiler source is not a sealed external appliance. It is an editable source dependency. JETOS's long-term direction remains to remove required C++ from its trusted toolchain and make the native compiler path source-visible, reproducible, and editable.

### Online fork status

The connected GitHub interface available during this bootstrap can write to existing repositories but does not expose GitHub's repository-fork/create operation. Therefore this PR creates the **reproducible editable source-fork mechanism** and pins the exact ancestor, but it does not falsely claim that a separate `Johnetordoff/cpython` GitHub repository has already been created.

Once such a repository exists, the local `jetos-language` branch is ordinary Git and can be pushed to it without changing the JETOS architecture.

### Canonical rule

> The language implementation is part of the operating system.

> If the language needs to change for JETOS, change the language.

> No compiler, interpreter, parser, runtime, standard library, or build tool is considered uneditable merely because it came from upstream.


---

## 27. Clone-to-boot development environment

The JETOS repository is intended to be sufficient as the human-editable project entry point.

The repository contains the JETOS-authored text: Python control logic, readable C experiments, Docker development recipe, Git configuration, and this single canonical architecture/specification document. Large imported upstream source trees and generated binaries are **not** checked into JETOS merely to make the repository self-contained. Instead, their exact source identities are pinned and JETOS can reconstruct them into `.build/`.

Pinned native/source inputs for the current development boot are:

```text
Linux stable repository: https://github.com/gregkh/linux.git
Linux version: 6.12.96
Linux commit: 6d15a1029d425b15c59463910ebdccc4afe760d6

CPython ancestor repository: https://github.com/python/cpython.git
CPython ancestor commit: 9d22a5334bd5273962adceeb697a1337e9a0ca21
JETOS language branch: jetos-language
```

### One-command path

After cloning JETOS:

```bash
git clone https://github.com/Johnetordoff/JETOS.git
cd JETOS
python jetos.py doctor
python jetos.py dev
```

`python jetos.py dev` uses Docker by default so the build environment is Linux even when the host is macOS or Windows. The sequence is:

```text
JETOS checkout
    ↓
Docker development environment
    ↓
pinned CPython ancestor
    ↓
JETOS language source fork
    ↓
JETOS language compiler/runtime build
    ↓
pinned Linux stable source
    ↓
JETOS Python kernel configuration/build orchestration
    ↓
JETOS Python rootfs + initramfs generation
    ↓
QEMU virtual machine
    ↓
JETOS-selected Linux kernel
    ↓
Python /init as PID 1
    ↓
JETOS language interpreter
    ↓
jetos>
```

The QEMU guest is launched with **no virtual NIC** in this first configuration. Its reported networking-OFF state therefore corresponds to the virtual hardware actually presented to the guest.

On Linux, the same work can be run without Docker:

```bash
python jetos.py dev --native
```

If `/dev/kvm` is available, the launcher uses KVM. Otherwise QEMU uses TCG software virtualization/emulation. macOS and Windows use the Docker-hosted Linux builder and portable QEMU/TCG path by default.

### Host prerequisite installation

JETOS has host setup tooling rather than requiring a handwritten setup document.

Inspect the host:

```bash
python jetos.py doctor
```

Show the proposed installation commands without executing them:

```bash
python jetos.py setup --plan
```

Execute the supported package-manager plan:

```bash
python jetos.py setup --install --yes
```

Current host families:

- **macOS:** Homebrew-based Git/QEMU setup plus Docker Desktop;
- **Linux:** apt, dnf, pacman, and zypper families, including native compiler/kernel-build dependencies, QEMU, and Docker;
- **Windows:** winget-based Git and Docker Desktop setup; JETOS itself builds in the Linux development container.

This is deliberately a **development/VM installation tool**, not a physical-disk eraser. Bare-metal installation should not be enabled until the guest boot, storage, recovery, and hardware-support paths are proven.

### All JETOS text

To inspect the entire tracked UTF-8 textual repository in one stream:

```bash
python jetos.py text
```

That command asks Git for the tracked file list and prints every UTF-8 text file with a filename boundary. Generated root filesystems, kernels, compiled interpreters, and imported source checkouts live under `.build/` and remain reproducible rather than being mistaken for JETOS-authored source.

### x86-64 and ARM64

The first-boot kernel policy and QEMU launcher now understand both:

- x86-64, using the 8250 serial console and `bzImage`;
- ARM64/AArch64, using the PL011 serial console and the kernel `Image`.

This is important for development portability: an Intel/AMD Linux or Windows development environment can build and run the x86-64 path, while an Apple Silicon/Linux ARM64 development environment can build and run the ARM64 path without forcing JETOS itself to become architecture-specific above the native boundary.

### Python PID 1 and hardware-facing filesystems

The generated `/init` no longer depends on a dry-run-provided `PYTHONPATH`; it explicitly locates `/jetos/src` itself.

The Python PID-1 code invokes Linux's `mount(2)` interface through `ctypes` and mounts:

- `devtmpfs` on `/dev`;
- `proc` on `/proc`;
- `sysfs` on `/sys`.

That gives JETOS's Python layer access to the kernel's hardware/process/device view without invoking an external `mount` command or a shell script.

### Development bootstrap boundary

The first complete build still contains imported bootstrap machinery:

- Linux Kbuild/make;
- CPython's configure/make build system;
- GCC/C compiler and native binutils;
- libc/dynamic loader;
- QEMU.

These are not declared permanent. They are explicitly the current substrate from which JETOS can iteratively remove, rewrite, or replace dependencies. JETOS-owned orchestration remains Python.

### Current verification

The new fast bootstrap test verifies without compiling a kernel that:

- AMD64/x86-64 and ARM64 architecture names normalize correctly;
- the correct architecture-specific serial-console kernel requirements are selected;
- JETOS's Python newc CPIO writer emits the expected format;
- generated `/init` is a Python entry point;
- generated `/init` locates the JETOS Python package without inherited host state.

Current local result:

```text
JETOS bootstrap tooling: 12 checks passed
```

The full kernel + QEMU boot still needs to be executed on a development host with Docker/QEMU available; this execution environment cannot install/run QEMU itself. The repository now contains the complete path needed to perform that test rather than merely describing it.
