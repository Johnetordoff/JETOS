# ODROID-HC1 Gen 2 target

Status: **current physical-hardware priority**

JetOS is being developed to **run on the ODROID-HC1 (Home Cloud One)** as a real, bootable operating-system environment. The HC1 is not a hypothetical compatibility target: it is the board JetOS should work on now while the project develops its first physical-machine path.

The HC1 uses the Samsung Exynos 5422 platform and a 32-bit ARMv7 userspace/kernel target. JetOS canonicalizes this CPU target as `armv7`.

## What “Gen 2” means

**Gen 2 means the Linux-backed JetOS configuration. It does not mean “second generation.”**

In Gen 2:

- Linux remains the imported native kernel and hardware substrate;
- JetOS owns the Python-first early userspace, control plane, policy, capability model, image/build logic, and user-facing behavior above that substrate;
- project-owned executable logic remains CPython-first under `MANDATE_004.md`;
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

Modules that CPython itself defines as platform-specific to a different operating system are not required merely to satisfy the word “entire.” For example, Windows-only modules are not expected to become Linux modules. Any other exception must be explicit and justified.

This standard-library qualification is important because JetOS deliberately prefers Python's standard library and project-owned code over third-party dependency stacks.

## First HC1 boot goal

The first useful physical milestone is:

**microSD → HC1 bootloader → Linux kernel + correct device tree → JetOS early userspace → CPython/JetOS console**

The existing attached SATA hard drive is **not the boot-development scratch disk by default**. Initial JetOS bring-up should use a dedicated microSD card and preserve existing SATA data unless the owner explicitly authorizes modifying it.

After the first console boot, the priority order is:

1. reliable repeated boot on the HC1;
2. target-native CPython and Gen 2 standard-library qualification;
3. Ethernet detection and link bring-up;
4. DHCP/address configuration, routing, and DNS;
5. remote administration suitable for a headless machine;
6. safe discovery and mounting of the attached SATA disk without formatting or destructive probing;
7. capability reporting for the actual HC1 hardware;
8. reproducible HC1 image construction and flashing.

The HC1 does not need a desktop GUI to qualify. It is primarily a headless/server-shaped JetOS target.

## Board-specific work belongs at the boundary

HC1 support may require board-specific:

- bootloader configuration;
- kernel configuration;
- kernel image/boot layout;
- Exynos 5422 support;
- device-tree selection;
- Ethernet driver/configuration;
- storage/USB-to-SATA behavior;
- thermal/power handling;
- microSD image layout.

These details must remain isolated from shared JetOS behavior. The existence of an HC1 target is not permission to fork JetOS into an HC1-specific operating system.

## Relationship to x86-64 and ARM64

The HC1 adds a first-class `armv7` target; it does not remove JetOS's other architecture goals.

JetOS currently recognizes:

- `x86_64` — including Ryzen-class development/reference systems;
- `armv7` — with the ODROID-HC1 as the current physical reference board;
- `arm64` — retained for modern ARM boards, including appropriate Raspberry Pi configurations.

Shared Python behavior should remain the same wherever equivalent facilities exist.

## Raspberry Pi delegation

JetOS may use Raspberry Pi systems as **delegate nodes** around the HC1. A Pi can take on work that is useful to distribute — for example sensing, network services, testing, storage-adjacent tasks, or other explicitly assigned capabilities — while the HC1 remains a valid standalone JetOS machine.

Delegation rules:

- the HC1 must not require a Raspberry Pi merely to boot or satisfy its own core qualification;
- a Pi is represented by its own board/device profile and actual CPU architecture;
- delegation occurs over explicit, authenticated network interfaces rather than hidden shared-state assumptions;
- responsibilities must be discoverable and capability-driven;
- failure or absence of a delegate must degrade cleanly;
- destructive or privileged work remains subject to the same explicit authorization and safety policy as local work;
- shared JetOS logic should be reused rather than reimplemented separately for Pi nodes.

This makes a small JetOS cluster possible without turning the operating system into architecture-specific copies.

## Definition of “working on the HC1”

JetOS is not considered to support the HC1 merely because Linux supports Exynos 5422 or because an ARMv7 root filesystem exists somewhere.

For the initial HC1 qualification, JetOS must at minimum:

- boot from a dedicated image on the physical HC1;
- enter the JetOS CPython control environment reliably;
- identify itself as the `armv7`/HC1 target;
- pass the Gen 2 Linux standard-library qualification with documented exceptions only;
- bring up Ethernet and obtain usable IP connectivity;
- perform DNS resolution;
- discover the attached SATA storage without destructive modification;
- preserve the same JetOS-facing Python architecture used by the other supported CPU targets.

That is the current hardware objective for JetOS.
