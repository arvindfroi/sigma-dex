"""Overwrite NARC members in place (same offsets, zero padded, FATB unchanged), so a game holding an old FATB in RAM
(savestates) still finds every member. python legend/narc_inplace.py ORIG_NARC PATCHED_NARC OUT_NARC"""
import sys, struct; sys.path.insert(0, '.')
from narc import unpack
o = open(sys.argv[1], 'rb').read(); P = unpack(open(sys.argv[2], 'rb').read()); O = unpack(o)
off = 16; sz, = struct.unpack_from('<I', o, off + 4); n, = struct.unpack_from('<H', o, off + 8)
ents = [struct.unpack_from('<II', o, off + 12 + 8 * i) for i in range(n)]
off += sz; sz, = struct.unpack_from('<I', o, off + 4); off += sz; base = off + 8
out = bytearray(o)
for i, (a, b) in enumerate(ents):
    if P[i] == O[i]: continue
    assert len(P[i]) <= b - a, (i, len(P[i]), b - a)
    out[base + a:base + b] = P[i] + bytes(b - a - len(P[i])); print('member', i, len(P[i]), '/', b - a)
open(sys.argv[3], 'wb').write(out)
