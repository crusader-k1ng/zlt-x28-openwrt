#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
image=x28-v2-build:25.12.6
volume=x28-v2-openwrt-25.12.6

case "${1:-}" in
 build)
  shift
  exec docker build --platform linux/arm64 -t "$image" "$@" "$repo/tools/v2-build"
  ;;
 check)
  shift
  [ "$#" -eq 0 ] || { echo 'Usage: run.sh check' >&2; exit 1; }
  set -- make -f include/prereq-build.mk prereq TOPDIR=/work/openwrt HOST_OS=Linux V=s
  ;;
 shell) shift; set -- bash "$@" ;;
esac
[ "$#" -gt 0 ] || set -- bash
set -- --rm --init --cap-drop ALL --security-opt no-new-privileges \
 --mount "type=volume,src=$volume,dst=/work" \
 --mount "type=bind,src=$repo,dst=/x28,readonly" \
 --workdir /work/openwrt "$image" "$@"
if [ -t 0 ] && [ -t 1 ]; then set -- -it "$@"; fi
exec docker run "$@"
