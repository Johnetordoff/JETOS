ARG PYTHON_IMAGE=python:3.14.8-slim
FROM ${PYTHON_IMAGE} AS base

ENV DEBIAN_FRONTEND=noninteractive

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

# Fast, reproducible repository qualification.  The two large frozen source
# submodules are excluded from this build context because this stage tests the
# JETOS-owned repository/tooling contract, not a kernel/CPython rebuild.
FROM base AS test
COPY . /jetos
RUN python tools/docker_contract.py
RUN python jetos.py test
CMD ["python", "jetos.py", "test"]

# Fat development toolchain.  `python jetos.py dev` bind-mounts the checkout
# (including initialized vendor submodules) at /jetos before build/QEMU work.
FROM base AS dev
CMD ["python", "jetos.py", "doctor"]
