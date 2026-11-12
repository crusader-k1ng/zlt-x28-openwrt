# LK device-tree fixups and the low-memory hypothesis

2026-11-12. Offline follow-up to [the load/entry audit](lk-kernel-handoff.md)
under the existing #546 investigation. No router access, firmware changes,
boot container, flash, slot change or hardware boot.

## Result

The serial DT is still **NOT FLASHABLE**. Two additional constraints are now
established: LK requires more metadata paths than the draft provides, and an
external initramfs above a proposed `mem=40M` window can be re-added by Linux
itself. Do not remove blanket exclusions and assume `mem=40M` fixes the handoff.

## Evidence and reproducibility

Original LK SHA-256 remains
`0ad94f065ebcfeefd157640d179b1b52779829a85179d07d38dd818b79007156`.
The existing `LkKernelHandoff.java` reporter was run on the annotated project
with `-readOnly -noanalysis`. Both reports completed their original-file and
mapped-byte checks. No saved analysis database or firmware bytes were changed.
The connected REA Ghidra provider lacked `GHIDRA_INSTALL_DIR`; the already
installed Ghidra and saved project were used directly, without changing MCP
configuration or importing a duplicate raw image.

Private, ignored evidence:

- `private/research/546-lk-fixups/ghidra-fixups.log`: file offsets
  `0x196a2 0x19a5c 0x351c 0x3c92 0x1e0e0`.
- `private/research/546-lk-fixups/ghidra-callbacks.log`: all 15 statically
  registered final-DT callbacks listed below.
- Linux source inspected in `/work/serial-546-final/linux` in the existing
  Docker volume: OpenWrt-patched Linux 6.12.112 from the previous build.

As in the earlier audit, `VA = file offset + 0x83fffe00`. Decompiled runtime
values remain unknown; the mapped bytes do not supply runtime mblock state.
This is static inspection, not execution/emulation of LK or its secure monitor.

## Command-line composition

**Observed:** finalizer file `0x196a2` (`0x840194a2`) requires `/chosen`, reads
`bootargs`, then `bootargs_ext`, appends the previously accumulated LK argument
buffer, processes a linked list of replacements, and writes back `bootargs`.
The append helper at file `0x19a5c` adds arguments to that buffer with a leading
space and asserts on overflow. This is composition, not a guarantee that the
draft DT's arguments are the complete/final Linux command line. Replacement
list contents and all registration sites were not audited here.

**Kernel-source observation:** `drivers/of/fdt.c:1056–1072` uses the built-in
`CONFIG_CMDLINE` in preference to supplied arguments when `CONFIG_CMDLINE_FORCE`
is selected (the `CONFIG_CMDLINE_EXTEND` branch precedes it). A future isolated
experiment could force its diagnostic arguments in Linux, but still must retain
Android header `bootopt=64S3,32N2,64N2` for LK's independent architecture selector.
The current artifact does not enable this proposed forced-command-line design.

## Final-DT callback requirements

**Observed:** dispatcher file `0x1e0e0` walks 15 pointer/name pairs from
`0x8403a700` up to, but not including, `0x8403a778`. The registered names are
actual firmware strings. Code pointers have their Thumb bit cleared below.

| File offset | Registered callback | Direct node behavior |
|---|---|---|
| `0x3a90` | `set_fdt_atag_boot` | Requires `/chosen` |
| `0x3b28` | `set_fdt_firmware` | Skips absent `/firmware/android` |
| `0x3bfc` | `set_fdt_usb_serialno` | Requires `/chosen` |
| `0x3d36` | `set_fdt_atag_meta` | Requires `/chosen` in selected boot modes |
| `0x7232` | `mboot_params_dts_write` | Requires `/chosen`; exports log/console metadata |
| `0x7982` | `mrdump_key_fdt_init` | Conditional compatible-node lookup; absent node skips the branch |
| `0x7f3c` | `mrdump_params_fdt_init` | Conditional `/chosen` writes; other runtime-state assertions remain |
| `0x865e` | `set_fdt_atag_all_items` | Finds or creates `/atag_rawdata_item` |
| `0x9136` | `set_fdt_dramc` | Requires `/dramc` for a non-null DT |
| `0x94c8` | `set_fdt_emi_info` | Requires `/soc/emicen`, `/soc/emimpu`, `/soc/emiisu`, or their root-level equivalents |
| `0x1dc9e` | `platform_fdt_set_chipid` | Requires `/chosen` |
| `0x1dd3a` | `platform_atag_devinfo_data` | Requires `/chosen` |
| `0x1ddbe` | `platform_fdt_set_model` | Conditionally replaces an existing root `model` property |
| `0x205fa` | `ccci_update_md_arg_info_to_dt` | Skips absent `/mddriver` |
| `0x24954` | `rootfs_sig_hock` | Requires `/chosen` when authenticated metadata is available |

`fdtget` on the existing compiled draft confirmed `/chosen`, `/memory` and
`/reserved-memory` present, but `/dramc` and the three `/soc/emi*` paths absent.
`set_fdt_emi_info` tries `/soc/NAME`, then `/NAME`, and asserts if both lookups
fail. Adding metadata nodes would address these direct lookups only; it would
not establish successful callback execution or a safe final memory map.
Transitive helper side effects, runtime-state assumptions and pre-dispatch DT
callbacks are not fully covered by this table.

## Why an external initramfs defeats a simple low-RAM argument

**Kernel-source observation:** `arch/arm64/mm/init.c:245–277` first applies
`memblock_mem_limit_remove_map(memory_limit)`, then adds back the kernel's own
range. When an external initrd exists and passes the linear-addressability
check, it also executes `memblock_add(base, size)`, clears `nomap` and reserves
the initrd range. Therefore a nonempty initrd at our hypothetical `0x44000000`
is not excluded solely by `mem=40M`, even if contiguous RAM starts at
`0x40000000` and that limit otherwise ends at `0x42800000`.

The limit counts memory, not an unconditional physical-address fence. LK's final
memory map, additional banks, kernel location and initrd parameters all matter.
The layout checker now reports whether its external ramdisk is outside the
low-40-MiB hypothesis; an empty external ramdisk clears only that one warning,
not any hardware-approval gate. Seven synthetic layout tests pass.

## Next experiment

1. Prepare a separate, minimal LK metadata fragment for the required paths;
   keep it distinct from standard Linux hardware bindings. Do not invent MMIO
   resources or enable extra hardware drivers merely to satisfy path lookups.
2. Build an **embedded** diagnostic initramfs and a reviewed forced command
   line, then verify the exact resulting kernel configuration and memory use
   under QEMU. The existing external-initramfs artifact is unchanged.
3. Check final memory-map assumptions and early reservations before deciding
   whether the broad DT exclusions can be removed. Test bounded-memory behavior,
   not just whether a shell runs with QEMU's default 256 MiB.
4. Audit trusted-monitor handoff and remaining authentication/load-and-return
   requirements before constructing any X28 boot container.

No revised DT or kernel was built in this pass. **Offline investigation may
continue; the current components remain unapproved for X28 boot or flashing.**
