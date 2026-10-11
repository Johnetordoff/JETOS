# Mandate 004 — Developer One Hyper Mandate: Python-first architecture, authorized AI APIs, JetOS goals, and multi-architecture support

Status: **active, permanent, HYPER MANDATE**
Issued by: **Developer One** (the repository owner), 2026-10-10.
Scope: **JetOS and every Brain Clone, Mac Brain, Digital Yamin, worker, agent runtime, provider broker, and future compatible system that integrates with or modifies JetOS.**

## JetOS is first-class architecture

JetOS is not an incidental repository. Any agent or runtime doing system-level work that may affect JetOS must first familiarize itself with the current `README.md`, `ARCHITECTURES.md`, `ODROID_HC1_TARGET.md`, and relevant live JetOS source/docs and preserve the actual goals stated there.

Agents must distinguish implemented JetOS behavior from planned architecture and must not describe planned capabilities as already working. Familiarity must be refreshed when JetOS materially changes.

Core JetOS goals include a source-oriented, Python-first operating system that can ultimately replace the software stack on a target machine; own/select its boot path; discover capabilities; install only what a device role requires; control enabled machine capabilities through explicit policy; use its own early userspace and Python control plane; account for provenance/dependencies/exceptions; and remain reproducibly rebuildable from pinned source inputs.

## Multi-architecture constitution

**JetOS must support x86-64, ARMv7, and ARM64/AArch64 as first-class CPU targets.** None is a compatibility afterthought, experimental side port, or separate operating system.

The current physical-board priority is the **ODROID-HC1**, which is an ARMv7 target. JetOS must work on the actual HC1 hardware using the Gen 2 Linux-backed configuration defined in `ODROID_HC1_TARGET.md`; generic Linux or generic ARMv7 support alone does not satisfy that physical target.

There is one JetOS above the architecture boundary. Shared Python control logic, policy, capability modeling, package/image logic, provenance, tests, public behavior, and system concepts must remain common wherever technically possible.

Architecture-specific divergence is allowed only where the machine genuinely requires it, including kernel architecture/configuration, firmware and boot handoff, kernel image format, QEMU machine/console details, device tree or ACPI handling, board/device profiles, and unavoidable C/assembly/native substrate.

The canonical target names are:

- `x86_64` for 64-bit x86/AMD64 systems;
- `armv7` for 32-bit ARMv7 systems, including the ODROID-HC1;
- `arm64` for AArch64/ARM64 systems.

Common aliases may be accepted at interfaces, but internal architecture decisions should normalize to these names.

A JetOS image must never knowingly mix kernel and userspace architectures. An ARMv7 kernel requires ARMv7 userspace; an ARM64 kernel requires ARM64 userspace; an x86-64 kernel requires x86-64 userspace. The current rootfs builder copies CPython and native libraries from its build environment, so until explicit cross-userspace construction is implemented, rootfs/initramfs assembly must occur in a matching target-native environment or use a verified target-native runtime source.

Changes to shared JetOS logic must preserve all first-class architecture targets unless the change is explicitly and correctly isolated to one architecture-specific boundary. Fast repository tests must continuously exercise the supported target definitions. Physical-board support remains a device-profile layer on top of CPU architecture; supporting an instruction-set family does not automatically qualify a specific board without its firmware/device-tree/peripheral work.

For the HC1 Gen 2 target, qualification includes a target-native CPython runtime and the complete Python standard-library surface supported by the selected CPython release on Linux, with only explicit platform-inapplicable or unavoidable documented exceptions. “Gen 2” means the Linux-backed JetOS configuration, not “second generation.”

Raspberry Pi systems may become additional JetOS board profiles and delegate nodes. A delegate must use shared JetOS behavior wherever possible, expose explicit capabilities, communicate over authorized interfaces, and never become an undeclared requirement for the HC1 to boot or satisfy its own core qualification.

Additional CPU architectures are not implicitly in scope. Expanding beyond x86-64, ARMv7, and ARM64/AArch64 requires an explicit Developer One decision.

## Python-first language constitution

**Python is the predominant and default implementation language.** If behavior can be implemented correctly and reasonably in CPython, it must be implemented in Python.

No other general-purpose language is an alternate implementation choice for project-owned backend, orchestration, automation, CLI, build, service, agent, policy, test, repository-tooling, package orchestration, or operating-system control logic. Do not introduce Rust, C++, Go, Java, Zig, Node.js, shell, or another language as a parallel implementation stack merely because it is convenient or supplied by an upstream tool/vendor.

Narrow exceptions exist only where Python cannot correctly perform the work:

- **C** for unavoidable/measured native boundaries, CPython extensions, or substrate that cannot correctly be expressed in Python;
- **assembly** only where the hardware architecture itself requires it;
- imported upstream native code may remain quarantined substrate/dependency debt, but it is not precedent for new JetOS-owned code.

Python retains orchestration, policy, validation, compatibility behavior, public interfaces, tests, and control of native exceptions wherever technically possible.

Declarative formats such as Markdown, JSON, YAML, TOML, schemas, configuration, and ordinary data remain appropriate because they are data/configuration rather than alternate executable implementation languages.

## JavaScript and Node prohibition

**Node.js is forbidden.** Do not use `node`, `npm`, `npx`, `yarn`, `pnpm`, Node-based tooling/bridges/CLIs, server-side JavaScript, JavaScript package ecosystems, or Node-dependent build chains.

JavaScript is permitted only as small native browser JavaScript for a genuine browser frontend when one actually exists and requires it. Browser JavaScript must not introduce Node, package managers, bundlers, or a second application stack.

## Dependency constitution

**The default third-party dependency budget for project-owned Python logic is zero.** Use the Python standard library and JetOS/project-owned code by default.

Do not smuggle dependencies through requirements files, lockfiles, optional/test dependencies, build helpers, SDKs, shell wrappers, generated clients, Node packages, or other side channels merely to avoid calling them dependencies.

External AI companies/services are **API integrations, not implementation dependencies**. Prefer direct documented HTTP APIs using the standard library over vendor/community SDKs or client libraries. SDK/library exceptions require a concrete technical necessity, must remain narrowly scoped, and do not become architectural precedent.

Do not create routine dependency ecosystems such as requirements/lock stacks, npm lockfiles, vendored dependency forests, or package-manager-driven application build stacks unless Developer One explicitly authorizes a genuinely necessary exception.

Imported operating-system/toolchain substrate that JetOS genuinely needs must be pinned, provenance-accounted, minimized, and treated as imported substrate rather than permission to write new JetOS logic in its language.

## Minimal source and reuse rule

Implement the smallest practical amount of clear code necessary. Reduce logical/source footprint without line-golf, obscurity, or loss of correctness.

Reuse shared behavior everywhere except intentional business-logic divergence points that must be able to change independently later. Non-business-logic duplication is unacceptable by default.

Architecture support follows the same rule: do not duplicate JetOS wholesale for x86-64, ARMv7, and ARM64. Reuse one implementation and isolate only the genuinely architecture-specific pieces.

## Authorized AI API integrations

Governed systems should maintain and improve first-class API connectivity for authorized providers including:

- OpenAI GPT/Codex;
- Anthropic Claude;
- Google Gemini;
- Mistral;
- Cohere;
- Cerebras;
- DeepSeek;
- Groq;
- other explicitly authorized non-xAI providers.

Use documented public HTTP APIs directly where practical; keep shared transport/error/authentication/tool-call behavior reusable; keep provider-specific divergence only where protocols genuinely differ; keep credentials external; and fail closed when credentials/configuration are missing.

## Explicit xAI / Grok prohibition

**xAI/Grok is explicitly blocked.** Do not whitelist xAI/Grok endpoints, add xAI/Grok adapters/models/credentials/routes/fallbacks, proxy to Grok through an aggregator, or weaken default-deny networking to make Grok reachable.

**Groq is not Grok/xAI.** Groq remains authorized unless Developer One explicitly changes that rule.

## Cross-system rule

Brain Clone, Mac Brain, Digital Yamin workers, JetOS, and future compatible systems must preserve this language/dependency/API/architecture policy when they integrate with one another. A cross-system integration must not introduce a forbidden language, Node toolchain, hidden dependency ecosystem, vendor SDK, or architecture-specific duplicate stack merely because another subsystem uses one.

This mandate does not loosen privacy, containment, provenance, reproducibility, machine-safety, default-deny networking, or JetOS's existing native-boundary rules.
