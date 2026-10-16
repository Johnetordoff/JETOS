ARG JETOS_BOOTSTRAP_IMAGE
FROM ${JETOS_BOOTSTRAP_IMAGE} AS base

# Docker is optional development/test machinery, not the JetOS distribution
# substrate. This image deliberately installs no Debian, Gentoo, or other
# distribution packages. Callers must provide a bootstrap image/toolchain that
# already exposes the capabilities below. JetOS itself is built from the
# vendored source estate under source/.
WORKDIR /jetos
ENV PYTHONPATH=/jetos/src
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV JETOS_CONTAINER=1
ENV JETOS_BOOTSTRAP_PYTHON=/usr/bin/python3
ENV CCACHE_DIR=/jetos/.jetos-cache/ccache
ENV CCACHE_COMPILERCHECK=content
ENV CC="ccache cc"

RUN command -v python3 \
    && command -v git \
    && command -v cc \
    && command -v make \
    && command -v ld \
    && command -v ccache \
    && command -v qemu-system-x86_64 \
    && command -v qemu-system-arm \
    && command -v qemu-system-aarch64 \
    && command -v strace

# Repository/userspace qualification only. The large vendored source trees are
# excluded from the image-build context; this target does not define JetOS's
# runtime or distribution identity.
FROM base AS test
COPY . /jetos
RUN python3 tools/docker_contract.py
RUN python3 tools/container_os_qualify.py --phase build --require-toolchain
RUN python3 jetos.py test
CMD ["python3", "tools/container_os_qualify.py", "--phase", "runtime", "--require-toolchain"]

# Optional Fat development harness. `jetos.py dev` bind-mounts the complete
# checkout, then tools/dev.py builds the kernel from source/linux and JetLang
# from source/cpython. The bootstrap image is external machinery only.
FROM base AS dev
VOLUME ["/jetos/.build"]
CMD ["python3", "jetos.py", "doctor"]
