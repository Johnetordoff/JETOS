# JetOS architecture

This is the single canonical architecture file. Append future architectural changes here; do not create additional architecture files.

## System identity

JetOS is one operating system across three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS behavior stays architecture-neutral wherever possible; machine-specific divergence is isolated at real kernel, firmware, bootloader, device-tree/ACPI, QEMU, C, or assembly boundaries.

The ODROID-HC1 is the current physical reference target. It is ARMv7 and requires real board qualification rather than generic ARM support alone. In JetOS terminology, **Gen 2 means the Gentoo/Linux-backed configuration context, not “second generation.”**

A complete image must pair a kernel and userspace for the same target architecture. Until explicit verified cross-userspace construction exists, rootfs/initramfs construction must run in a matching target-native environment or consume verified target-native runtime inputs.

## JetLang

JetLang is the JetOS language/runtime. It is an improved, deliberately diverging descendant of CPython. An informal mental model is “CPython 2,” but the formal name is JetLang.

CPython is JetLang's source lineage and compatibility foundation. Python language semantics and the supported standard-library surface are the compatibility contract. JetLang may replace or consolidate CPython implementation details when behavior remains correctly qualified. CPython regression tests are a primary compatibility corpus, supplemented by JetLang-native and JetOS same-runtime tests.

JetLang currently stabilizes on the Python 3.14 lineage. The next feature-series target is 3.15, but that transition is an integration into the existing JetLang-owned tree, not a wholesale source-tree replacement. Once the initial CPython-derived source has been absorbed, future CPython releases are treated as upstream change/reference streams: examine their release notes, diffs, tests, standard-library/runtime changes, and fixes; reconcile those changes into JetLang; preserve intentional JetLang changes; then qualify the resulting integrated runtime. The compatibility/version label advances only after that integration is complete and qualified.

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

The target source-control architecture is one outer JETOS Git repository containing ordinary tracked source trees, with no nested Git repositories or nested `.git` metadata. Transitional submodules may remain only until the exact pinned Linux and CPython working trees are safely absorbed. After absorption, the JetLang tree is JetOS-owned source; upstream CPython repositories remain provenance, comparison, change-discovery, and test/reference sources rather than replacement working trees. Upstream URLs, versions, licenses, and commit IDs are recorded as JetOS-owned metadata.

## Integrated-runtime qualification

A runtime-affecting source change is not fully tested unless the current/new JetOS kernel and current/new JetLang interpreter are built from the modified/current source lineages, the newly built interpreter runs with/on the newly built runtime where supported, relevant CPython/JetLang regression tests run through it, JetOS/native same-runtime integration tests run, and representative networking/runtime behavior is exercised. Where practical, include a small web-server/client check.

Testing only an old/prebuilt kernel, an old/prebuilt interpreter, or isolated source trees is insufficient for final integrated qualification.

## Long-horizon native workloads: AI, speech, and torrent services

JetOS records a distant-future architectural direction in `Documentation/FUTURE_AI_SPEECH_TORRENT.md`: AI support, high-performance speech-to-text/speech-to-command, and torrent/distributed-content services should become first-class JetOS workloads rather than unrelated application stacks.

This is **planned architecture, not current implementation**. The design direction is to keep policy and orchestration in JetLang, reuse and qualify Linux/Gentoo substrate capabilities first, and add kernel/native changes only when end-to-end measurements establish a real need.

Speech and AI are intended to converge on one low-latency streaming control path: Linux audio capture feeds incremental recognition, incremental intent/command interpretation, and a capability-checked execution boundary. Torrent/distributed-content services should share the same resource, storage, networking, lifecycle, and observability substrate while normally running at lower/background priority than interactive speech or foreground AI.

The architecture should preserve strong support for audio capture, asynchronous/pollable I/O, networking, hardware/accelerator discovery, cgroups/resource accounting, storage integrity, streaming/cancellation semantics, and target-neutral JetLang APIs. These capabilities should remain available across `x86_64`, `armv7`, and `arm64` while permitting target-specific acceleration only at real native boundaries.

## Fat and Skinny

Fat Mode contains the source/build/diagnostic/qualification environment. Skinny Mode is a target-specific qualified runtime projection and must not accidentally include complete Linux/CPython source trees, temporary development material, or test bulk.

## Architecture-specific boundaries

Allowed target-specific divergence includes kernel architecture/configuration, image format, firmware/bootloader handoff, device tree or ACPI, hardware discovery, native entry/MMU/interrupt details, QEMU machine/console selection, and unavoidable C/assembly. Do not duplicate the JetOS control plane across architectures.

Canonical architecture names are `x86_64`, `armv7`, and `arm64`; aliases should normalize to those names internally.
