#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Boot components on QEMU virt, NOT the X28 DTB or board; never attach storage/network."""
import os
from pathlib import Path
import selectors
import struct
import subprocess
import sys
import time


def smoke(directory):
    directory = Path(directory).resolve()
    with (directory / "Image").open("rb") as image:
        header = image.read(64)
    if len(header) != 64 or header[56:60] != b"ARM\x64":
        raise RuntimeError("Not an ARM64 Image")
    text_offset, image_size = struct.unpack_from("<QQ", header, 8)
    if text_offset not in (0, 0x80000) or not 0 < image_size <= 0x02800000:
        raise RuntimeError("Image cannot fit the documented 40 MiB low-RAM load window")
    print(f"Image text_offset={text_offset:#x}, runtime size={image_size:#x}; "
          "LK load-address compatibility still needs review")
    # The draft must not expose modem RAM or instantiate storage/radio hardware.
    expected = {
        ("/memory", "reg"): "0 40000000 0 2880000 0 44000000 0 c000000",
        ("/reserved-memory/excluded-low@42880000", "reg"): "0 42880000 0 1780000",
        ("/reserved-memory/excluded-upper@50000000", "reg"): "0 50000000 0 30000000",
        ("/serial@11002000", "reg"): "0 11002000 0 1000",
        ("/serial@11002000", "interrupts"): "0 6d 4",
    }
    for (node, prop), value in expected.items():
        actual = subprocess.check_output(
            ["fdtget", "-t", "x", str(directory / "mt6890-serial.dtb"), node, prop], text=True)
        if actual.strip() != value:
            raise RuntimeError(f"Unexpected DT property: {node} {prop}: {actual.strip()}")
    for node in ("excluded-low@42880000", "excluded-upper@50000000"):
        subprocess.run(["fdtget", str(directory / "mt6890-serial.dtb"),
                        f"/reserved-memory/{node}", "no-map"], check=True,
                       stdout=subprocess.DEVNULL)
    nodes = subprocess.check_output(
        ["fdtget", "-l", str(directory / "mt6890-serial.dtb"), "/"], text=True).splitlines()
    if set(nodes) != {"aliases", "chosen", "memory", "reserved-memory", "cpus", "psci",
                     "interrupt-controller@c000000", "timer", "clock-26m", "serial@11002000"}:
        raise RuntimeError("Unexpected root device nodes in serial-only DT")
    command = [
        "qemu-system-aarch64", "-machine", "virt,gic-version=3", "-cpu", "cortex-a53",
        "-smp", "1", "-m", "256M", "-nographic", "-monitor", "none", "-nic", "none",
        "-no-reboot", "-kernel", str(directory / "Image"),
        "-initrd", str(directory / "initramfs.cpio"),
        "-append", "console=ttyAMA0 rdinit=/init panic=0",
    ]
    with (directory / "qemu.log").open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                output = b""
                sent = False
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    for key, _ in selector.select(timeout=1):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            raise RuntimeError("QEMU exited before serial diagnostics passed; see qemu.log")
                        log.write(chunk)
                        log.flush()
                        output = (output + chunk)[-262144:]
                        if not sent and b"X28_SERIAL_INITRAMFS_READY" in output:
                            # Split marker so echoed command input cannot falsely pass the test.
                            process.stdin.write(b"uname -r; cat /proc/meminfo; printf 'X28_DIAGNOSTICS_%s\\n' OK\n")
                            process.stdin.flush()
                            sent = True
                        if sent and b"X28_DIAGNOSTICS_OK" in output and b"MemTotal:" in output:
                            if b"6.12.112" not in output:
                                raise RuntimeError("Unexpected kernel version")
                            print("PASS: Linux 6.12.112 reached PID1, serial shell and /proc diagnostics on QEMU virt")
                            return
                raise RuntimeError("Serial diagnostics timed out after 120 seconds; see qemu.log")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: smoke.py ARTIFACT_DIRECTORY")
    smoke(sys.argv[1])
