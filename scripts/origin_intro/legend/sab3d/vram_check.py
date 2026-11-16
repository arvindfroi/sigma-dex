"""The Ho-Oh film's texture VRAM: the sky scene and the pagoda scene are loaded together at the cut and share 256 KB
(measured 2026-11-16: declared TEX0 texture data 261904 bytes worked, 263376 failed: the pagoda scene drew white).
python vram_check.py A243      -> prints each time-of-day pair (sky m, pagoda m) and exits 1 if one is over"""
import sys, os, struct
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d/legend'))
from narc import unpack
from lz11 import lz11_dec
import nitro
def lz10_dec(src):
    n = int.from_bytes(src[1:4], 'little'); out = bytearray(); i = 4
    while len(out) < n:
        fl = src[i]; i += 1
        for b in range(8):
            if len(out) >= n: break
            if fl & (0x80 >> b):
                v = src[i] << 8 | src[i + 1]; i += 2; ln = (v >> 12) + 3; ds = (v & 0xfff) + 1
                for _ in range(ln): out.append(out[-ds])
            else: out.append(src[i]); i += 1
    return bytes(out)
F = unpack(open(sys.argv[1], 'rb').read()); T = {}
for i in (0, 5, 10, 15, 19, 23):
    raw = F[i]; d = lz11_dec(raw) if raw[:1] == b'\x11' else lz10_dec(raw) if raw[:1] == b'\x10' else raw
    r = nitro.read_bmd(d); bo = [b for b in r['blocks'] if d[b:b + 4] == b'TEX0'][0]; T[i] = struct.unpack_from('<4sIIHHIIIHHIIIIHHII', d, bo)[3] << 3
ok = True
for a, b in ((0, 15), (5, 19), (10, 23)):
    s = T[a] + T[b]; ok &= s <= 262144; print('pair %d+%d: %d + %d = %d of 262144 %s' % (a, b, T[a], T[b], s, 'ok' if s <= 262144 else 'OVER'))
sys.exit(0 if ok else 1)
