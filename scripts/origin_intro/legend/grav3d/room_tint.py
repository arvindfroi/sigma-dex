"""The Lugia cave room in the overworld gets the same green water as the film (Arvind 2026-11-16: the whole room).
Texture set 98 (a/0/4/4) is used by area 98 = maps 244 (Lugia cave) and 486 (Whirl Islands B3F): both change.
Same palette mapping as cave_tint.py, written in place.   python room_tint.py A044_IN A044_OUT [SET=98]"""
import sys, os, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(0, os.path.join(HERE, '..'))
from narc import unpack, pack
import nitro
SRC, DST = sys.argv[1:3]; SET = int(sys.argv[3]) if len(sys.argv) > 3 else 98
col = lambda k, d: np.array([float(x) for x in os.environ.get(k, d).split(',')])
DARK, MID, LIGHT = col('WDARK', '6,26,24'), col('WMID', '38,92,78'), col('WLIGHT', '176,214,190'); MIX = float(os.environ.get('WMIX', '0.9'))
WATER = ('dsea_on', 'dsea_un', 'sea_un', 'sea_f02', 'sea_line02', 'r_dpond_line', 'uzu_taki', 'uzushio')
F = unpack(open(SRC, 'rb').read()); d = bytearray(F[SET]); assert d[:4] == b'BTX0'
bo = struct.unpack_from('<I', d, 16)[0]; t = nitro.read_tex(bytes(d), bo); pbo = t['raw_hdr'][17]
def from555(v): return np.array([(v & 31), (v >> 5) & 31, (v >> 10) & 31], float) * 255 / 31
def to555(c): c = np.clip(np.round(c / 255 * 31), 0, 31).astype(int); return int(c[0] | c[1] << 5 | c[2] << 10)
def grad(y): return DARK + (MID - DARK) * (y / 0.5) if y < 0.5 else MID + (LIGHT - MID) * ((y - 0.5) / 0.5)
# the blue boulders in the pool in front of the fall (r_sea_rock) and the blue wet-rock pattern (cliff01gs) get a wet
# grey-green stone gradient (Arvind 2026-11-16: "the rocks with the waterfall")
ROCK = tuple(x for x in os.environ.get('ROCKS', 'r_sea_rock,cliff01').split(',') if x)
RDARK, RMID, RLIGHT = col('RDARK', '18,34,32'), col('RMID', '64,96,86'), col('RLIGHT', '156,184,166')
def rgrad(y): return RDARK + (RMID - RDARK) * (y / 0.5) if y < 0.5 else RMID + (RLIGHT - RMID) * ((y - 0.5) / 0.5)
pals = sorted(t['pals'], key=lambda p: p['off']); ends = [p['off'] for p in pals[1:]] + [None]; n = 0; nr = 0
for p, end in zip(pals, ends):
    if ROCK and p['name'].startswith(ROCK):
        cnt = min(16, ((end - p['off']) // 2) if end else 16, (len(d) - (bo + pbo + p['off'])) // 2)
        for i in range(cnt):
            a = bo + pbo + p['off'] + 2 * i; v = struct.unpack_from('<H', d, a)[0]; c = from555(v)
            struct.pack_into('<H', d, a, to555(c * (1 - MIX) + rgrad(float(c @ np.array([0.3, 0.59, 0.11])) / 255) * MIX) | (v & 0x8000))
        nr += 1; continue
    if not p['name'].startswith(WATER): continue
    cnt = min(16, ((end - p['off']) // 2) if end else 16, (len(d) - (bo + pbo + p['off'])) // 2)
    for i in range(cnt):
        a = bo + pbo + p['off'] + 2 * i; v = struct.unpack_from('<H', d, a)[0]; c = from555(v)
        struct.pack_into('<H', d, a, to555(c * (1 - MIX) + grad(float(c @ np.array([0.3, 0.59, 0.11])) / 255) * MIX) | (v & 0x8000))
    n += 1
F[SET] = bytes(d); open(DST, 'wb').write(pack(F)); print('room water palettes', n, 'rock palettes', nr, 'file', len(pack(F)))
