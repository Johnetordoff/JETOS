# JetOS agent instructions

Before changing JetOS, read:

1. `README.md` — current JetOS goals, implemented state, planned architecture, language constitution, native boundaries, capability model, provenance, and reproducibility goals.
2. `ARCHITECTURES.md` — the first-class architecture contract for x86-64, ARMv7, and ARM64/AArch64, including the rule that one shared JetOS exists above isolated machine-specific boundaries.
3. `ODROID_HC1_TARGET.md` — the current physical-hardware objective: boot and qualify JetOS Gen 2 on the ODROID-HC1, including Linux-appropriate full CPython standard-library qualification, Ethernet, safe SATA discovery, and optional Raspberry Pi delegation.
4. `MANDATE_004.md` — Developer One's active permanent Hyper Mandate covering Python-first implementation, zero/minimal dependencies, no Node.js, API-first authorized AI integrations, JetOS familiarity, source reuse/minimization, multi-architecture support, the HC1 physical target, and the explicit xAI/Grok prohibition.
5. `MANDATE_004D_UNUSED_CODE_RETIREMENT.md` — Developer One's permanent Super Directive requiring evidence-confirmed unused project-owned code to be retired eventually and every non-use deletion to be recorded in `AGENT_DELETION_CHANGELOG.md`.
6. `MANDATE_004E_INFORMATION_LIFECYCLE.md` — Developer One's permanent sub-hyper-mandate requiring an Information Lifecycle Worker that tracks provenance, validity/freshness, dependencies, expiry or invalidation rules, and refresh/replacement procedures for important JetOS information, including pre-expiry credential lifecycle coverage without storing secret values.

Before recreating, restoring, or replacing behavior that may have existed previously, read `AGENT_DELETION_CHANGELOG.md` and inspect the relevant native Git history first.

Do not rely on a stale summary when these files have materially changed.

For project-owned executable logic, CPython is the default and predominant implementation environment. Another general-purpose language is not an alternate backend/tooling choice. C and assembly remain only the narrow native/architectural exceptions described by JetOS itself and `MANDATE_004.md`.

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS logic must remain architecture-neutral wherever practical; architecture-specific behavior belongs only at genuine machine, kernel, boot, firmware, device, or native-code boundaries. None is a separate JetOS.

The **ODROID-HC1 is the current physical reference target**. It is an `armv7` machine. Work that advances physical JetOS should preferentially move the HC1 toward: dedicated microSD boot, correct Linux kernel/device tree, JetOS Python early userspace, Gen 2 standard-library qualification, Ethernet/IP/DNS, and safe attached-SATA discovery. Do not modify or format an existing HC1 SATA disk as part of bring-up unless explicitly authorized.

In JetOS terminology, **Gen 2 means the Linux-backed configuration, not “second generation.”** The HC1 Gen 2 target is expected to expose the complete CPython standard-library surface supported by the selected CPython release on Linux, with platform-inapplicable or unavoidable exceptions documented rather than silently omitted.

Raspberry Pi systems may be added as board profiles and optional delegate nodes. Delegation must be explicit, capability-driven, authorized, and non-essential to the HC1's own boot/core qualification.

Node.js and its package ecosystem are forbidden. Browser JavaScript is allowed only for a genuine browser frontend and must not introduce Node or a JavaScript build/package stack.

Third-party dependencies are zero/minimal by default. Prefer Python's standard library and direct documented APIs over SDK/client-library dependencies. Imported native operating-system/toolchain substrate must remain explicit, pinned, provenance-accounted, and minimized.
