# JETOS Docker development and qualification

JETOS uses Docker as a **Fat-mode development and qualification environment**. Docker is not part of the Skinny HC1 runtime and is not a substitute for physical HC1 qualification.

The container path is local/native repository tooling. It does not use GitHub Actions.

## One-command Docker test

```text
python jetos.py docker-test
```

This performs two steps:

1. builds the Dockerfile `test` target from `python:3.14.8-slim`;
2. starts the resulting image and verifies the exact Python 3.14.8 runtime plus a JETOS hardware-snapshot smoke test.

The Docker build itself runs:

```text
python jetos.py test
```

so a successful `docker-test` proves the ordinary repository test suite passed inside the container before the smoke container is started.

## Development / QEMU container

```text
python jetos.py dev --build-only
python jetos.py dev
```

The `dev` target contains the compiler, kernel-build prerequisites, QEMU for x86 and ARM, and `strace`. The current checkout is bind-mounted at `/jetos` so the Fat environment operates on the exact working tree rather than on a stale image copy.

The two large frozen source submodules, `vendor/linux` and `vendor/cpython`, are deliberately excluded from the ordinary Docker build context. For full Fat builds they remain in the host checkout and become visible through the bind mount. Initialize them before a full build with normal Git source acquisition.

## Dockerfile targets

- `base` — Python 3.14.8 plus JETOS build/test/QEMU prerequisites.
- `test` — lightweight repository copy plus full repository qualification; intended for `docker-test`.
- `dev` — Fat development toolchain; the checkout is supplied at runtime through a bind mount.

## Qualification boundary

Docker qualification answers: **does the JETOS-owned userspace/tooling behave correctly in a controlled Linux development environment?**

It does not by itself prove:

- the JETOS kernel boots;
- ARMv7 cross/native artifacts are correct;
- the HC1 device tree or bootloader is correct;
- Ethernet/SATA/thermal behavior works on the physical HC1;
- a Skinny image preserves the complete protected Python surface.

Those remain separate VM and physical-hardware gates.
