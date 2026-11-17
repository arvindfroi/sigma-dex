"""The Lugia ritual's version switch (Arvind 2026-11-17: "the only thing missing is the whole Lugia/Gravriel cutscene fixed:
it uses leaves, and the camera was very weird"). Origin is HeartGold, so the legendary cutscene code in overlay 2
(pret src/field/legend_cutscene_camera.c) takes Ho-Oh's path in the Whirl Islands too. Its three reads of gGameVersion
become calls to hooks.s (44 bytes of Thumb code at 0x01FFFE00, the top of ITCM, which stays empty all through the
ritual): SoulSilver on map 244 (the Lugia cave), the real version everywhere else. gGameVersion itself is never
changed, so the caught Pokemon is "met in HeartGold" and Bell Tower keeps HeartGold's path.
Sites (all `ldr rX, =gGameVersion ; ldrb rY, [rX]`, 4 bytes, replaced by one `bl`):
  0x02252D5C LegendCutscene_BeginClearBellAnim  FieldSystem r5 -> r0   (camera presets, leaves/waves, the eye glimmer)
  0x0225388E LegendCutscene_BirdFinalApproach   FieldSystem r4 -> r1   (start height 160 vs 120, timing)
  0x02253FE2 LegendCutscene_BeginLugiaArrivesEffect  FieldSystem r5 -> r0 (asserted not-HeartGold before)
python build.py IN.nds OUT.nds [--section]
  default: patches overlay 2 in place in OUT (file positions unchanged, so the jump ROMs' FAT pokes still hold) and
  prints the pokes that write hooks.bin to ITCM after a savestate is loaded (a savestate skips the boot's autoload)
  --section: also adds hooks.bin as an ARM9 autoload section at 0x01FFFE00 with ndspy (for a ROM that boots; ndspy
  lays the ROM out again, so the jump ROMs' pokes no longer fit it)"""
import sys, os, struct, shutil, subprocess
H = os.path.dirname(os.path.abspath(__file__))
IN, OUT = sys.argv[1:3]; SECTION = '--section' in sys.argv
OV2_RAM = 0x02245F40
HOOK_AT = 0x01FFFE00
syms = {}
for line in subprocess.run(['arm-none-eabi-nm', os.path.join(H, 'hooks.elf')], capture_output=True, text=True, check=True).stdout.split('\n'):
    p = line.split()
    if len(p) == 3: syms[p[2]] = int(p[0], 16)
code = open(os.path.join(H, 'hooks.bin'), 'rb').read()
assert syms['lv_common'] == HOOK_AT
def thumb_bl(at, dest):
    off = (dest & ~1) - (at + 4); assert -0x400000 <= off < 0x400000, hex(off); off &= 0x7FFFFF
    return struct.pack('<HH', 0xF000 | (off >> 12), 0xF800 | ((off >> 1) & 0x7FF))
SITES = [(0x02252D5C, bytes.fromhex('104800 78'.replace(' ', '')), 'lv_hook_r5_r0'),
         (0x0225388E, bytes.fromhex('05480178'), 'lv_hook_r4_r1'),
         (0x02253FE2, bytes.fromhex('29480078'), 'lv_hook_r5_r0')]
def patch_ov2(d):
    d = bytearray(d)
    for at, old, hook in SITES:
        o = at - OV2_RAM; cur = bytes(d[o:o + 4])
        assert cur == old, 'unexpected bytes at 0x%08X: %s (want %s)' % (at, cur.hex(), old.hex())
        d[o:o + 4] = thumb_bl(at, syms[hook]); print('  0x%08X %s -> bl %s' % (at, old.hex(), hook))
    return bytes(d)
if not SECTION:
    shutil.copyfile(IN, OUT)
    with open(OUT, 'r+b') as f:
        hdr = f.read(0x60); fat_off, = struct.unpack_from('<I', hdr, 0x48); ovt_off, ovt_len = struct.unpack_from('<II', hdr, 0x50)
        f.seek(ovt_off); ovt = f.read(ovt_len)
        ent = [struct.unpack_from('<8I', ovt, i) for i in range(0, ovt_len, 32)]
        ov2 = [e for e in ent if e[0] == 2][0]; assert ov2[1] == OV2_RAM, hex(ov2[1])
        f.seek(fat_off + 8 * ov2[6]); s, e = struct.unpack('<II', f.read(8))
        f.seek(s); d = f.read(e - s); d2 = patch_ov2(d); f.seek(s); f.write(d2)
    print('pokes:', ','.join('poke:0x%08X=%d' % (HOOK_AT + i, b) for i, b in enumerate(code)))
else:
    import ndspy.rom, ndspy.code
    rom = ndspy.rom.NintendoDSRom.fromFile(IN)
    ovs = rom.loadArm9Overlays(); ov2 = ovs[2]; assert not ov2.compressed and ov2.ramAddress == OV2_RAM
    rom.files[ov2.fileID] = patch_ov2(rom.files[ov2.fileID])
    arm9 = rom.loadArm9()
    for s in arm9.sections[1:]:
        lo, hi = s.ramAddress, s.ramAddress + len(s.data) + s.bssSize
        assert hi <= HOOK_AT or lo >= HOOK_AT + 0x200, 'section 0x%08X overlaps' % lo
    arm9.sections.append(ndspy.code.MainCodeFile.Section(code, HOOK_AT, 0))
    rom.arm9 = arm9.save(compress=False); rom.saveToFile(OUT); print('section added at 0x%08X (%d bytes)' % (HOOK_AT, len(code)))
print('ok', OUT)
