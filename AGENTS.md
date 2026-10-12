# JetOS agent instructions

Before changing JetOS, read:

1. `README.md` — current JetOS goals, implemented state, planned architecture, language constitution, native boundaries, capability model, provenance, and reproducibility goals.
2. `ARCHITECTURES.md` — the first-class architecture contract for x86-64, ARMv7, and ARM64/AArch64, including the rule that one shared JetOS exists above isolated machine-specific boundaries.
3. `ODROID_HC1_TARGET.md` — the current physical-hardware objective: boot and qualify JetOS Gen 2 on the ODROID-HC1, including Linux-appropriate full CPython standard-library qualification, Ethernet, safe SATA discovery, and optional Raspberry Pi delegation.
4. `MANDATE_004.md` — Developer One's active permanent Hyper Mandate covering Python-first implementation, zero/minimal dependencies, no Node.js, API-first authorized AI integrations, JetOS familiarity, source reuse/minimization, multi-architecture support, the HC1 physical target, and the explicit xAI/Grok prohibition.
5. `MANDATE_004D_UNUSED_CODE_RETIREMENT.md` — Developer One's permanent Super Directive requiring evidence-confirmed unused project-owned code to be retired eventually and every non-use deletion to be recorded in `AGENT_DELETION_CHANGELOG.md`.
6. `MANDATE_004E_INFORMATION_LIFECYCLE.md` — Developer One's permanent sub-hyper-mandate requiring an Information Lifecycle Worker that tracks provenance, validity/freshness, dependencies, expiry or invalidation rules, and refresh/replacement procedures for important JetOS information, including pre-expiry credential lifecycle coverage without storing secret values.
7. `MANDATE_004F_CUTTING_ROOM_STORAGE.md` — Developer One's permanent sub-hyper-mandate establishing that JETOS is the **cutting room, not the archive**: keep the smallest practical active/staging/derived working set, retain compact provenance/lifecycle/archive-reference metadata, and do not accumulate bulk historical data long-term once protected archival/backup handoff is verified.
8. `MANDATE_004G_NO_GITHUB_ACTIONS.md` — Developer One's permanent cross-repository Hyper Directive: never use GitHub Actions; build, test, qualification, packaging, benchmarking, and automation stay native/local under repository-owned tooling.
9. `MANDATE_004H_UPSTREAM_CURRENCY.md` — Developer One's permanent hard rule that JETOS tracks stable CPython promptly, qualifies each update in Fat Mode, and only projects it into Skinny Mode after the protected Python/OS surface passes; Gentoo is preferred source/build intelligence rather than JETOS identity.
10. `PYTHON_KERNEL_CODESIGN.md` — the active six-experiment program for using JETOS control of Python and the kernel to simplify or accelerate `subprocess`, `shutil`, tree traversal, asyncio/selectors, multiprocessing shared memory, and tempfile without reducing Python semantics.
11. `source-brain/README.md` — the Fat-mode Source Brain contract: Linux and CPython are coupled JETOS source lineages, exact source revisions must reproduce promoted runtime artifacts, the Source Brain Weaver may co-design both sides under stronger qualification, and Skinny images omit the complete source trees and Fat development tests.
12. `SKINNY_MODE.md` — the hard Fat/Skinny boundary: Fat owns source/build/test bulk; Skinny contains the already-qualified runtime and compact provenance only.
13. `WORK_SERVER.md` — the self-hosted JETOS Work Server contract: clean Git base, isolated worktrees, Docker OS qualification, Fat build gates, bounded opt-in improvement, post-change requalification, and retention only of candidates that pass.
14. `KEEP_SAFE_SPEC.md` — the semantic contract for JETOS `KEEP_Safe`, the protected local-retention type for data that must remain locally available beyond the ordinary cutting-room window; retained bulk payloads are compressed and encrypted, keys remain separate, plaintext working copies stay temporary, and `KEEP_Safe` is not a loophole for indefinite bulk accumulation.

Before recreating, restoring, or replacing behavior that may have existed previously, read `AGENT_DELETION_CHANGELOG.md` and inspect the relevant native Git history first.

Do not rely on a stale summary when these files have materially changed.

For project-owned executable logic, CPython is the default and predominant implementation environment. Another general-purpose language is not an alternate backend/tooling choice. C and assembly remain only the narrow native/architectural exceptions described by JetOS itself and `MANDATE_004.md`.

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS logic must remain architecture-neutral wherever practical; architecture-specific behavior belongs only at genuine machine, kernel, boot, firmware, device, or native-code boundaries. None is a separate JetOS.

The **ODROID-HC1 is the current physical reference target**. It is an `armv7` machine. Work that advances physical JetOS should preferentially move the HC1 toward: dedicated microSD boot, correct Linux kernel/device tree, JetOS Python early userspace, Gen 2 standard-library qualification, Ethernet/IP/DNS, and safe attached-SATA discovery. Do not modify or format an existing HC1 SATA disk as part of bring-up unless explicitly authorized.

In JetOS terminology, **Gen 2 means the Linux-backed configuration, not “second generation.”** The HC1 Gen 2 target is expected to expose the complete CPython standard-library surface supported by the selected CPython release on Linux, with platform-inapplicable or unavoidable exceptions documented rather than silently omitted.

Python currency is mandatory under `MANDATE_004H_UPSTREAM_CURRENCY.md`: adopt stable CPython maintenance releases promptly, record exact Source Brain revisions for reproducibility, qualify them in Fat Mode, and do not hold Skinny Mode on an obsolete Python release merely to avoid substrate work.

`source-brain/linux` and `source-brain/cpython` are not ordinary vendor directories. They are the exact Fat source lineages used to produce the JETOS kernel and language runtime. A promoted artifact must be traceable to the exact Source Brain revisions recorded by the JETOS Git revision. Coordinated Linux/CPython work belongs to the Source Brain Weaver responsibility and must pass stronger OS-, architecture-, and hardware-level qualification than an ordinary small Work Server candidate.

Raspberry Pi systems may be added as board profiles and optional delegate nodes. Delegation must be explicit, capability-driven, authorized, and non-essential to the HC1's own boot/core qualification.

Node.js and its package ecosystem are forbidden. Browser JavaScript is allowed only for a genuine browser frontend and must not introduce Node or a JavaScript build/package stack.

GitHub Actions are forbidden under `MANDATE_004G_NO_GITHUB_ACTIONS.md`. Do not add `.github/workflows/`, hosted Actions jobs, workflow dispatches, Actions artifacts, or hosted CI/status requirements. Use native Git and repository-owned local Python tooling instead.

The Work Server is allowed to create disposable Git worktrees and candidate `workbot/*` branches, but an automatic candidate must remain isolated until it passes the repository-defined Docker qualification and Fat build gates. A worker-host failure is not permission to rewrite JETOS to hide missing Docker, networking, disk, credentials, or other infrastructure. Automatic code changes must remain bounded, test-backed, reviewable, and compliant with `MANDATE_004G_NO_GITHUB_ACTIONS.md`.

The ordinary bounded Work Server improver is **not** authorized to modify `source-brain/linux` or `source-brain/cpython`. Source Brain modifications require the dedicated stronger weaving/qualification path described in `source-brain/README.md`.

Third-party dependencies are zero/minimal by default. Prefer Python's standard library and direct documented APIs over SDK/client-library dependencies. Imported native operating-system/toolchain substrate must remain explicit, pinned, provenance-accounted, and minimized.
