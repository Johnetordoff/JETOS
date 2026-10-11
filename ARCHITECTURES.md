# JetOS architecture contract

JetOS has three first-class CPU architecture targets:

- `x86_64` — the 64-bit x86 architecture used by modern AMD/Intel-compatible systems;
- `armv7` — 32-bit ARMv7, including the Samsung Exynos 5422 platform used by the ODROID-HC1;
- `arm64` — AArch64/ARM64, the 64-bit ARM architecture used by many single-board computers and other systems.

These are machine instruction-set targets for **one JetOS**, not separate operating systems and not independently evolving ports.

## Current physical reference target

The current physical-hardware priority is the **ODROID-HC1 (Home Cloud One)**. JetOS must be able to boot and operate on this board as a real ARMv7 machine, not merely emulate a generic ARM target.

The HC1 therefore drives near-term work on:

- ARMv7 Linux kernel selection/configuration;
- the HC1 bootloader and boot-media path;
- Exynos 5422 device-tree and board support;
- headless console/early userspace;
- Ethernet networking;
- attached SATA storage discovery and safe use;
- a target-native CPython runtime and Linux-appropriate Python standard library qualification.

Physical HC1 support is a concrete board target layered on top of the `armv7` CPU target. Supporting generic ARMv7 does not by itself mean the HC1 is qualified; the board-specific boot, device-tree, network, and storage path must work on the actual hardware.

## One OS above the machine boundary

JetOS-owned behavior should be architecture-neutral by default. The same Python control plane, policy, capability model, package/image logic, provenance model, tests, user-facing behavior, and system concepts should run on all supported architectures wherever the underlying hardware exposes equivalent capabilities.

Architecture-specific implementation is permitted only where the machine boundary genuinely requires it, including:

- Linux architecture selection and kernel configuration;
- kernel image format/path;
- firmware/bootloader handoff;
- device tree, ACPI, or architecture-specific hardware discovery;
- interrupt/MMU/CPU entry details in imported native substrate;
- architecture-required C or assembly;
- QEMU machine/console details;
- board/device profiles where hardware differs.

Architecture-specific C/assembly must remain isolated and must not leak upward into duplicate JetOS control stacks.

## Canonical names

JetOS canonicalizes common aliases to these names:

| Input family | JetOS canonical target |
| --- | --- |
| `x86_64`, `amd64` | `x86_64` |
| `armv7`, `armv7l`, 32-bit ARMv7 | `armv7` |
| `aarch64`, `arm64` | `arm64` |

New code should use the canonical names internally.

## Build rule

A complete JetOS image must contain a kernel **and userspace built for the same target architecture**.

The existing kernel and VM tooling can select supported targets. The current rootfs builder, however, copies the CPython interpreter and native shared libraries from the build environment. Therefore, until explicit cross-userspace construction exists, rootfs/initramfs assembly must run on a matching target architecture (directly or inside a matching VM/container/build environment), or be supplied with a verified target-native CPython/runtime source path.

JetOS must fail or refuse qualification rather than knowingly combine an `armv7`, `arm64`, or `x86_64` kernel with userspace for a different architecture.

Cross-compilation/cross-building may be added later, but it must remain Python-orchestrated, explicit, provenance-accounted, reproducible, and must not create a second dependency-heavy build architecture.

## Qualification rule

No first-class architecture is a compatibility afterthought. A change to shared JetOS logic is architecturally complete only when it preserves the supported targets unless the change is explicitly and correctly confined to one architecture-specific boundary.

Fast repository tests must continuously verify at least:

- alias normalization for supported architecture families;
- architecture-specific first-boot kernel requirements;
- architecture-specific kernel image paths;
- architecture-specific QEMU executable/console selection where QEMU support exists;
- rejection of unsupported architectures.

Physical-board qualification is a separate device-profile layer on top of CPU architecture. The ODROID-HC1 is the current board-level priority. Raspberry Pi boards may be added as additional ARM board profiles and can later act as JetOS delegate nodes; their exact CPU target depends on the model and selected userspace.

## Gen 2 relationship

The current ODROID-HC1 goal uses the JetOS **Gen 2** configuration. In JetOS terminology, **Gen 2 means the Linux-backed configuration; it does not mean “second generation.”**

Gen 2 keeps Linux as the imported native kernel/substrate while JetOS owns the Python-first userspace/control plane above it. On the HC1, Gen 2 qualification includes a target-native CPython runtime and the complete Python standard-library surface that CPython supports on Linux for this build, subject only to modules that CPython itself defines as unavailable on Linux or a documented unavoidable hardware/build limitation.

The detailed HC1 and Gen 2 acceptance criteria live in `ODROID_HC1_TARGET.md`.

## Non-goal

JetOS does not attempt to support every historical CPU architecture merely because Linux can. The current architectural contract is deliberately narrow: **x86-64 + ARMv7 + ARM64/AArch64**. Additional architectures require an explicit Developer One decision rather than accidental expansion.
