ARG PYTHON_IMAGE=python:3.14.8-slim
FROM ${PYTHON_IMAGE} AS base

ENV DEBIAN_FRONTEND=noninteractive

# Bootstrap provider mapping for JETOS build capabilities. JETOS-owned code
# asks for semantic capabilities (C compiler, linker, kernel-build tools), not
# for a compiler vendor. This Debian-based container currently provides those
# capabilities with the packages below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        gcc \
        make \
        binutils \
        libc6-dev \
        bc \
        bison \
        flex \
        ccache \
        libssl-dev \
        libelf-dev \
        dwarves \
        pkg-config \
        libffi-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        liblzma-dev \
        libgdbm-dev \
        libgdbm-compat-dev \
        tk-dev \
        uuid-dev \
        xz-utils \
        qemu-system-x86 \
        qemu-system-arm \
        strace \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /jetos
ENV PYTHONPATH=/jetos/src
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV JETOS_CONTAINER=1
# ccache fingerprints compiler/preprocessor inputs and compiler identity. The
# cache lives outside .build so a source-revision cleanup cannot silently make
# it stale or destroy it. Compiler identity is checked by content rather than
# only timestamp; no unsafe sloppiness options are enabled.
ENV CCACHE_DIR=/jetos/.jetos-cache/ccache
ENV CCACHE_COMPILERCHECK=content
ENV CC="ccache cc"

# Reproducible JETOS userspace qualification. The two large frozen source
# submodules are excluded from this build context because this stage tests the
# JETOS-owned operating-system userspace and repository contract, not a full
# kernel/CPython rebuild.
FROM base AS test
COPY . /jetos
RUN python tools/docker_contract.py
RUN python tools/container_os_qualify.py --phase build --require-toolchain
RUN python jetos.py test
CMD ["python", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]

# Fat development environment. `python jetos.py dev` bind-mounts the checkout
# (including initialized source trees) at /jetos before build/QEMU work.
# Keep .build on Docker-native Linux storage rather than the macOS bind mount:
# Linux/CPython source preparation and compiler output contain very large
# numbers of small files and are dramatically slower over Docker Desktop file
# sharing. The build-revision marker still invalidates stale artifacts.
# On Apple Silicon, jetos.py pins this image/run to linux/arm64. Debian's
# qemu-system-arm package supplies qemu-system-aarch64; fail the image build
# immediately if that or the native ARM64 build toolchain is unavailable.
FROM base AS dev
VOLUME ["/jetos/.build"]
RUN command -v qemu-system-aarch64 \
    && command -v ccache \
    && ccache --version \
    && command -v cc \
    && command -v make \
    && command -v ld
CMD ["python", "jetos.py", "doctor"]

# Temporary execution-capable Linux/x86_64 GreenGate proving ground.
# Render builds the final stage on a real Linux Docker builder. The normal
# Docker context intentionally omits the large source submodules, so this stage
# fetches the exact pinned public upstream commits, then runs the repository
# tests, builds NEW JetLang + NEW kernel + Fat image, boots QEMU under TCG, and
# fails the image build unless the in-guest loopback/web qualifier passes.
# This stage is evidence tooling only; it does not replace `python3 jetos.py dev`.
FROM dev AS render-qualify
COPY . /jetos
RUN set -eux; \
    rm -rf source/linux source/cpython; \
    git clone --filter=blob:none --no-checkout https://github.com/gregkh/linux.git source/linux; \
    git -C source/linux fetch --depth 1 origin 6d15a1029d425b15c59463910ebdccc4afe760d6; \
    git -C source/linux checkout --detach 6d15a1029d425b15c59463910ebdccc4afe760d6; \
    git clone --filter=blob:none --no-checkout https://github.com/python/cpython.git source/cpython; \
    git -C source/cpython fetch --depth 1 origin 8e6e75d9102e39bed2a2b279203a396741180f12; \
    git -C source/cpython checkout --detach 8e6e75d9102e39bed2a2b279203a396741180f12; \
    python jetos.py test; \
    python tools/dev.py build; \
    python tools/boot_smoke.py
CMD ["python", "-m", "http.server", "10000"]
