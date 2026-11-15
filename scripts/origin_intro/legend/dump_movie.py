"""Render the frames of a/2/4/5 (the Clear Bell cinematic: frame i = screen i, tiles 68+i, palette 136+i; LZ11) to PNG
(local only). python legend/dump_movie.py NARC OUTDIR [FIRST LAST]"""
import sys, os, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack
from lz11 import lz11_dec
from g2d import read_ncgr, read_nclr, sections
from PIL import Image
F = unpack(open(sys.argv[1], 'rb').read()); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
a, b = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 67)
D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
def bgr(v): return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)
for i in range(a, b + 1):
    pal, bd = read_nclr(D(136 + i)); g = read_ncgr(D(68 + i)); raw = np.frombuffer(g['data'], np.uint8)
    t = raw.reshape(-1, 8, 8) if g['bpp'] == 8 else np.stack([raw & 15, raw >> 4], 1).reshape(-1, 8, 8)
    mg, v, s = sections(D(i)); o, sd = s[b'NRCS']; w, h = struct.unpack_from('<HH', sd, 8); sz = struct.unpack_from('<I', sd, 16)[0]
    e = np.array(struct.unpack_from(f'<{sz // 2}H', sd, 20)); tw = w // 8
    P = np.array([bgr(x) for x in pal])
    img = np.zeros((h, w, 3), np.uint8)
    for k, ent in enumerate(e[:(w // 8) * (h // 8)]):
        ti = ent & 1023; hf = ent >> 10 & 1; vf = ent >> 11 & 1; pb = ent >> 12
        if ti >= len(t): continue
        tt = t[ti]; tt = tt[:, ::-1] if hf else tt; tt = tt[::-1] if vf else tt
        idx = tt.astype(int) + (pb * 16 if g['bpp'] == 4 else 0)
        y, x = divmod(k, tw); img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = P[idx % len(P)]
    Image.fromarray(img[:192]).save(os.path.join(OUT, f'm{i:02d}.png'))
print('bpp', g['bpp'], 'size', w, h, 'pal entries', len(pal))
