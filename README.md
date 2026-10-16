# JETOS

JETOS is its own source-built Linux distribution with JetLang as its primary userspace/runtime language.

The canonical operating-system source estate lives under `source/`:

- `source/linux/` — JetOS-owned kernel source;
- `source/cpython/` — CPython-derived JetLang source;
- `source/shared/` — native source shared by the integrated runtime;
- `source/ports/` — adapted dependency/native source.

JetOS is **not** a renamed Gentoo, Debian, Ubuntu, Alpine, or other Linux distribution. Historical Gentoo work informed earlier configuration and build decisions, but Gentoo is now provenance/reference only and creates no runtime, build-base, package-manager, or rolling-update obligation.

## Source ownership

The target repository state is one outer JETOS repository containing ordinary tracked Linux and JetLang source trees with no nested Git metadata. Current source gitlinks are transitional only until the exact pinned trees are safely absorbed.

Once absorbed, upstream Linux movement does not automatically make JetOS “behind.” Kernel changes are deliberate JetOS integrations made for a defined reason and qualified as JetOS changes.

JetLang follows a different policy: CPython remains an upstream compatibility/change stream. JetLang currently stabilizes on the Python 3.14 lineage; later CPython changes are reviewed and selectively integrated into the JetLang-owned tree rather than replacing it wholesale.

## Build model

Raw source necessarily needs already-executable bootstrap tooling for the first compile. That toolchain is external build machinery, not part of the JetOS distribution.

A native Linux environment with the required compiler/linker/build tools can build directly from the repository source. Docker is optional isolation/testing only. The repository deliberately chooses no Docker distribution base; if the Docker harness is used, the caller supplies an external tooling image through `JETOS_BOOTSTRAP_IMAGE`.

The bootstrap environment must never become the JetOS runtime. The JetOS kernel is built from `source/linux`; JetLang and its supported standard library are built from `source/cpython` after JetOS patching and qualification.

## Fat and Skinny

**Fat Mode** contains source, build, diagnostic, development, and qualification material. It may include complete source trees and toolchain-facing artifacts.

**Skinny Mode** is the target-specific runtime projection. It omits complete source trees, tests, temporary development material, and external bootstrap tooling while preserving the qualified runtime required by JetOS.

## Current CPU targets

JETOS has three first-class targets:

- `x86_64`
- `armv7`
- `arm64` / AArch64

The ODROID-HC1 is the current physical reference target and is ARMv7.

## Development

The direct source build is owned by `tools/dev.py`. It prepares the vendored source lineages, builds JetLang, qualifies the supported standard-library surface, builds the JetOS kernel, packages the root filesystem/initramfs, and can boot the result through QEMU where supported.

The optional Docker harness is entered through `jetos.py docker-test` or `jetos.py dev` after supplying `JETOS_BOOTSTRAP_IMAGE`. Docker is not required by a running JetOS image and is not a JetOS runtime dependency.

See `ARCHITECTURE.md` and `MANDATE.md` for the canonical architecture and policy.
