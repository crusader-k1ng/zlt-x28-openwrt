#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Run in the existing native ARM64 build container; creates offline, non-flashable artifacts.
set -euo pipefail
[ "$#" -eq 1 ] || { echo "Usage: build.sh NEW_OUTPUT_DIRECTORY" >&2; exit 1; }
root=$(cd "$(dirname "$0")" && pwd)
ow=/work/openwrt
kernel=$ow/build_dir/target-aarch64_generic_musl/linux-armsr_armv8/linux-6.12.112
[ "$(git -C "$ow" rev-parse HEAD)" = 64900e756efa667774214f9c6b17c113222e01f7 ]
[ -s "$kernel/arch/arm64/boot/Image" ]
[ "$(uname -m)" = aarch64 ]
mkdir "$1" # Refuse existing output, including an earlier incomplete build.
out=$(cd "$1" && pwd)
touch "$out/INCOMPLETE"
printf 'Offline experimental components only; no boot container or hardware approval.\n' > "$out/NOT-FLASHABLE"
export STAGING_DIR=$ow/staging_dir/target-aarch64_generic_musl
export PATH=$ow/staging_dir/toolchain-aarch64_generic_gcc-14.3.0_musl/bin:$PATH
export CROSS_COMPILE=aarch64-openwrt-linux-musl-
export ARCH=arm64
export KBUILD_BUILD_TIMESTAMP='2026-11-11 00:00:00 UTC'
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=x28-v2
cp "$kernel/.config" "$out/baseline.config"
# A separate source/build copy preserves the successful generic build and its configuration.
cp -a "$kernel" "$out/linux"
make -C "$out/linux" clean
"$out/linux/scripts/config" --file "$out/linux/.config" \
    -e ARCH_MEDIATEK -e SERIAL_8250_MT6577 -e SERIAL_8250_CONSOLE \
    -e BLK_DEV_INITRD -e PROC_FS -e SYSFS -e TMPFS -e BINFMT_ELF \
    -d CMDLINE_FORCE -d MTD -d BLOCK -d PCI -d USB_SUPPORT \
    -e NET -d NETDEVICES -d INET -d IPV6 -d NETFILTER -d WIRELESS \
    -d CPU_FREQ -d CPU_IDLE -d WATCHDOG -d EFI -d DRM -d SOUND -d FB
make -C "$out/linux" olddefconfig
for option in ARCH_MEDIATEK SERIAL_8250_MT6577 SERIAL_8250_CONSOLE BLK_DEV_INITRD PROC_FS SYSFS TMPFS BINFMT_ELF; do
    grep -qx "CONFIG_$option=y" "$out/linux/.config"
done
for option in MTD BLOCK PCI USB_SUPPORT NETDEVICES INET IPV6 NETFILTER WATCHDOG; do
    if grep -qx "CONFIG_$option=y" "$out/linux/.config"; then
        echo "Unexpected hardware subsystem enabled: $option" >&2; exit 1
    fi
done
make -C "$out/linux" -j4 Image
cp "$out/linux/arch/arm64/boot/Image" "$out/Image"
cp "$out/linux/.config" "$out/kernel.config"
dtc -I dts -O dtb -o "$out/mt6890-serial.dtb" "$root/mt6890-serial.dts"

# Match OpenWrt 25.12.6's BusyBox source, but build only static serial diagnostics.
archive=$ow/dl/busybox-1.37.0.tar.bz2
if [ ! -f "$archive" ]; then
    curl -fL --retry 3 https://www.busybox.net/downloads/busybox-1.37.0.tar.bz2 -o "$archive"
fi
echo "3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4  $archive" | sha256sum -c -
tar -xf "$archive" -C "$out"
bb=$out/busybox-1.37.0
make -C "$bb" allnoconfig
for option in STATIC ASH SH_IS_ASH ASH_JOB_CONTROL ASH_ALIAS ASH_ECHO ASH_PRINTF \
    FEATURE_SH_STANDALONE FEATURE_SH_NOFORK CAT ECHO PRINTF LS MOUNT \
    UNAME DMESG GREP HEXDUMP SLEEP SETSID CTTYHACK; do
    "$out/linux/scripts/config" --file "$bb/.config" -e "$option"
done
make -C "$bb" oldconfig < <(yes '')
for option in STATIC ASH CAT MOUNT SETSID CTTYHACK; do
    grep -qx "CONFIG_$option=y" "$bb/.config"
done
make -C "$bb" -j4
"${CROSS_COMPILE}readelf" -h "$bb/busybox" | grep -q AArch64
if "${CROSS_COMPILE}readelf" -l "$bb/busybox" | grep -q INTERP; then
    echo 'BusyBox must not require a dynamic loader' >&2; exit 1
fi
cp "$bb/.config" "$out/busybox.config"
cp "$root/init" "$out/init"
{
    printf 'dir /bin 755 0 0\ndir /dev 755 0 0\ndir /proc 555 0 0\ndir /sys 555 0 0\ndir /tmp 1777 0 0\n'
    printf 'nod /dev/console 600 0 0 c 5 1\nnod /dev/null 666 0 0 c 1 3\n'
    printf 'nod /dev/ttyS0 600 0 0 c 4 64\nnod /dev/ttyAMA0 600 0 0 c 204 64\n'
    printf 'file /init %s/init 755 0 0\nfile /bin/busybox %s/busybox 755 0 0\n' "$out" "$bb"
    for applet in sh cat echo printf ls mount uname dmesg grep hexdump sleep setsid cttyhack; do
        printf 'slink /bin/%s busybox 777 0 0\n' "$applet"
    done
} > "$out/initramfs.list"
# Uncompressed: the baseline kernel does not enable CONFIG_RD_GZIP.
"$out/linux/usr/gen_init_cpio" -t 0 "$out/initramfs.list" > "$out/initramfs.cpio"
(cd "$out"; cpio -it < initramfs.cpio > initramfs.contents)
{
    git -C "$ow" rev-parse HEAD
    "${CROSS_COMPILE}gcc" --version
    sha256sum "$root/build.sh" "$root/init" "$root/mt6890-serial.dts" "$ow/target/linux/generic/kernel-6.12" "$archive"
} > "$out/provenance.txt"
(cd "$out"; sha256sum Image mt6890-serial.dtb initramfs.cpio kernel.config busybox.config baseline.config init provenance.txt > sha256sums)
rm "$out/INCOMPLETE"
ls -lh "$out/Image" "$out/initramfs.cpio" "$out/mt6890-serial.dtb"
