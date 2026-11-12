# MT6890 serial-only kernel experiment (#546)

**Offline components, NOT FLASHABLE.** This is not an OpenWrt router image,
Android boot container, or proof that an X28 boots Linux 6.x. Nothing here
changes the router. Do not write these files to a slot.

**Handoff audit:** [LK load/decompression/entry findings](../../docs/research/lk-kernel-handoff.md)
show that the blanket DT exclusions can collide with LK's reservation checks.
The current DT remains a static draft, not a container-ready hardware candidate.

## Build and check

Requires the local `x28-v2-build:25.12.6` ARM64 Docker image and the completed
#545 generic kernel build in volume `x28-v2-openwrt-25.12.6`. That environment
pins OpenWrt `64900e756efa667774214f9c6b17c113222e01f7` (25.12.6), Linux
6.12.112 and GCC 14.3.0/musl. No feed update/install or full userspace build.
The existing generic kernel/config are preserved. Do not run concurrent builds
against this volume.

From this repository root, choose a **new** output directory:

```sh
docker run --rm --init --cap-drop ALL --security-opt no-new-privileges \
  --mount type=volume,src=x28-v2-openwrt-25.12.6,dst=/work \
  --mount "type=bind,src=$PWD,dst=/x28,readonly" \
  x28-v2-build:25.12.6 \
  bash /x28/tools/v2-kernel/build.sh /work/serial-NEW
```

The script copies the prepared, OpenWrt-patched kernel to its output directory,
changes only that copy, then builds `Image` at `-j4`. It enables the upstream
MediaTek UART driver and removes storage, network devices/IP/firewall, USB,
PCI, graphics, cpufreq, cpuidle and watchdog support. NET core stays enabled:
OpenWrt's patched `lib/kobject_uevent` references `sk_skb_reason_drop` even when
NET is disabled. There are no network device nodes in the experimental DT.

BusyBox 1.37.0 uses OpenWrt's pinned source checksum, compiled statically with
only a shell and serial diagnostics. The external initramfs is uncompressed
(`CONFIG_RD_GZIP` is off in the baseline). `/init` mounts only proc/sysfs;
there is no automatic disk mount, UBI attach, modem startup or reboot. Exiting
the shell starts another shell. Device nodes are explicitly listed in the
archive; no host `mknod` or device access is needed.

Output: `Image`, `mt6890-serial.dtb`, `initramfs.cpio`, kernel/BusyBox configs,
`baseline.config`, `provenance.txt`, `sha256sums`, and `NOT-FLASHABLE`.
`INCOMPLETE` remains on failure. Prepared kernel source and build products are
retained for diagnosis; this is not a byte-reproducibility claim.

For the emulator check, install QEMU only in a disposable container (no
hardware/device mounts, no Docker socket):

```sh
docker run --rm --user root --security-opt no-new-privileges \
  --mount type=volume,src=x28-v2-openwrt-25.12.6,dst=/work \
  --mount "type=bind,src=$PWD,dst=/x28,readonly" \
  x28-v2-build:25.12.6 bash -ec '
    apt-get update -qq
    apt-get install -y --no-install-recommends qemu-system-arm
    python3 /x28/tools/v2-kernel/smoke.py /work/serial-NEW
  '
```

`smoke.py` checks the ARM64 Image header/runtime size, the conservative DT RAM
ranges and allowed device nodes, then boots **QEMU virt's own DT, not the X28
DT**. It requires a PID1 marker plus an actual shell command that reads
`/proc/meminfo`, with a 120-second timeout and guaranteed QEMU cleanup.
The emulator has no disk or network devices; output is saved as `qemu.log`.
Passing this check proves only the kernel/initramfs combination works on virt.

Local static checks:

```sh
shellcheck tools/v2-kernel/build.sh tools/v2-kernel/init
python3 -m py_compile tools/v2-kernel/smoke.py
```

## Observed result (2026-11-11)

Built the isolated kernel and completed the static initramfs after correcting
BusyBox's config handling (duplicate appended options are ignored by its older
Kconfig; use the kernel's `scripts/config` instead). The initial attempts/logs
remain under `/work/logs/serial-546*`; the successful components are in
`/work/serial-546-final`, also copied to host `private/build/serial-546/`.

- Kernel: ~14 MiB, runtime `image_size=0xe50000`, `text_offset=0`, 4 KiB pages.
- Initramfs: 262 KiB; BusyBox is AArch64 and static (no ELF interpreter).
- QEMU 7.2.22 virt: Linux 6.12.112, PID1 marker, serial shell and a real
  `/proc/meminfo` read passed (`MemTotal: 242404 kB`). No kernel panic observed
  before the test terminated QEMU. This is not a soak test.
- Manifest hashes verified; the generic baseline kernel config is unchanged.
  Refusal to overwrite an existing output directory also passed.
- Shellcheck and Python compilation passed. A full clean repeat of the final
  script has not been checked; the completed kernel build was retained while
  retrying the BusyBox/initramfs phase.

SHA-256:

```text
f1f4676e15b3837ec8040c72d3d5d6b30910b11226da0f2db0c70e5a2fa657ff  Image
d2c524be26e1decf3da3b8649d7b44a0515fe6bfe3665de365987c105481d17c  mt6890-serial.dtb
27dcea226736f9948782c606d7475f0da1784a08b3a8f3ec3f36d70f0b7130c5  initramfs.cpio
```

## SDK guide and X28 cross-check

Reference SDK: `../zlt-x28/sdk-fg360/release_sdk/mtk/ext_kernel-4.19/`.
It is a sibling FG360 tree, **not the exact X28 vendor tree**. Only hardware
facts were used; no vendor driver or firmware blob was copied into this port.

| Resource | SDK guide | X28 evidence / draft choice |
|---|---|---|
| CPU/PSCI | `arch/arm64/boot/dts/mediatek/mt6890.dtsi` | Cortex-A55, SMC PSCI 0.2; CPU0 only, no idle states |
| GICv3 | same, lines 441–452 | Distributor `0x0c000000/0x40000`, redistributor `0x0c040000/0x200000`; maintenance PPI 9 |
| Timer | same, `timer` | Saved X28 tree: PPIs 13/14/11/10, 13 MHz; live clocksource `arch_sys_counter` |
| UART0 | same, lines 3294–3304 | `0x11002000/0x1000`, SPI 109, 26 MHz baud source |
| UART gate | `drivers/clk/mediatek/clk-mt6890.c`, `ifrao_clks` | IFRAO2 bit 22, parent `fuart_ck`; **not ported** |

Fresh read-only checks on the running X28 (2026-11-11):

```sh
ssh -o BatchMode=yes x28 'uname -r; cat /proc/iomem; cat /sys/devices/system/clocksource/clocksource0/current_clocksource; readlink /sys/class/tty/ttyS0/device; cat /proc/tty/driver/serial'
```

Observed kernel 4.19.205, `ttyS0` device `../../../11002000.serial`, MMIO
`0x11002000`, and the memory ranges below. GIC/SPI/timer/clock properties also
match [`docs/firmware/x28-device-tree.dts`](../../docs/firmware/x28-device-tree.dts).

The UART uses upstream `8250_mtk.c`'s legacy **unnamed** baud-clock path, which
does not request a bus clock. This is deliberate, not a fabricated fixed bus
clock. It assumes LK leaves the bus gate/pinmux operational; `clk_ignore_unused`
does not enable a disabled gate. Real baud, RX IRQs, gating and power behavior
are not verified. Upgrade to a measured MT6890 clock-provider implementation
before relying on console operation across resets/power transitions.

## Conservative RAM ledger

The saved/live vendor DT has overlapping 1 GiB and 488 MiB memory declarations,
plus dynamic firmware reservations. Do not copy them wholesale or reclaim the
modem's memory. The draft admits only these observed, unreserved RAM windows:

| Start–end (inclusive) | Size | Reason |
|---|---:|---|
| `0x40000000–0x4287ffff` | 40.5 MiB | Observed low System RAM, includes the stock kernel load window |
| `0x44000000–0x4fffffff` | 192 MiB | Subset of observed `0x43e40000–0x4fffffff`, no nested live reservations |

Everything else in the 1 GiB DRAM range is excluded, not declared free:
`0x42880000–0x43ffffff` and `0x50000000–0x7fffffff` also have explicit `no-map`
reservations. These cover known ATF/LK/log buffers and all upper modem/firmware
regions, including the unexplained effective MD start at `0x6de00000`.
This was a conservative draft experiment map, **not reconciliation of the full
map or a proven LK-compatible design**. The subsequent handoff audit found an
overlap assertion gate in LK; the blanket-exclusion design must be replaced
or proven compatible before packaging.

The exact `/memory`, `/reserved-memory` and `/chosen` paths are retained for
LK's lookups. The `/memory` spelling intentionally triggers dtc's unit-address
warning. LK can replace `/memory/reg` and inject reservations; the explicit
excluded regions must survive its fixups. Overlap handling with LK's added
reservations, final DT contents, DT/ramdisk load placement and any firmware DMA
into these windows still need review. No field measurement proves this draft
safe for hardware yet.

## Hardware blockers / next gate

1. **Load address:** the 6.12 Image has `text_offset=0`. The handoff audit
   confirmed LK obtains the physical destination from Android header `+0x0c`;
   `0x40000000` is an aligned hypothesis, not proven allocation/boot success.
   The LK virtual alias `0x80080000` is not that physical destination. Its
   64-bit path requires gzip and selects architecture using the header's
   `bootopt`. Do not patch the Image header or reuse stock addresses blindly.
2. **LK handoff:** inspect its fixups on the minimal DT, including lookups of
   omitted modem nodes. Prove that it can pass this tree without assertions,
   expansion into usable RAM, or incorrect initrd addresses. Current kernel
   bootargs come from DT, not a forced command line; LK may replace them.
3. **Container/authentication:** stock uses an Android v2 boot image with an
   Android DTB table. A raw Image/DTB/cpio set is not that container. LK's changed
   boot-image authentication acceptance remains unproven. No bypass or LK
   modification is included.
4. **Hardware safety:** prove UART capture, kernel-entry privilege/cache/timer
   state, clock inheritance, active DMA and watchdog behavior, bounded runtime,
   fresh slot/counter state, verified full backup and tested return procedure.
   A missing watchdog/thermal driver is not protection against watchdog reset
   or overheating; there is no unattended hardware boot approval.

Only after these gates should a separately reviewed boot-container candidate
and an owner-approved inactive-slot experiment be considered. Keep the current
working installation intact. See [the roadmap](../../docs/research/x28-mainline-roadmap.md),
[boot flow](../../docs/BOOT-FLOW.md#where-linux-gets-its-device-tree-offline-2026-11-01-215)
and [LK authentication](../../docs/research/lk-boot-auth-preview.md).
