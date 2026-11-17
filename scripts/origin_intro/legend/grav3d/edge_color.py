"""Gravriel's outline in the ghost green (Arvind 2026-11-16: "the blue outline the same green as his see-through form").
The outline is the DS edge marking: 8 colours by polygon-ID group (id >> 3), set by the film overlay (Origin's ov097 =
pret ov106) from a table at ov097+0x1578: [0x0000, 0x7A89 (blue), 0x1084 x6]. Group 1 (ids 8-15) is used only by
Lugia's materials in Lugia's film (the Ho-Oh film and the third film use group 0), so entry 1 changes only him.
python edge_color.py ROM_IN ROM_OUT R,G,B   (8-bit, converted to RGB555)"""
import sys, struct
src, dst, rgb = sys.argv[1], sys.argv[2], [int(v) for v in sys.argv[3].split(',')]
b = bytearray(open(src, 'rb').read())
ovt_off, ovt_size = struct.unpack_from('<II', b, 0x50); fat_off = struct.unpack_from('<I', b, 0x48)[0]
for k in range(ovt_size // 32):
    oid, ram, size, bss, s0, s1, fid, flags = struct.unpack_from('<8I', b, ovt_off + 32 * k)
    if oid == 97: break
assert oid == 97 and not (flags >> 24) & 1, 'overlay 97 missing or compressed'
start, end = struct.unpack_from('<II', b, fat_off + 8 * fid)
tab = struct.unpack_from('<8H', b, start + 0x1578)
assert tab[0] == 0 and tab[2] == 0x1084, ('edge table not where expected', [hex(x) for x in tab])
c = (rgb[0] >> 3) | (rgb[1] >> 3) << 5 | (rgb[2] >> 3) << 10
struct.pack_into('<H', b, start + 0x157A, c)
open(dst, 'wb').write(b); print('ov097 edge colour 1: %#x -> %#x' % (tab[1], c))
