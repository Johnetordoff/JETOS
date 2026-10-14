# JetOS architecture

This is the single canonical architecture file. Append future architectural changes here; do not create additional architecture files.

## System identity

JetOS is one operating system across three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS behavior stays architecture-neutral wherever possible; machine-specific divergence is isolated at real kernel, firmware, bootloader, device-tree/ACPI, QEMU, C, or assembly boundaries.

The ODROID-HC1 is the current physical reference target. It is ARMv7 and requires real board qualification rather than generic ARM support alone. In JetOS terminology, **Gen 2 means the Gentoo/Linux-backed configuration context, not “second generation.”**

A complete image must pair a kernel and userspace for the same target architecture. Until explicit verified cross-userspace construction exists, rootfs/initramfs construction must run in a matching target-native environment or consume verified target-native runtime inputs.

## JetLang

JetLang is the JetOS language/runtime. It is an improved, deliberately diverging descendant of CPython. An informal mental model is “CPython 2,” but the formal name is JetLang.

CPython is JetLang's source lineage and compatibility foundation. Python language semantics and the supported standard-library surface are the compatibility contract. JetLang may replace or consolidate CPython implementation details when behavior remains correctly qualified. CPython regression tests are a primary compatibility corpus, supplemented by JetLang-native and JetOS same-runtime tests.

Linux and CPython-derived JetLang native responsibilities are components of one integrated JetOS/JetLang runtime, not separate products.

## Source organization

External/native/dependency source lives under one plainly named directory:

```text
source/
  linux/
  cpython/     # CPython-derived JetLang lineage
  shared/
  ports/
```

The target source-control architecture is one outer JETOS Git repository containing ordinary tracked source trees, with no nested Git repositories or nested `.git` metadata. Transitional submodules may remain only until the exact pinned Linux and CPython working trees are safely absorbed. Upstream repositories are provenance/update sources; their URLs, versions, licenses, and commit IDs are recorded as JetOS-owned metadata.

## Integrated-runtime qualification

A runtime-affecting source change is not fully tested unless the current/new JetOS kernel and current/new JetLang interpreter are built from the modified/current source lineages, the newly built interpreter runs with/on the newly built runtime where supported, relevant CPython/JetLang regression tests run through it, JetOS/native same-runtime integration tests run, and representative networking/runtime behavior is exercised. Where practical, include a small web-server/client check.

Testing only an old/prebuilt kernel, an old/prebuilt interpreter, or isolated source trees is insufficient for final integrated qualification.

## Fat and Skinny

Fat Mode contains the source/build/diagnostic/qualification environment. Skinny Mode is a target-specific qualified runtime projection and must not accidentally include complete Linux/CPython source trees, temporary development material, or test bulk.

## Architecture-specific boundaries

Allowed target-specific divergence includes kernel architecture/configuration, image format, firmware/bootloader handoff, device tree or ACPI, hardware discovery, native entry/MMU/interrupt details, QEMU machine/console selection, and unavoidable C/assembly. Do not duplicate the JetOS control plane across architectures.

Canonical architecture names are `x86_64`, `armv7`, and `arm64`; aliases should normalize to those names internally.
