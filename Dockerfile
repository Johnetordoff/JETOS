ARG BASE_IMAGE=debian:trixie-slim
FROM ${BASE_IMAGE} AS base

ENV DEBIAN_FRONTEND=noninteractive

# Bootstrap provider mapping for JETOS build capabilities. The container's
# Python is deliberately only a build/orchestration interpreter. It is NOT the
# JetOS/JetLang runtime: Fat/dev builds compile that runtime from the pinned
# source/cpython lineage before packaging the guest filesystem.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
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
ENV JETOS_BOOTSTRAP_PYTHON=/usr/bin/python3
# ccache fingerprints compiler/preprocessor inputs and compiler identity. The
# cache lives outside .build so a source-revision cleanup cannot silently make
# it stale or destroy it. Compiler identity is checked by content rather than
# only timestamp; no unsafe sloppiness options are enabled.
ENV CCACHE_DIR=/jetos/.jetos-cache/ccache
ENV CCACHE_COMPILERCHECK=content
ENV CC="ccache cc"

# Reproducible repository/userspace qualification. The two large frozen source
# trees are excluded from this image-build context; this stage tests the
# JETOS-owned orchestration contract with the bootstrap interpreter. It does
# not create the JetOS runtime. The dev/Fat path below binds the complete
# checkout and builds JetLang from source/cpython.
FROM base AS test
COPY . /jetos
RUN python3 tools/docker_contract.py
RUN python3 tools/container_os_qualify.py --phase build --require-toolchain
RUN python3 jetos.py test
CMD ["python3", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]

# Fat development environment. `python3 jetos.py dev` bind-mounts the checkout
# (including initialized source trees) at /jetos before build/QEMU work.
# tools/dev.py copies and patches source/cpython, builds and installs JetLang,
# qualifies its standard library, and passes that source-built runtime to the
# packager. The bootstrap /usr/bin/python3 must never be packaged as JetLang.
# Keep .build on Docker-native Linux storage rather than the macOS bind mount:
# Linux/CPython source preparation and compiler output contain very large
# numbers of small files and are dramatically slower over Docker Desktop file
# sharing. The build-revision marker still invalidates stale artifacts.
# On Apple Silicon, jetos.py pins this image/run to linux/arm64. Debian's
# qemu-system-arm package supplies qemu-system-aarch64; fail the image build
# immediately if that or the native ARM64 build toolchain is unavailable.
FROM base AS dev
VOLUME ["/jetos/.build"]
RUN command -v python3 \
    && command -v qemu-system-aarch64 \
    && command -v ccache \
    && ccache --version \
    && command -v cc \
    && command -v make \
    && command -v ld
CMD ["python3", "jetos.py", "doctor"]
