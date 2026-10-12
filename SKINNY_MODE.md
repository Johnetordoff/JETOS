# JETOS Fat Development / Skinny HC1 Runtime

Status: **active architecture rule**

## Core rule

JETOS is developed and qualified in a **Fat Mode** environment, but the ODROID-HC1 is flashed with a deliberately minimized **Skinny Mode** runtime image.

**Fat Mode is the workshop. Skinny Mode is the product.**

The purpose of Fat Mode is to make JETOS easy to build, inspect, test, instrument, debug, compare, and reduce. The purpose of Skinny Mode is to preserve the maximum useful Python 3.14 capability surface with the minimum Linux/kernel/userspace substrate required to support it on the HC1.

## Fat Mode

Fat Mode may include development-only material such as:

- full frozen Linux source;
- full frozen CPython 3.14 source;
- compilers, linkers, headers, build tools, diagnostics, tracing, debuggers, and profilers;
- broad kernel configuration used to establish a capability baseline;
- extensive test fixtures and qualification tooling;
- image-generation and flashing tools;
- comparison manifests for reduction experiments.

Fat Mode is not the target footprint for the HC1.

## Skinny Mode

The flashed HC1 image should contain only what the qualified runtime needs, including:

- the JETOS-maintained HC1/ARMv7 Linux kernel configuration and resulting kernel;
- the HC1 device tree and required boot files;
- the target-native JETOS Python runtime based on CPython 3.14;
- the supported Python standard library and required native extension/shared-library dependencies;
- JETOS early userspace/control logic;
- storage/filesystem support needed by the target;
- Ethernet, IP, routing, DHCP/DNS, and authorized remote administration support;
- safe SATA discovery support;
- required firmware, certificate roots, logging/recovery pieces, and other capabilities that survive qualification.

Development-only compilers, build trees, package-manager machinery, and diagnostic bulk do not belong in the Skinny HC1 runtime unless a specific runtime responsibility proves they are required.

## Python-first reduction gate

Skinny Mode is not allowed to become smaller by silently reducing Python.

The reduction process is:

1. build a broad/fat HC1-capable kernel and target-native Python 3.14 runtime;
2. run the full JETOS standard-library and Python↔OS qualification suite;
3. record the passing behavior as the baseline;
4. remove one Linux kernel/userspace capability family at a time;
5. rebuild and boot the HC1 image;
6. rerun the same qualification suite on the actual target;
7. keep the reduction only when the required Python-visible capability surface remains intact;
8. restore the removed substrate when the reduction causes a required Python capability to regress.

Therefore the optimization target is:

> **the smallest HC1 Linux/kernel/userspace substrate that preserves the complete qualified JETOS Python 3.14 capability surface.**

## Kernel ownership

The Skinny kernel is a **JETOS-maintained Linux kernel build**, not a clean-room replacement kernel. JETOS owns the selected source revision, HC1/ARMv7 configuration, required patches, build rules, capability rationale, and qualification evidence. Linux remains the imported hardware/kernel substrate.

## Source retention versus runtime footprint

Keeping source available and keeping source resident in boot RAM are different requirements.

Complete Linux source may remain part of the JETOS installation at `/usr/src/linux`, but on the constrained HC1 it should live on the microSD/root filesystem rather than being expanded into the initramfs. The boot/initramfs path should stay small enough for reliable operation on the HC1.

## Flashing model

The normal physical workflow is:

**Fat development machine/environment → build + qualify → construct Skinny HC1 image → flash dedicated microSD → boot HC1 → target qualification → iterate.**

The attached SATA disk is not a build scratch disk and must not be formatted or modified during bring-up without explicit authorization.
