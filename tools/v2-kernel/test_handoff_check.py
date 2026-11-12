#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic layout tests; no firmware dump, Docker or device needed."""
import struct
import unittest

from handoff_check import audit, image_header, layout, overlap


def image(offset=0, size=0xe50000, flags=0xa):
    data = bytearray(64)
    data[56:60] = b"ARM\x64"
    struct.pack_into("<QQQ", data, 8, offset, size, flags)
    return bytes(data)


class HandoffTests(unittest.TestCase):
    def test_modern_layout_and_ramdisk_reservation(self):
        result = layout(image(), 2049, 2048)
        self.assertEqual(result["candidate_kernel_address"], "0x40000000")
        self.assertEqual(result["candidate_kernel_reservation_end_exclusive"], "0x42800000")
        self.assertEqual(result["ramdisk_copied_bytes"], 4096)
        self.assertEqual(result["ramdisk_reserved_bytes"], 4096)
        self.assertTrue(result["stock_ramdisk_address_conflicts_with_kernel_reservation"])
        self.assertEqual(layout(image(), 1, 2048)["ramdisk_reserved_bytes"], 4096)

    def test_legacy_offset_and_empty_ramdisk(self):
        result = layout(image(offset=0x80000), 0, 2048)
        self.assertEqual(result["candidate_kernel_address"], "0x40080000")
        self.assertEqual(result["candidate_kernel_reservation_end_exclusive"], "0x42880000")
        self.assertFalse(result["stock_ramdisk_address_conflicts_with_kernel_reservation"])

    def test_external_initrd_conflicts_with_low_ram_hypothesis(self):
        result = layout(image(), 1, 2048)
        self.assertTrue(result["external_initrd_outside_low_40m_hypothesis"])
        self.assertEqual(result["low_40m_end_exclusive"], "0x42800000")
        self.assertFalse(layout(image(), 0, 2048)["external_initrd_outside_low_40m_hypothesis"])

    def test_invalid_image_headers(self):
        for bad in (b"", bytes(64), image(size=0), image(size=63),
                    image(size=0x2800001), image(offset=0x40000),
                    image(flags=0xb), image(flags=0xc), image(flags=0x1a)):
            with self.subTest(header=bad[:32]), self.assertRaises(ValueError):
                image_header(bad)

    def test_invalid_ramdisk_sizes_and_page(self):
        for size, page in ((-1, 2048), (1, 4096), (0xc000001, 2048)):
            with self.subTest(size=size, page=page), self.assertRaises(ValueError):
                layout(image(), size, page)

    def test_overlap_boundaries(self):
        self.assertFalse(overlap(0, 1, 1, 1))
        self.assertFalse(overlap(0, 1, 0, 0))
        self.assertTrue(overlap(0, 2, 1, 1))
        self.assertTrue(overlap(1, 1, 0, 2))

    def test_unknown_stock_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown stock"):
            audit(bytes(0x2000000), image(), b"")


if __name__ == "__main__":
    unittest.main()
