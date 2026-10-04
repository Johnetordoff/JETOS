FROM python:3.14.8-slim

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
        tcl-dev \
        tk-dev \
        libx11-dev \
        qemu-system-x86 \
        qemu-system-arm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /jetos
COPY . /jetos

ENV PYTHONPATH=/jetos/src
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN python tools/test.py
RUN python tools/test_unicode.py
RUN python tools/test_language.py
RUN python tools/test_bootstrap.py
RUN python tools/test_capabilities.py
RUN python tools/test_desktop.py
RUN python tools/test_policy.py
RUN python tools/test_interpreters.py

CMD ["python", "jetos.py", "doctor"]
