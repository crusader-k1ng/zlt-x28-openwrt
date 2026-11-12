// SPDX-License-Identifier: GPL-3.0-or-later
// Ghidra read-only-project report; changes analysis permissions, NEVER firmware bytes.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;

public class LkKernelHandoff extends GhidraScript {
    private static final long BASE = 0x83fffe00L;
    private static final String SHA = "0ad94f065ebcfeefd157640d179b1b52779829a85179d07d38dd818b79007156";
    // Original-file offsets, not VAs. Optional arguments select further callees.
    private static final long[] DEFAULTS = {0x3e3a, 0x4448, 0x34d6, 0x3590,
        0x36ac, 0x36f2, 0x3784, 0x37d8, 0x394a, 0x39ac, 0x441a, 0x5c4, 0x33c8};

    @Override public void run() throws Exception {
        byte[] original = Files.readAllBytes(Path.of(currentProgram.getExecutablePath()));
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
        if (original.length != 0x200000 || !hash.equals(SHA))
            throw new IllegalArgumentException("Refusing unknown LK input: " + hash);
        if (!currentProgram.getLanguageID().toString().equals("ARM:LE:32:v8") ||
            currentProgram.getMinAddress().getOffset() != BASE)
            throw new IllegalArgumentException("Require ARM:LE:32:v8 at raw base 0x83fffe00");
        verifyBytes(original);
        println("HANDOFF INPUT VERIFIED " + hash);
        // Raw full-partition backing overlaps runtime state with unrelated stored bytes.
        // Writable ANALYSIS metadata prevents false constant-folding of cached boot headers.
        for (var block : currentProgram.getMemory().getBlocks()) block.setWrite(true);
        long[] offsets = DEFAULTS;
        String[] args = getScriptArgs();
        if (args.length != 0) {
            offsets = new long[args.length];
            for (int i = 0; i < args.length; i++) offsets[i] = Long.decode(args[i]);
        }
        DecompInterface dc = new DecompInterface();
        try {
            if (!dc.openProgram(currentProgram)) throw new IllegalStateException(dc.getLastMessage());
            for (long offset : offsets) {
                if (offset < 0x200 || offset >= 0x2ef00 || (offset & 1) != 0)
                    throw new IllegalArgumentException("Not an aligned first-payload code offset");
                var address = toAddr(BASE + offset);
                disassemble(address);
                Function function = getFunctionAt(address);
                if (function == null) function = createFunction(address, null);
                if (function == null) throw new IllegalStateException("No function at " + address);
                dc.flushCache();
                DecompileResults result = dc.decompileFunction(function, 90, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                println("HANDOFF FUNCTION file=0x" + Long.toHexString(offset) + " VA=" + address);
                println(result.getDecompiledFunction().getC());
                var instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction instruction = instructions.next();
                    println("ASM file=0x" + Long.toHexString(instruction.getAddress().getOffset() - BASE) + " " + instruction);
                }
            }
        } finally {
            dc.dispose();
        }
        verifyBytes(original);
        println("HANDOFF COMPLETE; original and mapped bytes unchanged; no firmware export");
    }

    private void verifyBytes(byte[] original) throws Exception {
        byte[] mapped = new byte[original.length];
        if (currentProgram.getMemory().getBytes(toAddr(BASE), mapped) != mapped.length ||
            !Arrays.equals(original, mapped))
            throw new IllegalStateException("Analysis memory differs from original file");
    }
}
