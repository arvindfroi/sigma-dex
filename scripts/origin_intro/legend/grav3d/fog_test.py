"""LOOK TEST ONLY for green fog in the Lugia room (Arvind 2026-11-16: "I want to try it; if it's meh we drop it").
The mist weathers 9/10 run one task in overlay 1 (ov01 ~0x021ED4B0) that calls the fog setup with two pool literals:
ov001+0x7E30 = fog offset 0x7555 (where the fog starts in depth; far, so it is barely visible from the overhead camera)
and ov001+0x7E34 = fog colour 0x7FFF (white). Both are SHARED with weather 9 (Sprout Tower 2F, Goldenrod Dept. Store
3F), so this patch is for a look test; the real change needs weather 10 to get its own values.
python fog_test.py ROM_IN ROM_OUT OFFSET COLOR555      e.g. 0x7300 0x3A88"""
import sys, struct
src, dst, off_v, col_v = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4], 0)
b = bytearray(open(src, 'rb').read())
ovt_off, ovt_size = struct.unpack_from('<II', b, 0x50)                  # arm9 overlay table
fat_off = struct.unpack_from('<I', b, 0x48)[0]
for k in range(ovt_size // 32):
    oid, ram, size, bss, s0, s1, fid, flags = struct.unpack_from('<8I', b, ovt_off + 32 * k)
    if oid == 1: break
assert oid == 1 and not (flags >> 24) & 1, 'overlay 1 missing or compressed'
start, end = struct.unpack_from('<II', b, fat_off + 8 * fid)
assert struct.unpack_from('<II', b, start + 0x7E30) == (0x7555, 0x7FFF), ('unexpected literals', [hex(x) for x in struct.unpack_from('<II', b, start + 0x7E30)])
struct.pack_into('<II', b, start + 0x7E30, off_v, col_v)
open(dst, 'wb').write(b); print('overlay 1 at %#x: fog offset %#x, colour %#x' % (start, off_v, col_v))
