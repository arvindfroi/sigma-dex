"""Gravriel's cave (Lugia's film a/2/4/4, member 0 `demoapri_r`): keep the cave, recolour the water (Arvind 2026-11-16:
"keep the cave, but the colour of the water, and add fog"). Every palette of the sea, the falling water (all animation
frames), the pond edge and the waves is mapped by brightness onto a gradient (dark -> mid -> light), so the foam and the
ripples still read; alpha and the cave walls are untouched. Same size, written in place.
python cave_tint.py A244_IN A244_OUT     env: WDARK, WMID, WLIGHT ('r,g,b'), WMIX (0..1, how much of the new colour)"""
import sys, os, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(0, os.path.join(HERE, '..'))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
SRC, DST = sys.argv[1:3]
col = lambda k, d: np.array([float(x) for x in os.environ.get(k, d).split(',')])
DARK, MID, LIGHT = col('WDARK', '6,26,24'), col('WMID', '38,92,78'), col('WLIGHT', '176,214,190'); MIX = float(os.environ.get('WMIX', '0.9'))
WATER = ('dsea_on', 'dsea_un', 'sea_un', 'sea_f02', 'sea_line02', 'r_dpond_line', 'uzu_taki')
F = unpack(open(SRC, 'rb').read()); d = bytearray(lz11_dec(F[0]) if F[0][:1] == b'\x11' else F[0])
r = nitro.read_bmd(bytes(d))
def from555(v): return np.array([(v & 31), (v >> 5) & 31, (v >> 10) & 31], float) * 255 / 31
def to555(c): c = np.clip(np.round(c / 255 * 31), 0, 31).astype(int); return int(c[0] | c[1] << 5 | c[2] << 10)
def grad(y):
    return DARK + (MID - DARK) * (y / 0.5) if y < 0.5 else MID + (LIGHT - MID) * ((y - 0.5) / 0.5)
n = 0
for bo in r['blocks']:
    if d[bo:bo + 4] != b'TEX0': continue
    t = nitro.read_tex(bytes(d), bo); pbo = t['raw_hdr'][17]
    pals = sorted(t['pals'], key=lambda p: p['off']); ends = [p['off'] for p in pals[1:]] + [None]
    for p, end in zip(pals, ends):
        if not p['name'].startswith(WATER): continue
        cnt = min(16, ((end - p['off']) // 2) if end else 16, (len(d) - (bo + pbo + p['off'])) // 2)
        for i in range(cnt):
            a = bo + pbo + p['off'] + 2 * i; v = struct.unpack_from('<H', d, a)[0]; c = from555(v)
            y = float(c @ np.array([0.3, 0.59, 0.11])) / 255
            struct.pack_into('<H', d, a, to555(c * (1 - MIX) + grad(y) * MIX) | (v & 0x8000))
        n += 1
print('water palettes recoloured', n)
F[0] = lz10_enc(bytes(d)); open(DST, 'wb').write(pack(F)); print('file', len(pack(F)))
