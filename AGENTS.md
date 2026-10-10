# JetOS agent instructions

Before changing JetOS, read:

1. `README.md` — current JetOS goals, implemented state, planned architecture, language constitution, native boundaries, capability model, provenance, and reproducibility goals.
2. `ARCHITECTURES.md` — the first-class dual-architecture contract for x86-64 and ARM64/AArch64, including the rule that one shared JetOS exists above isolated machine-specific boundaries.
3. `MANDATE_004.md` — Developer One's active permanent Hyper Mandate covering Python-first implementation, zero/minimal dependencies, no Node.js, API-first authorized AI integrations, JetOS familiarity, source reuse/minimization, dual-architecture support, and the explicit xAI/Grok prohibition.

Do not rely on a stale summary when these files have materially changed.

For project-owned executable logic, CPython is the default and predominant implementation environment. Another general-purpose language is not an alternate backend/tooling choice. C and assembly remain only the narrow native/architectural exceptions described by JetOS itself and `MANDATE_004.md`.

JetOS has two first-class CPU targets: `x86_64` and `arm64`/AArch64. Shared JetOS logic must remain architecture-neutral wherever practical; architecture-specific behavior belongs only at genuine machine, kernel, boot, firmware, device, or native-code boundaries. Neither target is a secondary port.

Node.js and its package ecosystem are forbidden. Browser JavaScript is allowed only for a genuine browser frontend and must not introduce Node or a JavaScript build/package stack.

Third-party dependencies are zero/minimal by default. Prefer Python's standard library and direct documented APIs over SDK/client-library dependencies. Imported native operating-system/toolchain substrate must remain explicit, pinned, provenance-accounted, and minimized.
