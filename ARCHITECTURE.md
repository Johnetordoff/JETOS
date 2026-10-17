# JetOS architecture

This is the single canonical architecture file. Append future architectural changes here; do not create additional architecture files.

## System identity

JetOS is its own source-built Linux distribution and one operating system across three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. It is not a Gentoo, Debian, Ubuntu, Alpine, or other distribution derivative at build or runtime. Shared JetOS behavior stays architecture-neutral wherever possible; machine-specific divergence is isolated at real kernel, firmware, bootloader, device-tree/ACPI, QEMU, C, or assembly boundaries.

The ODROID-HC1 is the current physical reference target. It is ARMv7 and requires real board qualification rather than generic ARM support alone. The historical **Gen 2** label records the Gentoo-informed configuration context from which this source estate was developed; it does not create an ongoing Gentoo dependency or update obligation.

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

The target source-control architecture is one outer JETOS Git repository containing ordinary tracked source trees, with no nested Git repositories or nested `.git` metadata. Transitional submodules may remain only until the exact pinned Linux and CPython working trees are safely absorbed.

After absorption, `source/linux` is JetOS-owned kernel source and `source/cpython` is JetOS-owned JetLang source. Their recorded upstream repositories and commits remain provenance and reference points, not rolling distribution dependencies. JetOS does not update its Linux source merely because an upstream distribution or Linux release moved; kernel changes are deliberate JetOS source integrations made for a specific capability, fix, security need, hardware target, or engineering decision and are qualified as JetOS changes.

Upstream CPython may continue to be examined as a compatibility/change stream under the JetLang rules above. Upstream URLs, versions, licenses, and original commit IDs remain recorded as provenance.

## Bootstrap boundary

Raw source cannot compile itself without some already-executable compiler/tooling. That unavoidable bootstrap machinery is external build infrastructure, not part of the JetOS distribution identity. JetOS must not select Debian, Gentoo, or another Linux distribution as its canonical base merely to obtain a compiler.

Native Linux hosts may build the vendored source directly with a qualifying external toolchain. Docker, when used, is an optional test/build harness supplied with a caller-selected bootstrap image that already provides required tools; the repository must not name a default Linux distribution image. Bootstrap Python/toolchains must never be copied into JetOS in place of the runtime built from `source/cpython` and `source/linux`.

## Integrated-runtime qualification

A runtime-affecting source change is not fully tested unless the current/new JetOS kernel and current/new JetLang interpreter are built from the modified/current source lineages, the newly built interpreter runs with/on the newly built runtime where supported, relevant CPython/JetLang regression tests run through it, JetOS/native same-runtime integration tests run, and representative networking/runtime behavior is exercised. Where practical, include a small web-server/client check.

Testing only an old/prebuilt kernel, an old/prebuilt interpreter, or isolated source trees is insufficient for final integrated qualification.

## Long-horizon native workloads: AI, speech, and torrent services

JetOS records a distant-future architectural direction in `Documentation/FUTURE_AI_SPEECH_TORRENT.md`: AI support, high-performance speech-to-text/speech-to-command, and torrent/distributed-content services should become first-class JetOS workloads rather than unrelated application stacks.

This is **planned architecture, not current implementation**. The design direction is to keep policy and orchestration in JetLang, reuse and qualify the JetOS/Linux substrate first, and add kernel/native changes only when end-to-end measurements establish a real need.

Speech and AI are intended to converge on one low-latency streaming control path: Linux audio capture feeds incremental recognition, incremental intent/command interpretation, and a capability-checked execution boundary. Torrent/distributed-content services should share the same resource, storage, networking, lifecycle, and observability substrate while normally running at lower/background priority than interactive speech or foreground AI.

The architecture should preserve strong support for audio capture, asynchronous/pollable I/O, networking, hardware/accelerator discovery, cgroups/resource accounting, storage integrity, streaming/cancellation semantics, and target-neutral JetLang APIs. These capabilities should remain available across `x86_64`, `armv7`, and `arm64` while permitting target-specific acceleration only at real native boundaries.

## Fat, Transition, and Skinny

JetOS uses one source estate and one operating system, but promotion deliberately crosses three operational environments:

1. **Fat Development Environment** — the full source/build/debug/qualification workshop;
2. **Transition Environment** — a compact target-specific pre-runtime that retains only enough qualification and diagnosis to prove the production projection after development bulk is removed;
3. **Skinny Production Environment** — the final promoted target runtime.

Fat may contain complete Linux/JetLang source trees, toolchains, exhaustive tests, diagnostics, inventories, benchmarks, and temporary development material. It is not the production footprint.

Transition uses the exact candidate production kernel, JetLang runtime, supported standard library, native runtime dependencies, target configuration, and device responsibilities, plus a small intentional qualification/diagnostic layer. It omits complete source worktrees and general build machinery. Failures found here go back to Fat source for repair; Transition is never an authoritative source fork.

Skinny contains only promoted runtime responsibilities plus compact provenance and any production self-checks that have a real continuing operational purpose. It must not accidentally inherit complete source trees, host/container bootstrap machinery, development compilers, or broad qualification bulk.

The canonical promotion path is:

**Fat source/development → integrated exhaustive qualification → Transition candidate → target qualification → Skinny production image → production/physical qualification.**

See `SKINNY_MODE.md` for the detailed reduction and promotion contract.

## Architecture-specific boundaries

Allowed target-specific divergence includes kernel architecture/configuration, image format, firmware/bootloader handoff, device tree or ACPI, hardware discovery, native entry/MMU/interrupt details, QEMU machine/console selection, and unavoidable C/assembly. Do not duplicate the JetOS control plane across architectures.

Canonical architecture names are `x86_64`, `armv7`, and `arm64`; aliases should normalize to those names internally.
