# OS-first Python/JetLang qualification policy

Status: active engineering policy
Authority: repository owner

## Principle

JetLang is a CPython-derived runtime. During standard-library qualification, preserve JetLang behavior by default and make JetOS provide the smallest correct Linux/POSIX environment needed by the supported Python standard-library surface.

A standard-library failure is presumed to be an operating-system, kernel-configuration, early-userspace, mount, device, process, signal, clock, filesystem, networking, loader, library, or build-environment deficiency until evidence distinguishes JetLang from an equivalently built upstream CPython reference.

Do not patch JetLang merely to compensate for an incomplete JetOS environment.

## Required failure order

For every failing, hanging, unavailable, or interrupted CPython-derived standard-library test:

1. Preserve the exact first failure/hang and the last completed test in qualification evidence.
2. Investigate JetOS first: Linux kernel configuration and syscalls; `/proc`, `/sys`, `/dev`, devpts and `/tmp`; permissions and filesystem semantics; fork/exec/wait, pipes and signals; clocks/timers/selectors; threads/synchronization; loopback, sockets and required network setup; dynamic loader/native libraries; environment and early userspace.
3. Prefer one minimal substrate correction that fixes an OS contract for all callers over test-specific or JetLang-specific workarounds.
4. Rebuild the affected JetOS layer and rerun the focused failing test, then resume the full deterministic suite.
5. Change JetLang only when evidence shows that JetOS provides the required contract and an equivalently configured/reference CPython succeeds while JetLang fails, or when the repository owner explicitly authorizes a deliberate JetLang divergence.

## Differential oracle

Where practical, use equivalent upstream CPython behavior as a diagnostic oracle inside the same JetOS environment:

- JetLang fails and reference CPython fails: investigate JetOS first.
- JetLang fails and reference CPython passes: investigate JetLang/build differences.
- Both pass: the capability may proceed to integrated qualification.

The reference runtime is diagnostic evidence only. JetOS must still ship and qualify its source-built JetLang, not substitute an external Python runtime.

## Minimal does not mean incomplete

JetOS should remain small, but process control, filesystems, sockets/networking, signals, timing, threads, polling, memory mapping, terminals and the other Linux/POSIX facilities required by the supported Python standard library are operating-system responsibilities. Do not remove a kernel/userspace capability merely because a reduced image can compile without it. Kernel reduction remains subordinate to integrated JetLang standard-library qualification.

## Shared-code boundary

JetOS and JetLang may share source and evolve toward tighter integration, but ownership follows semantics: ordinary Linux/POSIX facilities belong in the OS substrate; Python-language/runtime semantics belong in JetLang. Shared implementation is not permission to move missing OS responsibilities into JetLang compatibility hacks.

## Qualification evidence

Qualification should record each test/module as it starts and completes so interruption or a hang identifies the exact boundary. A final PASS marker remains mandatory; progress markers do not convert interrupted, skipped, unavailable, or hanging tests into passes.
