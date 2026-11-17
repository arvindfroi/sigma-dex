"""Make the legend bird (Ho-Oh's slot: Sabertann) land HEIGHT world units above its map object, so it hovers above the
Kimono girls instead of standing behind them. Patches Task_BirdFinalApproach's CORRECT_POS state in overlay 2 (pret
src/field/legend_cutscene_camera.c): yEnd = pos.y + HEIGHT; the 120-unit descent is kept. Origin is HeartGold only, so the
dead SoulSilver branch there makes room. The overlay is stored uncompressed; it is found in the ROM by its bytes.
python hover_patch.py OV002.bin ROM_IN ROM_OUT HEIGHT"""
import sys, struct
OV, SRC, DST, H = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
assert 0 <= H <= 255
ov = open(OV, 'rb').read(); rom = bytearray(open(SRC, 'rb').read())
A = 0xdae4                                            # ldr r0,[sp,#0x24] ; str r0,[r4,#4] ; ... version branch ... str r0,[r4]
OLD = [0x9809, 0x6060, 0x1c20, 0x30e0, 0x8800, 0x2807, 0xd102, 0x201e, 0x0380, 0xe001, 0x200a, 0x0400, 0x6020]
NEW = [0x9809,           # ldr  r0, [sp, #0x24]   pos.y
       0x2100 | H,       # movs r1, #H
       0x0309,           # lsls r1, r1, #12       H in fx32
       0x1840,           # adds r0, r0, r1
       0x9009,           # str  r0, [sp, #0x24]   pos.y += H (the descent starts from there too)
       0x6060,           # str  r0, [r4, #4]      yEnd
       0x201e, 0x0380,   # movs r0, #0x1e ; lsls r0, r0, #14   yDelta = 120 (HeartGold)
       0x46c0, 0x46c0, 0x46c0, 0x46c0,   # nop
       0x6020]           # str  r0, [r4]
o = rom.find(ov[A - 0x40:A + 0x40]); assert o >= 0 and rom.find(ov[A - 0x40:A + 0x40], o + 1) < 0, 'overlay bytes not found once'
o += 0x40
cur = list(struct.unpack_from('<13H', rom, o))
assert cur == OLD, [hex(x) for x in cur]
struct.pack_into('<13H', rom, o, *NEW); open(DST, 'wb').write(rom); print('patched at', hex(o), 'height', H)
