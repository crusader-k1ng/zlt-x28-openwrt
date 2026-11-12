# LK to Linux 6.12: load/decompression/entry audit (#546)

2026-11-11. **Offline static analysis only. No firmware patch/export, boot
container, router access, slot change, flash or reboot in this investigation.**
The preceding kernel/initramfs booted QEMU virt, not an X28.

## Result

The physical kernel destination is **read from Android header offset `0x0c`**,
not hard-coded to `0x40080000`. For our modern Image (`text_offset=0`),
`0x40000000` is a plausible aligned destination to investigate. This closes the
question of whether LK merely hard-codes the old physical address; it does
**not** prove the allocator/monitor will accept the new address on hardware.

Three more constraints were established:

1. LK's 64-bit path calls a **gzip/deflate decompressor**, not a raw Image copy.
2. The Android header's **`bootopt=64S3,32N2,64N2`** selects the kernel execution
   path. Do not replace the header command line with only our Linux arguments.
3. The preliminary serial DT's **blanket exclusions are not suitable for the
   stock handoff**: LK validates input reserved-memory `reg` ranges against its
   own reservation table and asserts on overlaps. `no-map` does not bypass it.
   Broad exclusions covering ATF/modem reservations must not be packaged as-is.

No boot image was generated. The next work is to design a memory/command-line
strategy compatible with LK's fixups, before choosing an external versus
embedded initramfs and constructing a container.

## Inputs and evidence

| Input | Bytes | SHA-256 |
|---|---:|---|
| Original LK A (B matches the original investigation) | 2,097,152 | `0ad94f065ebcfeefd157640d179b1b52779829a85179d07d38dd818b79007156` |
| Original boot B | 33,554,432 | `c8cc8244078cb6539c72842540250bc7ca40b8fb9b66123a6bd85a529e47b120` |
| Experimental Linux 6.12.112 Image | ~14 MiB | `f1f4676e15b3837ec8040c72d3d5d6b30910b11226da0f2db0c70e5a2fa657ff` |

Original inputs are in the sibling `../zlt-x28/private/` worktree, not Git.
Experimental components are in `private/build/serial-546/`.
Private evidence is in `private/research/546-lk-handoff/`:

- Complete REA 6.7.0/Ghidra 12.1.4 Evidence JSON, including assembly and limits.
  No MCP registration/configuration was changed; CLI used the installed engine.
- `ghidra-handoff.log` and `ghidra-handoff-helpers.log`: independent reports from
  the existing `ARM:LE:32:v8` database opened **read-only**, no auto-analysis/save.
- `layout-audit.json`: read-only layout calculation, explicitly NOT FLASHABLE.

Key REA Evidence IDs:

| Function | Evidence ID |
|---|---|
| Prepare | `ev_1b3a29af5d989e41cdaf2b4ad535b05088544dba05081b49dfffbb86a68c02db` |
| Caller | `ev_ad61d7c0420271bac2bc45a21a3aa241e0227dd5271eddff19d1feec0ca06579` |
| Decompress | `ev_1dc7df671c3785d1021a8adce03147582292f5d9301e2fdc0a1c026ae26d1d15` |
| Entry wrapper | `ev_167746213c05f9f805d4eecde5da2bfc729fe8017533b1cea71dd714c34d219b` |

**Important analysis correction:** REA's generic raw ARM import uses
`ARM:LE:32:v7` and read-only raw backing. Runtime globals overlap unrelated
stored bytes in a full partition import, so its decompiler incorrectly folds
some getters to nonsense constants (e.g. `0x42816a71`). Those return values are
**not firmware state**. The getter's decoded `ldr [header,#0xc]` and header
parser's writes are the evidence. `LkKernelHandoff.java` marks only the ephemeral
analysis blocks writable before decompilation to prevent this folding; it
verifies the entire mapped image against original bytes before and after.
The saved database and firmware files are not altered.

## Stock container and modern Image

Read from the hash-pinned original Android boot header:

| Field | Value |
|---|---|
| Header version / size | 2 / `0x67c` |
| Page size | `0x800` (2048) |
| Kernel bytes / address | `0x8997d1` / `0x40080000` |
| Kernel encoding | gzip (`1f 8b 08`), 31,121,416 decompressed bytes |
| Stock Image `text_offset` / runtime `image_size` | `0x80000` / `0x2083000` |
| Ramdisk bytes / address | **0** / `0x41000000` |
| Second bytes / address | 0 / `0x40f00000` |
| Tags address | `0x42f00000` |
| DTB bytes / header DTB address | `0x19284` / `0x41f00000` |
| Header architecture selector | `bootopt=64S3,32N2,64N2` |

Modern Image header: `text_offset=0`, runtime `image_size=0xe50000`, flags
`0xa` (little-endian, 4 KiB pages, physical-placement bit set).
The ARM64 protocol still requires `load = 2 MiB aligned base + text_offset`.
Therefore stock's load at `0x40080000` is not the address to blindly reuse.

## Observed call chain

All file offsets refer to the original complete LK partition.
**VA = file offset + `0x83fffe00`**. Names below are analyst descriptions, not
recovered source names or rebuilt vendor code.

| File offset / VA | Observed role |
|---|---|
| `0xee12` / `0x8400ec12` | Boot/recovery loader, existing policy/authentication gates |
| `0x33c8` / `0x840031c8` | Checks `ANDROID!`, copies `0x67c` bytes to cached header `0x840490a8` |
| `0x38be` / `0x840036be` | Searches the first 512 header command-line bytes for `bootopt=`, finds two commas, compares the following two bytes with `64` |
| `0x3868` / `0x84003668` | Publishes the loaded image buffer pointer |
| `0x4448` / `0x84004248` | Gets component destinations/sizes; prepares optional ramdisk, calls kernel preparation |
| `0x34d6` / `0x840032d6` | Returns cached header `+0x0c`: **physical kernel destination** |
| `0x37d8` / `0x840035d8` | Returns cached header `+0x20`: **tags/DT physical destination**, not the v2 `dtb_addr` field |
| `0x394a` / `0x8400374a` | Returns architecture-state byte XOR 1, populated by the `bootopt` parser |
| `0x3e3a` / `0x84003c3a` | Prepares DT/kernel, decompresses, runs fixups, cleans up and requests monitor handoff |
| `0x39ac` / `0x840037ac` | Gzip header parsing followed by raw-deflate inflate (`-15` window bits); returns failure unless stream ends successfully |
| `0x441a` / `0x8400421a` | Calls SMC `0x82000115`, then spins if the call returns |
| `0x5c4` / `0x840003c4` | ARM-state register wrapper issuing `smc #0` |

### Physical address versus LK virtual alias

For a nonzero header kernel address, preparation requests a **40 MiB** mblock
reservation at that physical destination, aligned at 512 KiB. It asserts the
allocator returned exactly that address. Its internal 64-bit-kernel **virtual**
mapping is `0x80080000`; that is not the Linux physical entry address.
The decompressor writes through that virtual mapping. The final handoff uses
the original requested **physical** destination.

The allocator at file `0x1b6de` / VA `0x8401b4de` takes a fixed-address request;
zero selects a different allocation path. Its runtime free/reserved tables
were not emulated. We cannot claim a proposed allocation succeeds just because
its arithmetic and observed RAM bounds fit.

### Monitor boundary

The inspected 64-bit path passes, in analyst notation:

```text
SMC service 0x82000115(kernel_physical, dt_physical, 0, 1)
```

The wrapper loads the fifth service argument from the ARM stack into `r4`.
This is not a direct AArch64 `br` from LK. Final exception level, `x0`–`x3`,
cache/MMU state, entry validation/rewrites and the monitor's accepted address
range remain **UNKNOWN** until the matching trusted-firmware path is audited
or measured in a separately authorized boot. Do not infer them from this call.

## Ramdisk and DT implications

The stock ramdisk is empty. The caller nevertheless requires nonzero ramdisk
address and source-buffer pointer. For a nonempty ramdisk it rounds the header
size to the Android page size, reserves a further 4 KiB-rounded physical
range, maps a requested LK virtual address and copies the page-rounded bytes.
It later places the **page-rounded** end in `linux,initrd-end`.
This nonempty path is not established by the stock boot evidence.

Reusing stock ramdisk address `0x41000000` would overlap LK's entire 40 MiB
kernel reservation, even if it happens to miss the modern kernel's actual
runtime footprint. A future external ramdisk needs a separate range. An
embedded initramfs is another candidate, but would require a new kernel build
and its own command-line/memory validation.

The DT buffer is requested via **tags_addr** at `0x42f00000`, reserved as 1 MiB,
and prepared at virtual `0x82f00000`. The v2 table supplies the source tree.
The third argument `0x80000` is **destination capacity**, not a fixed source
copy length. Function file `0x1056c` / VA `0x8401036c` matches libfdt's
`fdt_open_into`; its move helper at file `0xf9f2` / VA `0x8400f7f2` copies the
validated source FDT `totalsize`, then the outer function expands the destination
header's `totalsize` to 512 KiB. The SDK's `scripts/dtc/libfdt/fdt_rw.c:429` and
`fdt.c:245` corroborate this algorithm. The older BOOT-FLOW copy-size inference
was corrected: a ~1.8 KiB source DT does not require a 512 KiB source read, but
the destination must have room for LK's additions. See
[BOOT-FLOW](../BOOT-FLOW.md#where-linux-gets-its-device-tree-offline-2026-11-01-215).

**Reserved-memory rejection gate:** file `0x1c8e4` / VA `0x8401c6e4` requires
`/reserved-memory`, iterates existing children with `reg`, and asserts when a
range overlaps its recorded reservations. It also requires `/memory` and
writes `mblock_info` and other handoff properties. This is not a transparent
pass-through of arbitrary exclusions. The preliminary DT's low exclusion
covers ATF/log areas and its upper exclusion covers modem/tinysys regions that
stock LK reserves. That design must be replaced or proven compatible, not
merely padded into an Android container. This is a static rejection risk, not
an observed attempt to boot the draft.

One possible next slice is an **embedded initramfs and a kernel-enforced low
RAM limit** covering only the first 40 MiB, with no blanket reserved-memory
ranges. First establish that the minimal kernel/shell fits that limit, that
LK preserves required nodes, and that the kernel actually enforces the limit
after all fixups. Do not simply remove reservations and expose 1 GiB to Linux.

## Read-only layout hypothesis and checks

`tools/v2-kernel/handoff_check.py` checks the known stock hash and ARM64 header,
then calculates reservations without generating/writing any firmware:

```sh
python3 tools/v2-kernel/test_handoff_check.py
python3 tools/v2-kernel/handoff_check.py \
  ../zlt-x28/private/firmware/20261021/boot_b.bin \
  private/build/serial-546/Image private/build/serial-546/initramfs.cpio
```

Observed calculation, **not an approved layout**:

- Kernel physical candidate: `0x40000000`; full reservation ends `0x42800000`.
- DT physical buffer: `0x42f00000` (tags address), outside that reservation.
- External ramdisk candidate: `0x44000000`; copy 268,288 bytes, reserve 270,336.
- Standard gzip encoding of the current Image is ~5.0 MiB on this host.
- No blanket-DT compatibility, mblock success, monitor behavior or authentication
  result is inferred from these values.

Six synthetic tests passed: modern/legacy offsets, empty/nonempty ramdisk,
2 KiB copy versus 4 KiB reservation rounding, overlap boundaries, malformed
Image flags/sizes/offsets, out-of-window sizes and unknown stock refusal.
The Ghidra reporter completed all 13 default functions, six extra handoff
helpers and two libfdt helpers,
checking all original bytes unchanged. A synthetic non-firmware input was
refused before the completion marker. No full boot-chain emulation was done.

Reproduce the Ghidra report with the existing annotated project (use an
absolute, canonical project path; Ghidra rejects `..` path elements):

```sh
JAVA_HOME=$(/usr/libexec/java_home) \
  /Users/ali/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless \
  /absolute/path/to/zlt-x28/private/research/207-lk-ghidra/project \
  X28_LK_Readable -process mtd25-lk_a.bin -readOnly -noanalysis \
  -scriptPath "$PWD/tools/firmware" -postScript LkKernelHandoff.java
```

Require `HANDOFF INPUT VERIFIED` and `HANDOFF COMPLETE`, not just exit code 0.
Additional original-file function offsets may follow the script name;
this investigation used `0x3868 0x38be 0x1b6de 0x15b96 0x1c8e4 0x3c92`,
then `0x1056c` and `0xf9f2` for the libfdt copy-size correction.

## Remaining gates

- Compatible minimal DT, memory enforcement and the callback's omitted-node
  assumptions; header/Linux command-line merging is not fully traced yet.
- Nonempty ramdisk support or a reviewed embedded-initramfs alternative.
- Monitor entry state and whether it honors the proposed physical address.
- Boot authentication remains separate: no LK patch/bypass or signing-policy
  change was made. See [the authentication map](lk-authentication-ghidra.md).
- UART gate/pinmux, DMA quiescence, watchdog/thermal behavior, fresh slot/counter
  state, verified backup and exact guarded return procedure before hardware.

**Verdict: GO for further offline design; NO-GO for packaging the current DT as
an X28 boot candidate or attempting any hardware boot/write.**
