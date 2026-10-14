# JetOS agent instructions

Before changing JetOS, read:

1. `JETLANG_ARCHITECTURE.md` — **canonical current language/repository identity**: JetLang is an improved, deliberately diverging CPython descendant (informally, "CPython 2"); the formal name is JetLang; Linux, the CPython-derived JetLang tree, and shared runtime code belong to one outer JETOS Git repository with no Source Brain submodules or nested Git after migration.
2. `README.md` — current JetOS goals, implemented state, planned architecture, language constitution, native boundaries, capability model, provenance, and reproducibility goals.
3. `ARCHITECTURES.md` — the first-class architecture contract for x86-64, ARMv7, and ARM64/AArch64, including the rule that one shared JetOS exists above isolated machine-specific boundaries.
4. `ODROID_HC1_TARGET.md` — the current physical-hardware objective: boot and qualify JetOS Gen 2 on the ODROID-HC1, including the Linux-appropriate JetLang/Python standard-library surface, Ethernet, safe SATA discovery, and optional Raspberry Pi delegation.
5. `MANDATE_004.md` — Developer One's active permanent Hyper Mandate covering Python-first implementation, zero/minimal dependencies, no Node.js, API-first authorized AI integrations, JetOS familiarity, source reuse/minimization, multi-architecture support, the HC1 physical target, and the explicit xAI/Grok prohibition.
6. `MANDATE_004D_UNUSED_CODE_RETIREMENT.md` — Developer One's permanent Super Directive requiring evidence-confirmed unused project-owned code to be retired eventually and every non-use deletion to be recorded in `AGENT_DELETION_CHANGELOG.md`.
7. `MANDATE_004E_INFORMATION_LIFECYCLE.md` — Developer One's permanent sub-hyper-mandate requiring an Information Lifecycle Worker that tracks provenance, validity/freshness, dependencies, expiry or invalidation rules, and refresh/replacement procedures for important JetOS information, including pre-expiry credential lifecycle coverage without storing secret values.
8. `MANDATE_004F_CUTTING_ROOM_STORAGE.md` — Developer One's permanent sub-hyper-mandate establishing that JETOS is the **cutting room, not the archive**: keep the smallest practical active/staging/derived working set, retain compact provenance/lifecycle/archive-reference metadata, and do not accumulate bulk historical data long-term once protected archival/backup handoff is verified.
9. `MANDATE_004G_NO_GITHUB_ACTIONS.md` — Developer One's permanent cross-repository Hyper Directive: never use GitHub Actions; build, test, qualification, packaging, benchmarking, and automation stay native/local under repository-owned tooling.
10. `MANDATE_004H_UPSTREAM_CURRENCY.md` — Developer One's permanent hard rule that JETOS tracks useful stable CPython upstream promptly as JetLang's source lineage, qualifies each update in Fat Mode, and only projects it into Skinny Mode after the protected Python/OS surface passes; Gentoo is preferred source/build intelligence rather than JETOS identity.
11. `PYTHON_KERNEL_CODESIGN.md` — the active program for using JetOS control of JetLang/CPython-derived implementation and the kernel to simplify or accelerate Python-visible behavior without reducing semantics.
12. `source-brain/README.md` — the Fat-mode Source Brain contract: Linux, CPython-derived JetLang, and shared native code are coupled JETOS source lineages, exact outer-repository source state must reproduce promoted runtime artifacts, and the Source Brain Weaver may co-design both sides under stronger qualification.
13. `source-brain/shared/README.md` — coherent shared Langkernel ownership and integrated-runtime acceptance requirements.
14. `SKINNY_MODE.md` — the hard Fat/Skinny boundary: Fat owns source/build/test bulk; Skinny contains the already-qualified runtime and compact provenance only.
15. `WORK_SERVER.md` — the self-hosted JETOS Work Server contract: clean Git base, isolated worktrees, Docker OS qualification, Fat build gates, bounded opt-in improvement, post-change requalification, and retention only of candidates that pass.
16. `KEEP_SAFE_SPEC.md` — the semantic contract for JETOS `KEEP_Safe`, the protected local-retention type for data that must remain locally available beyond the ordinary cutting-room window.

When older documents conflict with `JETLANG_ARCHITECTURE.md`, treat the older wording as historical/stale and update it rather than reverting the current architecture.

Before recreating, restoring, or replacing behavior that may have existed previously, read `AGENT_DELETION_CHANGELOG.md` and inspect the relevant native Git history first.

## Language identity

JetLang is the JetOS language/runtime and is an improved CPython descendant. A useful informal mental model is **CPython 2**, but the project name is **JetLang**. Do not say JetLang is unrelated to CPython; do not reduce JetLang to unmodified stock CPython either.

Python semantics and the supported standard-library surface are the compatibility contract. CPython source and regression tests are first-class JetLang inputs. JetLang may deliberately diverge in implementation, including coordinated kernel/runtime improvements, when behavior remains correctly qualified.

For project-owned high-level executable logic, Python/JetLang is the default and predominant implementation environment. Another general-purpose language is not an alternate backend/tooling choice. C and assembly remain the narrow native/architectural exceptions described by JetOS and `MANDATE_004.md`.

## One-repository rule

The canonical source-control architecture is **one outer JETOS repository**. The final Source Brain checkout contains ordinary tracked directories:

```text
source-brain/linux
source-brain/cpython
source-brain/shared
```

There must be no Source Brain Git submodules and no nested `.git` files/directories after migration. Upstream Linux and CPython Git repositories are provenance/update sources only. Their URLs and commit IDs are recorded inside JETOS metadata.

A temporary bootstrap checkout may still contain the old gitlinks until `tools/absorb_source_brain.py` safely copies the pinned working trees into the outer repository. Never "fix" the architecture by deleting the gitlinks before the source has been absorbed.

After migration, build/test tooling must use the outer JETOS source graph and repository-owned upstream provenance rather than treating `source-brain/linux` or `source-brain/cpython` as independent Git repositories.

## Architecture and targets

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. Shared JetOS/JetLang logic must remain architecture-neutral wherever practical; architecture-specific behavior belongs only at genuine machine, kernel, boot, firmware, device, or native-code boundaries. None is a separate JetOS.

The **ODROID-HC1 is the current physical reference target** and is an `armv7` machine. Work advancing physical JetOS should preferentially move it toward dedicated microSD boot, correct kernel/device tree, JetLang early userspace, standard-library qualification, Ethernet/IP/DNS, and safe attached-SATA discovery. Do not modify or format an existing HC1 SATA disk unless explicitly authorized.

In JetOS terminology, **Gen 2 means Gentoo/Linux-backed configuration context where applicable, never "second generation."** Gentoo provides source/build/configuration intelligence; it is not JetOS itself.

Python/CPython upstream currency remains important because CPython is JetLang's lineage. Intake must preserve JetLang changes and provenance rather than resetting JetLang to stock upstream.

`source-brain/linux` and `source-brain/cpython` are controlled Fat source lineages, not opaque vendor code. Coordinated Linux/JetLang work belongs to the Source Brain Weaver responsibility and requires stronger OS-, architecture-, integration-, and hardware-level qualification than an ordinary small Work Server candidate.

Raspberry Pi systems may be added as board profiles and optional delegate nodes. Delegation must be explicit, capability-driven, authorized, and non-essential to the HC1's own boot/core qualification.

Node.js and its package ecosystem are forbidden. Browser JavaScript is allowed only for a genuine browser frontend and must not introduce Node or a JavaScript build/package stack.

GitHub Actions are forbidden under `MANDATE_004G_NO_GITHUB_ACTIONS.md`. Do not add `.github/workflows/`, hosted Actions jobs, workflow dispatches, Actions artifacts, or hosted CI/status requirements. Use native Git and repository-owned local Python tooling instead.

The Work Server may create disposable Git worktrees and candidate `workbot/*` branches, but automatic candidates remain isolated until repository-defined qualification gates pass. A worker-host failure is not permission to rewrite JetOS to conceal missing infrastructure. Automatic code changes must remain bounded, test-backed, reviewable, and compliant with the no-Actions rule.

The ordinary bounded Work Server improver is **not** automatically authorized to modify Source Brain native lineages. Such modifications require the dedicated stronger weaving/qualification path described in `source-brain/README.md`.

Third-party dependencies are zero/minimal by default. Prefer the Python/JetLang standard library and direct documented APIs over SDK/client-library dependencies. Imported native operating-system/toolchain substrate must remain explicit, pinned, provenance-accounted, and minimized.
