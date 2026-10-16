# JetOS Environment Qualification Priority

This file is a repository-level engineering directive. It governs platform qualification work until explicitly superseded.

## Required order

JetOS environments are qualified sequentially. Do not advance to a later environment until the current environment is fully green.

1. **Linux x86-64** — current and sole engineering priority.
2. **Intel macOS x86-64**.
3. **Apple Silicon M1 / arm64**.
4. **Other ARM infrastructures and environments**.

Work on later environments must not displace the current gate. Avoid unrelated portability, source-reduction, LOC, and documentation-only work while the active environment still has unrun or failing qualification tests.

## Definition of full green

For each environment, one exact revision must prove the canonical end-to-end flow using newly built artifacts:

- build the JetLang/CPython-derived interpreter for the target architecture;
- build the JetOS kernel and required Fat image/initramfs for that target;
- boot the new kernel in the repository-supported runtime/QEMU configuration;
- launch the new interpreter inside that new runtime and reach the interactive `jetos>` prompt;
- verify interpreter identity/version/platform, imports, filesystem, subprocess/process behavior, environment handling, sockets/loopback, supported native extensions, clean exit, and restart;
- run all repository-native Python/JetLang tests; and
- run the complete practical CPython-derived standard-library regression suite inside the same new runtime with canonical CPython test machinery (`python -m test`) or the repository's equivalent wrapper.

A test is green only when it actually ran and passed on the exact qualifying revision and target runtime. Skipped, unavailable, interrupted, or unrun tests are not passes and must be recorded separately with exact names/reasons where applicable. Host-only tests do not substitute for in-runtime tests.

## Failure loop

For the active environment, always take the first concrete failure, make the smallest evidence-supported repair, rebuild/reboot from the earliest affected stage, rerun the failing test first, and then immediately resume the deterministic remaining suite. If the suite requires multiple sessions, persist the exact completed, failing, skipped, unavailable, interrupted, and remaining test modules so work resumes without losing coverage.

## Current gate

**Linux x86-64 is the current gate.** Intel macOS x86-64, M1/arm64, and other ARM environments remain downstream until Linux x86-64 satisfies the full-green definition above.

Do not use GitHub Actions as a substitute for the canonical target-runtime qualification flow.
