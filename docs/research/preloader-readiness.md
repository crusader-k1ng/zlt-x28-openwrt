# X28 preloader: provenance and requirements for future work

Investigation: **2026-11-12**. Offline inspection of saved X28 captures, the local
Fibocom FG360 SDK, ELF/debug metadata and existing boot/recovery evidence.
No router connection, firmware execution, patching, image generation, security
configuration change or flash operation. This is an inventory, not a complete
preloader control-flow or Boot ROM authentication audit.

## Decision

**Preserve the working preloader for the Linux 6.12 port.** We have a useful
MediaTek-family binary reference and debug symbols, but not the matching
preloader source/build recipe or proven recovery from a broken preloader.
A clean Linux device tree does not require replacing this stage.

## 1. What the provenance establishes

**Artifact observation:** the original X28 payload contains source-path strings
under `mtk5g-t750/T750/mtk/package/boot/preloader/platform/mt6890/`, including
`dramc_top.c`, `emi.c`, `memory.c`, `platform.c`, `main.c`, `sec.c`,
`sec_auth.c` and `tz_init.c`. A separate path identifies MediaTek's
`secure_lib/src/core/sboot_state.c`. The same artifact records project filename
`preloader_evb6890v1_64_cpe_nand.bin` and `MTK_BLOADER_INFO_v49`.

**SDK observation:** the FG360 sibling preloader shares that project filename
and MT6890 source-directory structure, with different build paths and bytes.
This supports **MediaTek T750/MT6890 BSP lineage**. It does not identify the
individual authors, prove Tozed wrote the preloader, or establish which changes
came from MediaTek, Quectel, Tozed or another integrator. Absence of a particular
vendor name in a bounded string search is not evidence of no vendor changes.

**Important source limitation:** the SDK recipe at
`openwrt/package/mtk/boot/preloader/Makefile` has empty compile steps. It copies
`.bin`/`.elf`, optional `loader_ext.img`/`efuse.img`, `pi_img.img`, and download
agent/configuration files from `mtk/prebuilt/boot/preloader/$(SUBTARGET)`.
The referenced `mtk/package/boot/preloader` source directory is absent from
this local SDK. This package is not evidence of a source-rebuild capability.

A bounded public search also did not establish an exact X28 preloader source
release. The [existing X28 OpenWrt work](https://github.com/gaglians/zlt-x28-openwrt2305)
explicitly separates its original code from vendor SDK components. Recovery
projects or firmware mirrors do not establish matching source or compatibility.

## 2. Artifact identities and reference value

Original captures live under the sibling worktree's
`private/recovery/20261020-capture-prepared-20261021/images/`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `mtd00-preloader.bin` | 4,194,304 | `0f59889f3a11410fce4cea6fabab22b94a0d113e02c1d6fbbbe7f23c1205d950` |
| `mtd01-preloader_backup.bin` | 2,097,152 | `cf1c2226273bd56d6e19c9973ad46a3da70788ed7a65fb9c5d38c16285232eba` |
| Saved `pl_gfh.bin` slice | 256,364 | `45af881f2094435c3fdcae37562b714e1a0f481132f1c2460986980515969a43` |
| FG360 NAND preloader binary | 238,476 | `f0425a0893759ea1296c3c48354d88230dca7786b57c95ed0689ff7a502b194e` |
| FG360 NAND preloader ELF | 2,401,220 | `7505e623a9892755a744e93e44d265f30d9202191ad0e8dae65c9bf0c00543fe` |

The saved GFH slice occurs **byte-for-byte at `0x40000` in both original
partitions**. The raw dumps differ in size and bytes outside that slice; they
must not be treated as interchangeable flash containers, nor as proof of two
different payload builds. ECC/OOB, NAND bad-block handling and Boot ROM copy
selection are not resolved by this comparison.

The saved Ghidra project imports this exact slice at `0x200ea0` using
`ARM:LE:32:v8`; its identity was checked, but no new decompilation was performed
in this pass. Previously decoded PRO-unit slot-selection addresses must not
be reused blindly on this first-unit payload.

**SDK ELF observation:** ELF32, little-endian ARM EABI5, unstripped, with DWARF,
entry `0x201004`. Global symbols include `platform_pre_init`, `platform_init`,
`emi_init`, `emi_init2`, `mt_set_emi`, `bldr_load_part_lk`, `bldr_load_tee_part`,
`bldr_load_loader_ext_dram`, `bldr_jump` and `bldr_jump64`. These are sibling
reference symbols, not established names/addresses in the X28 binary.

The DWARF producer records Android GNU C **4.9.x 20150123**, ARMv7-A/Thumb,
soft-float, freestanding code. The local `arm-linux-androideabi-gcc` launcher is
a Python wrapper; its selected compiler executable is **x86-64 Linux**. Merely
having this SDK on our ARM64 Docker host does not make its original build
usable. We did not execute the vendor compiler or test emulation.

## 3. Responsibilities that must remain compatible

| Responsibility | Evidence | What a replacement must establish |
|---|---|---|
| Early platform/DRAM setup | X28 paths; sibling `emi_init` and platform symbols | Exact DRAM part/configuration, training/timing, PMIC, clocks, boot voltage/reset assumptions |
| NAND and partition loading | Sibling NAND symbols; existing successful recovery captures | Geometry, ECC/OOB/randomizer, bad blocks, boot-copy format and partition addressing |
| A/B selection and boot attempts | Existing [slot audit](slot-b-reuse.md), partly PRO-specific | Same-unit control-flow verification, `misc` record copies/defaults and reset/failure behavior |
| Loading later stages | UART logs show extension, LK, TEE/tinysys checks; sibling loader symbols | Compatible extension/PI images, trusted firmware, image metadata and load/reserved ranges |
| Security/authentication | X28 security paths and observed certificate-check logging | Actual Boot ROM policy, eFuse/security configuration, permitted signing/owner-key path, failure behavior |
| USB download/recovery | Proven preloader-based DA sessions | Recovery that still works when the preloader itself is invalid; this is not currently proven |

The mere existence of `efuse.img` or security-off log lines authorizes no write
and proves no replacement acceptance. Do not flash SDK images or alter fuses.
The existing USB recovery path is largely **preloader-mediated**. The
[recovery notes](../RECOVERY.md#brom-mode-and-the-mtkclient-version-research-2026-10-22)
explicitly leave direct Boot ROM entry with a damaged preloader unresolved.

## 4. What to obtain before considering a rebuild/replacement

1. **Matching source delivery:** MT6890 platform and board project, linker maps,
   DRAM/EMI tables and generator inputs, PMIC/clock/storage drivers, extension
   sources, required libraries, build scripts and licence/redistribution terms.
   Request the exact X28/module firmware branch, not just an MT6890 sibling SDK.
2. **Board facts:** DRAM and NAND part identities, schematics or verified pin/
   power configuration, UART voltage/pinout, and per-board revision differences.
   A shared SoC/project filename is not a substitute.
3. **Reproducible original build:** compiler/binutils/Python versions, host
   architecture/runtime dependencies and exact configuration. First compare
   sections/symbols, headers, DRAM tables and manifests offline; do not assume
   byte differences are harmless or identical hashes sufficient for every unit.
4. **Security/container contract:** independently trace Boot ROM-to-preloader
   acceptance and preloader-to-extension/LK/TEE verification. Determine whether
   supported replacement signing is possible. Do not assume either that vendor
   private keys are required or that authentication is disabled.
5. **Independent recovery proof:** backup all critical partitions and device
   identity/calibration; establish a usable entry path independent of the
   candidate preloader and a board-specific restore procedure. A stock backup
   plus a currently functioning preloader USB window is insufficient proof.
6. **Separate, reviewed experiment:** recoverable spare hardware, serial capture,
   explicit stop/rollback conditions, and only then a narrowly scoped test plan.
   Do not combine a new preloader, LK and kernel in one first experiment.

For the current kernel port we instead need the **handoff contract**: usable RAM
and reservations, UART state, trusted-monitor/PSCI behavior, LK loading and DT
fixups. Keep preloader/DRAM firmware unchanged while resolving those questions.

## 5. Reproduction and remaining unknowns

Private evidence produced here:
`private/research/preloader-20261112/inventory.json`,
`sdk-symbols-full.txt`, `sdk-elf-symbols.txt` and `sdk-elf-core.txt`.
The inventory records SHA-256, sizes, exact matching-slice locations and selected
source-path strings. Standard read-only `readelf -h`, `readelf -Ws` and
`readelf --debug-dump=info` on the sibling ELF reproduce its format, symbol and
compiler observations. No private binaries/debug files were added to Git.

Still unknown: exact integrator attribution; matching X28 source/deltas;
board-specific DRAM settings equivalence; ROM trust policy and effective fuses;
complete authentication/failure paths; boot-copy failover; direct recovery with
a bad preloader; and whether any rebuilt replacement would execute correctly.
**A buildable or safe replacement has not been demonstrated.**
