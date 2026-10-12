# JetOS agent instructions

Before changing JetOS, read:

1. `README.md` — current JetOS goals, implemented state, planned architecture, language constitution, native boundaries, capability model, provenance, and reproducibility goals.
2. `ARCHITECTURES.md` — the first-class architecture contract for x86-64, ARMv7, and ARM64/AArch64, including the rule that one shared JetOS exists above isolated machine-specific boundaries.
3. `FAT_SKINNY_RUNTIME.md` — the canonical source/runtime contract: Fat carries the portable source universe while using target-native compiled JETOS Language and C extensions at runtime; Skinny is a target-resolved deployment retaining only required compiled/runtime artifacts plus provenance.
4. `ODROID_HC1_TARGET.md` — the current physical-hardware objective: boot and qualify JetOS Gen 2 on the ODROID-HC1, including Linux-appropriate full CPython standard-library qualification, Ethernet, safe SATA discovery, and optional Raspberry Pi delegation.
5. `MANDATE_004.md` — Developer One's active permanent Hyper Mandate covering Python-first implementation, zero/minimal dependencies, no Node.js, API-first authorized AI integrations, JetOS familiarity, source reuse/minimization, multi-architecture support, the HC1 physical target, and the explicit xAI/Grok prohibition.
6. `MANDATE_004D_UNUSED_CODE_RETIREMENT.md` — Developer One's permanent Super Directive requiring evidence-confirmed unused project-owned code to be retired eventually and every non-use deletion to be recorded in `AGENT_DELETION_CHANGELOG.md`.
7. `MANDATE_004E_INFORMATION_LIFECYCLE.md` — Developer One's permanent sub-hyper-mandate requiring an Information Lifecycle Worker that tracks provenance, validity/freshness, dependencies, expiry or invalidation rules, and refresh/replacement procedures for important JetOS information, including pre-expiry credential lifecycle coverage without storing secret values.
8. `MANDATE_004F_CUTTING_ROOM_STORAGE.md` — Developer One's permanent sub-hyper-mandate establishing that JETOS is the **cutting room, not the archive**: keep the smallest practical active/staging/derived working set, retain compact provenance/lifecycle/archive-reference metadata, and do not accumulate bulk historical data long-term once protected archival/backup handoff is verified.
9. `MANDATE_004G_NO_GITHUB_ACTIONS.md` — Developer One's permanent cross-repository Hyper Directive: never use GitHub Actions; build, test, qualification, packaging, benchmarking, and automation stay native/local under repository-owned tooling.
10. `MANDATE_004H_UPSTREAM_CURRENCY.md` — Developer One's permanent hard rule that JETOS tracks stable CPython promptly, qualifies each update in Fat Mode, and only projects it into Skinny Mode after the protected Python/OS surface passes; Gentoo is the preferred source/build intelligence input pending any later promotion to a mandatory currency rule.
11. `KEEP_SAFE_SPEC.md` — the semantic contract for JETOS `KEEP_Safe`, the protected local-retention type for data that must remain locally available beyond the ordinary cutting-room window; retained bulk payloads are compressed and encrypted, keys remain separate, plaintext working copies stay temporary, and `KEEP_Safe` is not a loophole for indefinite bulk accumulation.

Before recreating, restoring, or replacing behavior that may have existed previously, read `AGENT_DELETION_CHANGELOG.md` and inspect the relevant native Git history first.

Do not rely on a stale summary when these files have materially changed.

For project-owned executable logic, CPython is the default and predominant implementation environment. Another general-purpose language is not an alternate backend/tooling choice. C and assembly remain only the narrow native/architectural exceptions described by JetOS itself and `MANDATE_004.md`.

When C is justified, the normal JetOS bridge is a CPython C extension: Python owns the public object/API model and orchestration while pure C implements hardware/kernel boundaries and measured hot operations. Fat mode retains the corresponding source but still runs the extension compiled for the current machine and JETOS-Language ABI. Skinny mode retains only the target-required compiled extension/runtime artifacts plus reproducible provenance unless source is explicitly required by that role.

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS logic must remain architecture-neutral wherever practical; architecture-specific behavior belongs only at genuine machine, kernel, boot, firmware, device, or native-code boundaries. None is a separate JetOS.

The **ODROID-HC1 is the current physical reference target**. It is an `armv7` machine. Work that advances physical JetOS should preferentially move the HC1 toward: dedicated microSD boot, correct Linux kernel/device tree, JetOS Python early userspace, Gen 2 standard-library qualification, Ethernet/IP/DNS, and safe attached-SATA discovery. Do not modify or format an existing HC1 SATA disk as part of bring-up unless explicitly authorized.

In JetOS terminology, **Gen 2 means the Linux-backed configuration, not “second generation.”** The HC1 Gen 2 target is expected to expose the complete CPython standard-library surface supported by the selected CPython release on Linux, with platform-inapplicable or unavoidable exceptions documented rather than silently omitted.

Python currency is mandatory under `MANDATE_004H_UPSTREAM_CURRENCY.md`: adopt stable CPython maintenance releases promptly, pin exact revisions for reproducibility, qualify them in Fat Mode, and do not hold Skinny Mode on an obsolete Python release merely to avoid substrate work.

Raspberry Pi systems may be added as board profiles and optional delegate nodes. Delegation must be explicit, capability-driven, authorized, and non-essential to the HC1's own boot/core qualification.

Node.js and its package ecosystem are forbidden. Browser JavaScript is allowed only for a genuine browser frontend and must not introduce Node or a JavaScript build/package stack.

GitHub Actions are forbidden under `MANDATE_004G_NO_GITHUB_ACTIONS.md`. Do not add `.github/workflows/`, hosted Actions jobs, workflow dispatches, Actions artifacts, or hosted CI/status requirements. Use native Git and repository-owned local Python tooling instead.

Third-party dependencies are zero/minimal by default. Prefer Python's standard library and direct documented APIs over SDK/client-library dependencies. Imported native operating-system/toolchain substrate must remain explicit, pinned, provenance-accounted, and minimized.
