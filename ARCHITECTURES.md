# JetOS architecture contract

JetOS has two first-class CPU architecture targets:

- `x86_64` — the 64-bit x86 architecture used by modern AMD/Intel-compatible systems;
- `arm64` — AArch64/ARM64, the 64-bit ARM architecture used by many single-board computers and other systems.

These are two machine instruction-set targets for **one JetOS**, not two operating systems and not two independently evolving ports.

## One OS above the machine boundary

JetOS-owned behavior should be architecture-neutral by default. The same Python control plane, policy, capability model, package/image logic, provenance model, tests, user-facing behavior, and system concepts should run on both architectures wherever the underlying hardware exposes equivalent capabilities.

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

JetOS canonicalizes common aliases to exactly two names:

| Input family | JetOS canonical target |
| --- | --- |
| `x86_64`, `amd64` | `x86_64` |
| `aarch64`, `arm64` | `arm64` |

New code should use the canonical names internally.

## Build rule

A complete JetOS image must contain a kernel **and userspace built for the same target architecture**.

The existing kernel and VM tooling can select either target. The current rootfs builder, however, copies the CPython interpreter and native shared libraries from the build environment. Therefore, until explicit cross-userspace construction exists, rootfs/initramfs assembly must run on a matching target architecture (directly or inside a matching VM/container/build environment), or be supplied with a verified target-native CPython/runtime source path.

JetOS must fail or refuse qualification rather than knowingly combine an `arm64` kernel with an `x86_64` userspace, or the reverse.

Cross-compilation/cross-building may be added later, but it must remain Python-orchestrated, explicit, provenance-accounted, reproducible, and must not create a second dependency-heavy build architecture.

## Qualification rule

Neither architecture is secondary. A change to shared JetOS logic is architecturally complete only when it preserves both targets unless the change is explicitly and correctly confined to one architecture-specific boundary.

Fast repository tests must continuously verify at least:

- alias normalization for both architecture families;
- architecture-specific first-boot kernel requirements;
- architecture-specific kernel image paths;
- architecture-specific QEMU executable/console selection;
- rejection of unsupported architectures.

Physical-board support is a separate device-profile layer on top of the CPU architecture. Supporting `arm64` does not automatically mean every ARM64 board is bootable; firmware, device trees, peripherals, and boot media still require device-specific work. The same applies to x86-64 hardware-specific capabilities.

## Non-goal

JetOS does not attempt to support every historical CPU architecture merely because Linux can. The current architectural contract is deliberately narrow: **x86-64 + ARM64/AArch64**. Additional architectures require an explicit Developer One decision rather than accidental expansion.
