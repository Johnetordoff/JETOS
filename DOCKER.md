# JETOS Docker development and qualification

JETOS uses Docker as a **Fat-mode development and operating-system qualification environment**. Docker is not part of the Skinny HC1 runtime and is not a substitute for physical HC1 qualification.

**GitHub Actions are forbidden.** The Docker path is repository-owned local/native tooling. Jenkins may trigger the same Git command/checkout and `python3 jetos.py docker-test`, but Jenkins is only a scheduler/executor; the test definition remains in JETOS itself.

## What “JETOS in Docker” means

The Docker test container is treated as a real JETOS **userspace operating-system environment**: JETOS owns the userspace being qualified and exercises filesystems, mmap, process creation, selectors, Unix sockets, shared memory, `/proc`, `/sys`, `/dev`, and the selected build capabilities from inside that environment.

Docker does **not** provide an independent kernel. The container shares the host Linux kernel. JETOS Gen 2 therefore reports this honestly as:

```text
userspace = JETOS
kernel_model = shared host Linux kernel
```

The runtime qualifier runs as PID 1 inside the test container. That lets JETOS exercise its container userspace as the sole intended userspace under test without pretending Docker booted a separate JETOS kernel.

## One-command Docker test

```text
python jetos.py docker-test
```

The command first proves that both parts of the host Docker capability exist:

1. the `docker` CLI executable is available;
2. the Docker daemon is reachable.

If the CLI is absent, JETOS says that directly. If the CLI exists but the daemon/socket/remote Docker host is unavailable, JETOS reports Docker's daemon diagnostic. There is no silent fallback to GitHub Actions or another hosted system.

Then it:

1. builds the Dockerfile `test` target from `python:3.14.8-slim`;
2. runs the container build-phase OS/capability qualifier;
3. runs the full ordinary repository test suite inside the image;
4. starts the resulting image;
5. runs the JETOS runtime OS qualifier as container PID 1.

The runtime qualifier checks the Python version, Linux substrate, `/proc`, `/sys`, `/dev`, file I/O, mmap, symlinks, selectors, Unix sockets, subprocess creation, shared memory, and required Fat-mode tool capabilities.

A machine executing this test therefore needs a working Docker installation and access to any uncached base-image/package sources needed by `docker build`. A Jenkins worker can provide that environment directly; the repository does not attempt to install or secretly substitute a container engine during qualification.

## Tool capabilities, not vendor names

JETOS-owned code names what it needs by **capability**. For example:

- C compiler;
- linker;
- build orchestrator;
- parser generator;
- lexer generator;
- kernel debug-info tool;
- package-configuration query tool;
- x86 and ARM system emulators;
- system-call tracer.

JETOS-owned native tests use `CC` and default to the conventional `cc` command. They do not hard-code `gcc` as the operating-system interface.

The current Debian-based Docker bootstrap happens to satisfy the C-compiler capability with the `gcc` package and maps the other capabilities to Debian packages. That package/provider mapping is bootstrap implementation detail, not the permanent JETOS capability name. JETOS does not yet declare one compiler vendor as part of its OS contract.

## Jenkins on Git

A repository `Jenkinsfile` invokes:

```text
python3 jetos.py docker-test
```

A Jenkins worker therefore needs Git, Python 3 to invoke JETOS tooling, and access to a working Docker CLI/daemon. Jenkins does not duplicate test logic and does not introduce GitHub Actions.

## Development / QEMU container

```text
python jetos.py dev --build-only
python jetos.py dev
```

The `dev` target supplies the Fat-mode capabilities required to compile C, link native artifacts, build the Linux kernel, inspect system calls, and emulate x86/ARM targets. The current checkout is bind-mounted at `/jetos` so the Fat environment operates on the exact working tree rather than on a stale image copy.

The two large frozen source submodules, `vendor/linux` and `vendor/cpython`, are deliberately excluded from the ordinary Docker test build context. For full Fat builds they remain in the host checkout and become visible through the bind mount. Initialize them before a full build with normal Git source acquisition.

## Dockerfile targets

- `base` — Python 3.14.8 plus the current bootstrap providers for JETOS build/test/emulation capabilities.
- `test` — lightweight repository copy, OS/capability qualification, and the full repository test suite.
- `dev` — Fat development environment; the checkout is supplied at runtime through a bind mount.

## Qualification boundary

Docker qualification answers: **does the JETOS-owned userspace and Python-facing OS contract behave correctly in a controlled Linux container environment?**

It does not by itself prove:

- the JETOS kernel boots;
- ARMv7 cross/native artifacts are correct;
- the HC1 device tree or bootloader is correct;
- Ethernet/SATA/thermal behavior works on the physical HC1;
- a Skinny image preserves the complete protected Python surface.

Those remain separate QEMU and physical-hardware gates.
