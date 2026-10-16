# Docker and JetOS

Docker is **optional external build/test machinery**. It is not part of JetOS, is not required by a running JetOS system, and does not define the JetOS distribution.

JetOS is built from the source estate under `source/`, primarily `source/linux` and `source/cpython`. A native Linux machine with a qualifying compiler/toolchain can run the repository-owned build directly.

The repository Dockerfile deliberately has no Debian, Gentoo, Ubuntu, Alpine, Python, or other default distribution base. If Docker isolation is useful, the caller supplies `JETOS_BOOTSTRAP_IMAGE`, which must already contain the tools required by the harness (`python3`, Git, C compiler/linker/build tools, ccache, QEMU, and strace).

That bootstrap image is disposable infrastructure. It must never supply the kernel or JetLang runtime installed into JetOS. `tools/dev.py` builds those from the JetOS-owned source trees.

Example shape:

```sh
JETOS_BOOTSTRAP_IMAGE=<external-tooling-image> python3 jetos.py docker-test
JETOS_BOOTSTRAP_IMAGE=<external-tooling-image> python3 jetos.py dev
```

No specific bootstrap image is canonical. Choosing or maintaining one is outside the JetOS distribution contract.

The target source-control architecture is a single repository with the Linux and JetLang source trees vendored as ordinary tracked files. Transitional source gitlinks may remain only until the exact pinned trees are safely absorbed.
