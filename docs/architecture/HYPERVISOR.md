# JETOS Hypervisor Test Architecture

**Status:** Near-term integration-test plan  
**Date:** 2026-10-04

## Purpose

Docker is useful for fast JETOS userspace development, but Docker does not prove that JETOS can boot as an operating system because the host supplies the Linux kernel.

The next major JETOS integration target is a virtual machine running under a hardware-assisted hypervisor.

The VM should boot a JETOS-controlled kernel and root filesystem and reach a JETOS-controlled userspace without depending on the host operating system's kernel.

## Layers

Docker test:

```text
host Linux kernel
        ↓
JETOS container/userspace
```

Hypervisor test:

```text
physical machine
        ↓
hardware virtualization / hypervisor
        ↓
virtual firmware / boot environment
        ↓
JETOS Linux kernel
        ↓
JETOS init / bootstrap
        ↓
CPython
        ↓
JETOS Python control plane
        ↓
JETOS prompt / services
```

## Initial VM target

The first VM image SHOULD contain only what is needed to prove boot ownership:

- virtual firmware/boot path;
- Linux kernel selected and configured by JETOS;
- minimal initramfs or root filesystem;
- C runtime required by CPython/native code;
- CPython;
- JETOS Python package;
- JETOS native C components;
- a JETOS-controlled PID 1/bootstrap path;
- read/write virtual disk support;
- console input/output;
- hardware inventory;
- Dona Code / Unicode tests;
- networking default state and status reporting;
- JETOS test runner.

The first VM does not need a graphical desktop.

## Initial console goal

A successful boot should reach an interactive console resembling:

```text
JETOS 0.1
John E Tordoff's Operating System

architecture: <arch>
kernel: Linux <version>
python: <version>
Dona Code: Unicode / UTF-8
network: OFF
filesystem: mounted

jetos>
```

The exact presentation is not frozen.

## Initial console capabilities

The first bootable VM should eventually expose commands equivalent to:

```text
hardware
files
languages
exceptions
unicode
test
network status
python
reboot
poweroff
```

Command names may change, but the capabilities should be testable from the console.

## Architecture targets

JETOS should support hypervisor testing on both:

- x86-64;
- AArch64 / ARM64.

The public JETOS APIs and behavior-level tests should remain common.

Native kernel images, boot firmware, machine definitions, and architecture-specific code may differ.

## Host acceleration

Where available, development SHOULD use hardware-assisted virtualization rather than pure software emulation.

Examples include:

- Apple Hypervisor.framework / QEMU HVF on Apple Silicon;
- KVM on Linux;
- Hyper-V/WHPX-class acceleration on supported Windows hosts;
- other equivalent hardware-virtualization backends.

The hypervisor implementation is development infrastructure, not part of the JETOS runtime identity.

## Networking

The first VM SHOULD boot with external networking disabled by default.

This gives the JETOS master-networking policy a clean integration target.

Tests should verify:

1. JETOS reports networking OFF;
2. no external interface is usable while OFF;
3. enabling networking is explicit;
4. turning networking OFF again removes/blocks external connectivity;
5. the reported state agrees with the actual VM network behavior.

A virtual NIC may be present even when policy leaves it inactive.

## Storage

The first VM should use an ordinary virtual block device.

JETOS should be able to:

- discover it;
- mount the root filesystem;
- read/write a test filesystem;
- report the device through the hardware/introspection API.

Later tests can cover multiple disks, removable media, and corruption/recovery cases.

## Boot ownership milestone

The VM test becomes materially different from Docker when:

- the VM firmware loads a JETOS-selected kernel;
- JETOS controls the root filesystem;
- JETOS controls PID 1 / early userspace;
- CPython is started by the JETOS boot path;
- the JETOS console is reached without a host distribution starting JETOS for us.

At that point JETOS is no longer merely a userspace experiment inside another Linux environment.

## Docker remains useful

Docker should remain part of the project for:

- fast compilation;
- unit tests;
- sanitizer tests;
- reproducible userspace dependencies;
- Dona Code / Unicode tests;
- package quarantine experiments.

The VM/hypervisor path adds boot and kernel integration testing; it does not replace the faster Docker path.

## Near-term implementation order

1. Define a minimal kernel configuration for one VM architecture.
2. Define the smallest root filesystem that can start CPython.
3. Write the JETOS early-bootstrap/PID-1 path.
4. Build the root filesystem using Python-owned tooling.
5. Produce a bootable VM disk/initramfs artifact.
6. Boot it under hardware-accelerated virtualization.
7. Reach the JETOS console.
8. Run the same JETOS tests inside the VM.
9. Add network-OFF verification.
10. Repeat for the second architecture.

## Canonical shorthand

> Docker proves JETOS userspace.  
> A hypervisor proves JETOS boot ownership.

> The host may virtualize the machine.  
> It should not supply JETOS's kernel.
