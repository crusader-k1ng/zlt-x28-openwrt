# v2 OpenWrt build environment

Native Linux ARM64 environment for the MT6890 port, based on **OpenWrt 25.12.6**
(commit `64900e756efa667774214f9c6b17c113222e01f7`, MediaTek kernel **6.12.112**).
This prepares the upstream build system; it does not add an MT6890 target.

From this repository's `v2` worktree:

```sh
tools/v2-build/run.sh build
tools/v2-build/run.sh check
tools/v2-build/run.sh shell
```

Or run a command directly:

```sh
tools/v2-build/run.sh git status --short
tools/v2-build/run.sh make menuconfig
```

The image is `x28-v2-build:25.12.6`. It runs as `builder` (UID 1000), with no Docker
socket or device access. Source, downloads and build output live in Docker's
case-sensitive named volume **`x28-v2-openwrt-25.12.6`**, at `/work/openwrt` inside
the container. The first run seeds that volume from the image. Later runs retain
changes and build caches; rebuilding the image does not reset the volume.
Do not run two builds against that volume simultaneously.

The repository is mounted read-only at `/x28` for access to porting patches.
Keep changes intended for Git in this repository; the volume is a working build
tree, not their only copy. The host worktree's `.git` metadata is not usable
through this mount; use host Git for this repository.

The base-image digest and upstream source commit are pinned. Debian packages
come from the configured Bookworm repositories at image-build time and are not
snapshot-pinned. Reuse the built image for a consistent local environment.
OpenWrt builds its own target toolchain; a preinstalled vendor cross-compiler is
not needed. Feeds have not been fetched or installed yet.

`check` runs upstream `include/prereq-build.mk` directly, with `HOST_OS=Linux`,
which checks the host tools/compiler, libc headers and case-sensitive filesystem.
This avoids the top-level `make prereq` launching menuconfig before an MT6890
target/configuration exists. No checks are suppressed. No MT6890 firmware is compiled or approved to flash.
Docker currently has about 7.75 GiB RAM; start actual builds with `-j4` and adjust
only after measuring memory use.

References: [OpenWrt host checks](https://github.com/openwrt/openwrt/blob/v25.12.6/include/prereq-build.mk),
[kernel version](https://github.com/openwrt/openwrt/blob/v25.12.6/target/linux/generic/kernel-6.12).
