import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack
from g2d import lz10_dec
import nitro
F = unpack(open(sys.argv[1], 'rb').read())
for i, d in enumerate(F):
    if d[:1] == b'\x10': d = lz10_dec(d)
    if d[:4] not in (b'BTX0', b'BMD0'): continue
    offs = [nitro.u32(d, 16 + 4 * k) for k in range(nitro.u16(d, 14))]
    for o in offs:
        if d[o:o+4] == b'TEX0':
            t = nitro.read_tex(d, o)
            big = [x for x in t['texs'] if x['w'] >= 64 or x['h'] >= 64]
            if big: print(i, len(t['texs']), ', '.join(f"{x['name']}:{x['fmt']}:{x['w']}x{x['h']}" for x in t['texs'][:9]))
