#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only X28 load-layout audit. Does NOT build, authenticate or approve a boot image."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

STOCK_SHA = "c8cc8244078cb6539c72842540250bc7ca40b8fb9b66123a6bd85a529e47b120"
KERNEL_RESERVATION = 40 * 1024 * 1024


def image_header(image):
    if len(image) < 64 or image[56:60] != b"ARM\x64":
        raise ValueError("Not an ARM64 Image")
    offset, size, flags = struct.unpack_from("<QQQ", image, 8)
    if flags & ~0xf or flags & 1 or ((flags >> 1) & 3) != 1:
        raise ValueError("Only the little-endian 4 KiB-page experiment is covered")
    if offset not in (0, 0x80000) or not len(image) <= size <= KERNEL_RESERVATION:
        raise ValueError("Image offset/runtime size outside the audited experiment")
    return offset, size


def round_up(size, alignment):
    return (size + alignment - 1) // alignment * alignment


def overlap(start, size, other, other_size):
    return size > 0 and other_size > 0 and start < other + other_size and other < start + size


def layout(image, ramdisk_size, page):
    if page != 2048 or ramdisk_size < 0:
        raise ValueError("Only the observed 2 KiB Android page layout is covered")
    offset, size = image_header(image)
    # Hypothesis for a future container, NOT a measured LK allocation success.
    kernel = 0x40000000 + offset
    dtb, ramdisk = 0x42f00000, 0x44000000
    copied = round_up(ramdisk_size, page)
    rounded = round_up(copied, 4096)
    if kernel + KERNEL_RESERVATION > 0x42880000:
        raise ValueError("LK's full kernel reservation exceeds observed low System RAM")
    if ramdisk + rounded > 0x50000000:
        raise ValueError("Ramdisk exceeds the conservative high RAM window")
    if overlap(kernel, KERNEL_RESERVATION, ramdisk, rounded) or overlap(
            kernel, KERNEL_RESERVATION, dtb, 0x100000):
        raise ValueError("Candidate LK reservations overlap")
    return {
        "image_text_offset": hex(offset), "image_runtime_size": hex(size),
        "candidate_kernel_address": hex(kernel),
        "candidate_kernel_reservation_end_exclusive": hex(kernel + KERNEL_RESERVATION),
        "dt_physical_address_from_tags": hex(dtb),
        "lk_kernel_virtual_mapping": "0x80080000 (not the physical entry address)",
        "candidate_ramdisk_address": hex(ramdisk), "ramdisk_copied_bytes": copied,
        "ramdisk_reserved_bytes": rounded,
        "stock_ramdisk_address_conflicts_with_kernel_reservation": overlap(
            kernel, KERNEL_RESERVATION, 0x41000000, rounded),
    }


def audit(stock, image, ramdisk):
    if len(stock) != 0x2000000 or hashlib.sha256(stock).hexdigest() != STOCK_SHA:
        raise ValueError("Refusing unknown stock boot dump")
    page, version = struct.unpack_from("<II", stock, 36)
    if stock[:8] != b"ANDROID!" or version != 2 or page != 2048:
        raise ValueError("Unexpected stock Android header")
    command_line = stock[64:576].split(b"\0", 1)[0]
    match = re.search(rb"(?:^|\s)(bootopt=\S+)", command_line)
    if not match or match[1] != b"bootopt=64S3,32N2,64N2":
        raise ValueError("Unexpected stock bootopt architecture selector")
    result = layout(image, len(ramdisk), page)
    result.update({
        "status": "LAYOUT HYPOTHESIS ONLY — NOT FLASHABLE",
        "stock_sha256": STOCK_SHA,
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "initramfs_sha256": hashlib.sha256(ramdisk).hexdigest(),
        "stock_kernel_address": hex(struct.unpack_from("<I", stock, 12)[0]),
        "stock_ramdisk_bytes": struct.unpack_from("<I", stock, 16)[0],
        "preserve_android_header_selector": match[1].decode("ascii"),
        "required_kernel_encoding": "gzip/deflate (not raw Image)",
        "gzip_component_bytes": len(gzip.compress(image, mtime=0)),
        "handoff": "SMC 0x82000115(kernel_physical, dt_physical, 0, 1)",
        "not_verified": ["mblock allocation success", "LK DT/reservation/command-line fixups",
                         "nonzero external ramdisk path", "secure-monitor entry state",
                         "authentication acceptance", "X28 UART/boot/recovery"],
    })
    return result


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: handoff_check.py ORIGINAL_BOOT_DUMP Image initramfs.cpio")
    try:
        print(json.dumps(audit(*(Path(p).read_bytes() for p in sys.argv[1:])), indent=2))
    except (OSError, ValueError) as error:
        sys.exit(str(error))
