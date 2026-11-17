"""Write 7 frames (64x64 index arrays, 0 = clear) and a 15-colour palette into an overworld sprite of a/0/8/1 (BTX0, 4 bpp),
e.g. member 210 (Ho-Oh's cutscene bird). Sizes stay the same, so the NARC can be written in place.
python legend/write_ow.py NARC_IN NARC_OUT MEMBER PAL.npy IDX0.npy ... IDX6.npy"""
import sys, os, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack, pack
from g2d import lz10_dec
import nitro
SRC, DST, M, PALF = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]; IDX = [np.load(f) for f in sys.argv[5:]]
F = unpack(open(SRC, 'rb').read()); raw = F[M]; comp = raw[:1] == b'\x10'
d = bytearray(lz10_dec(raw) if comp else raw)
o = [nitro.u32(d, 16 + 4 * k) for k in range(nitro.u16(d, 14))][0]
t = nitro.read_tex(d, o)
f = t['raw_hdr']; tbo = f[6]; pbo = f[17]
for k, x in enumerate(t['texs']):
    assert x['fmt'] == 3 and x['w'] == 64 and x['h'] == 64
    ix = IDX[min(k, len(IDX) - 1)].astype(np.uint8).reshape(-1)
    off = (x['param'] & 0xffff) << 3
    d[o + tbo + off:o + tbo + off + 2048] = bytes(ix[0::2] | (ix[1::2] << 4))
pal = np.load(PALF)
po = t['pals'][0]['off']
def bgr(c): r, g, b = (int(round(v / 255 * 31)) for v in c); return r | g << 5 | b << 10
for i in range(16):
    struct.pack_into('<H', d, o + pbo + po + 2 * i, bgr(pal[i - 1]) if 1 <= i <= len(pal) else 0)
assert not comp, 'compressed member: re-compress not supported'
F[M] = bytes(d); open(DST, 'wb').write(pack(F)); print('wrote', len(t['texs']), 'frames into member', M)
