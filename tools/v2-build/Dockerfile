FROM debian:bookworm@sha256:d74df7598108a173a621eda4d58a2adbf850b2d9a9d81bc2cca1a6c21174a880

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf automake bc bison build-essential bzip2 ca-certificates cpio curl \
    device-tree-compiler file flex gawk gettext git libelf-dev libncurses-dev \
    libssl-dev libtool patch pkg-config python3 python3-distutils \
    python3-setuptools rsync swig time unzip wget xz-utils zlib1g-dev zstd \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /bin/bash builder \
    && mkdir /work && chown builder:builder /work

LABEL org.opencontainers.image.source="https://github.com/openwrt/openwrt" \
      org.opencontainers.image.version="25.12.6" \
      org.opencontainers.image.revision="64900e756efa667774214f9c6b17c113222e01f7"

USER builder
WORKDIR /work/openwrt
RUN git init . \
    && git remote add origin https://github.com/openwrt/openwrt.git \
    && git fetch --depth 1 origin 64900e756efa667774214f9c6b17c113222e01f7 \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = 64900e756efa667774214f9c6b17c113222e01f7
CMD ["bash"]
