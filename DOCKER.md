# JETOS Docker development and qualification

JETOS uses Docker as a **Fat-mode development and operating-system qualification environment**. Docker is not part of the Skinny HC1 runtime and is not a substitute for physical HC1 qualification.

**GitHub Actions are forbidden.** The Docker path is repository-owned local/native tooling. Jenkins may schedule a JETOS Work Server cycle, but Jenkins is only a scheduler/executor; the build and qualification definitions remain in JETOS itself.

## What “JETOS in Docker” means

The Docker test container is treated as a real JETOS **userspace operating-system environment**: JETOS owns the userspace being qualified and exercises filesystems, mmap, process creation, selectors, Unix sockets, shared memory, `/proc`, `/sys`, `/dev`, and selected build capabilities from inside that environment.

Docker does **not** provide an independent kernel. The container shares the host Linux kernel. JETOS Gen 2 therefore reports this honestly as:

```text
userspace = JETOS
kernel_model = shared host Linux kernel
```

The runtime qualifier runs as PID 1 inside the test container. That exercises the container userspace as the sole intended userspace under test without pretending Docker booted a separate JETOS kernel.

## One-command Docker test

```text
python jetos.py docker-test
```

The command proves that the Docker CLI exists and the Docker daemon is reachable, then builds the `test` target, runs build-phase OS/capability qualification, runs the repository tests, and starts the resulting image with the runtime qualifier as PID 1. There is no hosted-CI fallback.

JETOS-owned code names tool needs by capability rather than vendor. Native tests use `CC`, defaulting to `cc`. The current Debian image happens to supply those capabilities with packages such as GCC, binutils, QEMU, and strace; that provider mapping is bootstrap detail, not permanent JETOS identity.

## Jenkins and the Work Server

The repository `Jenkinsfile` invokes:

```text
python3 tools/work_server.py run-cycle
```

The Work Server owns the normal gates, including:

```text
python jetos.py docker-test
python jetos.py dev --build-only
```

Automated bounded improvements are not authorized to rewrite `source/linux` or `source/cpython`; changes to those integrated native lineages require the stronger qualification contract in `MANDATE.md` and `ARCHITECTURE.md`.

## Development / QEMU container

```text
python jetos.py dev --build-only
python jetos.py dev
```

The `dev` target supplies Fat-mode capabilities required to compile C, link native artifacts, build the Linux kernel, inspect system calls, and emulate x86/ARM targets. The current checkout is bind-mounted at `/jetos` so the Fat environment operates on the exact working tree.

The large `source/linux` and `source/cpython` trees are deliberately excluded from the ordinary Docker test build context. Full Fat builds use the initialized source in the bind-mounted checkout. Fat builds retain source and qualification material; Skinny images intentionally omit complete development source trees and the development test suite.

## Dockerfile targets

- `base` — Python 3.14.8 plus bootstrap providers for build/test/emulation capabilities.
- `test` — lightweight repository copy, OS/capability qualification, and repository tests.
- `dev` — Fat development environment with the checkout supplied by bind mount.

## Qualification boundary

Docker qualification proves the JETOS-owned userspace and Python-facing OS contract in a controlled Linux container. It does not by itself prove the JETOS kernel boots, target-specific artifacts are correct, the HC1 device tree/bootloader works, or physical Ethernet/SATA/thermal behavior works. Runtime-affecting source changes must additionally satisfy the integrated kernel + JetLang qualification described in `MANDATE.md` and `ARCHITECTURE.md`.
