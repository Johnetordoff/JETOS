# Mandate 004 — Developer One Hyper Mandate: Python-first architecture, authorized AI APIs, and JetOS goals

Status: **active, permanent, HYPER MANDATE**
Issued by: **Developer One** (the repository owner), 2026-10-10.
Scope: **JetOS and every Brain Clone, Mac Brain, Digital Yamin, worker, agent runtime, provider broker, and future compatible system that integrates with or modifies JetOS.**

## JetOS is first-class architecture

JetOS is not an incidental repository. Any agent or runtime doing system-level work that may affect JetOS must first familiarize itself with the current `README.md` and relevant live JetOS source/docs and preserve the actual goals stated there.

Agents must distinguish implemented JetOS behavior from planned architecture and must not describe planned capabilities as already working. Familiarity must be refreshed when JetOS materially changes.

Core JetOS goals include a source-oriented, Python-first operating system that can ultimately replace the software stack on a target machine; own/select its boot path; discover capabilities; install only what a device role requires; control enabled machine capabilities through explicit policy; use its own early userspace and Python control plane; account for provenance/dependencies/exceptions; and remain reproducibly rebuildable from pinned source inputs.

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

Brain Clone, Mac Brain, Digital Yamin workers, JetOS, and future compatible systems must preserve this language/dependency/API architecture when they integrate with one another. A cross-system integration must not introduce a forbidden language, Node toolchain, hidden dependency ecosystem, or vendor SDK merely because another subsystem uses one.

This mandate does not loosen privacy, containment, provenance, reproducibility, machine-safety, default-deny networking, or JetOS's existing native-boundary rules.
