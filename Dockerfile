ARG PYTHON_IMAGE=python:3.14.8-slim
FROM ${PYTHON_IMAGE} AS base

ENV DEBIAN_FRONTEND=noninteractive

# Bootstrap provider mapping for JETOS build capabilities.  JETOS-owned code
# asks for semantic capabilities (C compiler, linker, kernel-build tools), not
# for a compiler vendor.  This Debian-based container currently provides those
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
ENV CC=cc

# Reproducible JETOS userspace qualification.  The two large frozen source
# submodules are excluded from this build context because this stage tests the
# JETOS-owned operating-system userspace and repository contract, not a full
# kernel/CPython rebuild.
FROM base AS test
COPY . /jetos
RUN python tools/docker_contract.py
RUN python tools/container_os_qualify.py --phase build --require-toolchain
RUN python jetos.py test
CMD ["python", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]

# Fat development environment.  `python jetos.py dev` bind-mounts the checkout
# (including initialized vendor submodules) at /jetos before build/QEMU work.
FROM base AS dev
CMD ["python", "jetos.py", "doctor"]
