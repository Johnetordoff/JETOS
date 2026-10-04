FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /jetos
COPY . /jetos

ENV PYTHONPATH=/jetos/src
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN python tools/test.py
RUN python tools/test_unicode.py

CMD ["/bin/bash"]
