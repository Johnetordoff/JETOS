# ODROID-HC1 Gen 2 target

Status: **current physical-hardware priority**

JetOS is being developed to **run on the ODROID-HC1 (Home Cloud One)** as a real, bootable operating-system environment. The HC1 is not a hypothetical compatibility target: it is the board JetOS should work on now while the project develops its first physical-machine path.

The HC1 uses the Samsung Exynos 5422 platform and a 32-bit ARMv7 userspace/kernel target. JetOS canonicalizes this CPU target as `armv7`.

## What “Gen 2” means

**Gen 2 means the Linux-backed JetOS configuration. It does not mean “second generation.”**

In Gen 2:

- Linux remains the imported native kernel and hardware substrate;
- JetOS owns the Python-first early userspace, control plane, policy, capability model, image/build logic, and user-facing behavior above that substrate;
- project-owned executable logic remains Python/JetLang-first under `MANDATE.md`;
- the Linux/board/native boundary must stay explicit rather than being disguised as Python.

The HC1 is the current reference machine for proving that Gen 2 can operate on constrained real hardware.

## Python standard-library requirement

A qualified HC1 Gen 2 image must provide the **complete CPython standard-library surface supported for the selected CPython release on Linux**, including standard-library modules implemented through normal CPython extension modules when they are part of that Linux build.

Qualification must be systematic rather than anecdotal:

1. enumerate the standard-library modules expected for the selected CPython/Linux build;
2. import/smoke-test them on the target image;
3. exercise modules that require real operating-system facilities where practical;
4. record every unavailable module and the exact reason;
5. treat an optional extension that can reasonably be built for the HC1 as work to complete, not as permission to silently omit it.

Modules that CPython itself defines as platform-specific to a different operating system are not required merely to satisfy the word “entire.” Any other exception must be explicit and justified.

## First HC1 boot goal

The first useful physical milestone is:

**microSD → HC1 bootloader → Linux kernel + correct device tree → JetOS early userspace → JetLang/JetOS console**

The existing attached SATA hard drive is **not the boot-development scratch disk by default**. Initial JetOS bring-up should use a dedicated microSD card and preserve existing SATA data unless the owner explicitly authorizes modifying it.

After the first console boot, the priority order is reliable repeated boot, target-native JetLang and standard-library qualification, Ethernet/link, DHCP/routing/DNS, headless remote administration, safe SATA discovery without destructive probing, hardware capability reporting, and reproducible image construction/flashing.

The HC1 does not need a desktop GUI to qualify.

## Board-specific work belongs at the boundary

HC1 support may require board-specific bootloader configuration, kernel configuration/image layout, Exynos 5422 support, device tree, Ethernet, SATA behavior, thermal/power handling, and microSD layout. These details remain isolated from shared JetOS behavior rather than forking the operating system.

## Relationship to x86-64 and ARM64

JetOS recognizes `x86_64`, `armv7`, and `arm64`; the HC1 is the current physical `armv7` reference board. Shared Python/JetLang behavior should remain the same wherever equivalent facilities exist.

## Raspberry Pi delegation

Raspberry Pi systems may act as optional delegate nodes. The HC1 must remain independently bootable/qualifiable; delegates use explicit authenticated interfaces and capability-driven responsibilities; failure must degrade cleanly; privileged/destructive work remains explicitly authorized; and shared JetOS logic is reused rather than reimplemented.

## Definition of “working on the HC1”

Initial HC1 qualification requires JetOS to boot from a dedicated physical image, enter its JetLang control environment reliably, identify the `armv7`/HC1 target, pass the Linux standard-library qualification with documented exceptions only, bring up Ethernet/IP/DNS, discover attached SATA without destructive modification, and preserve the same JetOS-facing language architecture used by the other supported CPU targets.
