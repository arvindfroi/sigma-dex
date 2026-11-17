"""Sabertann's Ho-Oh film v33: the locked v32 with less texture VRAM, so it no longer freezes in the daytime (2026-11-17:
v32's 259280 bytes freeze in the morning and at midday, when the sun flare needs VRAM too; Origin's film padded to
240000 bytes is clean in the morning, 248000 shows garbage; vram_pad_test.py / heap_pad_test.py).
The chosen 8-bpp textures go to 4 bpp (16 colours) with the same size, so the texture coordinates do not change: a
16-colour palette by k-means in Lab over the texture's colours, each colour weighted by its count (POWER 1.0: the least
error over the area; POWER 0.5, the square root, gave rare colours more slots but turned the dark fur brownish and
blotchy), every texel to its nearest colour. Everything else in the
film file is v32's, bit for bit. The textures are the same in all three times of day (sky 0/5/10, pagoda 15/19/23).
python vram_trim.py A243_V32 OUT_A243 [NAME@sky|pagoda ...]
default: ho_head_top@sky hou_mouth01@sky ho_head_top@pagoda hou_eye@pagoda hou_mouth01@pagoda
(the sky shot's hou_eye, which holds the face close-up of the fly-by, stays 8 bpp)"""
import sys, os, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', '..')); sys.path.insert(0, os.path.join(H, '..'))
sys.path.insert(0, os.path.join(H, '..', 'grav3d'))
import numpy as np
from narc import unpack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro, tex0_grow
from sklearn.cluster import KMeans
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
dec = lambda raw: lz11_dec(raw) if raw[:1] == b'\x11' else lz10_dec(raw) if raw[:1] == b'\x10' else raw
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
SRC, DST = sys.argv[1:3]; POWER = float(os.environ.get('POWER', 1.0))
want = sys.argv[3:] or ['ho_head_top@sky', 'hou_mouth01@sky', 'ho_head_top@pagoda', 'hou_eye@pagoda', 'hou_mouth01@pagoda']
GROUP = {'sky': (0, 5, 10), 'pagoda': (15, 19, 23)}
F = unpack(open(SRC, 'rb').read()); cache = {}
for m in range(len(F)):
    g = 'sky' if m in GROUP['sky'] else 'pagoda' if m in GROUP['pagoda'] else None
    names = [w.split('@')[0] for w in want if w.split('@')[1] == g]
    if not names: continue
    d = dec(F[m]); bo = [b for b in nitro.read_bmd(d)['blocks'] if d[b:b + 4] == b'TEX0'][0]; t = nitro.read_tex(d, bo)
    pals = {p['name']: p['off'] for p in t['pals']}; texd, pald = {}, {}
    for x in t['texs']:
        if x['name'] not in names: continue
        assert x['fmt'] == 4, (x['name'], x['fmt'])
        key = (g, x['name'], x['data'], t['paldata'][pals[x['name'] + '_pl']:pals[x['name'] + '_pl'] + 512])
        if key not in cache:
            raw = np.frombuffer(key[3], '<u2'); rgb = np.stack([raw & 31, (raw >> 5) & 31, (raw >> 10) & 31], -1).astype(float)
            idx = np.frombuffer(x['data'], np.uint8)
            cols, counts = np.unique(idx, return_counts=True); L = lab(rgb[cols] * 255 / 31)
            wt = counts ** POWER
            km = KMeans(16, n_init=8, random_state=0).fit(L, sample_weight=wt)
            # each centre as the weighted mean of its colours in 5-bit (the DS palette), each old colour to its nearest centre
            c5 = np.array([np.round(np.average(rgb[cols][km.labels_ == k], 0, wt[km.labels_ == k])) if (km.labels_ == k).any() else [0, 0, 0] for k in range(16)]).astype(int)
            lut = np.zeros(256, np.uint8); lut[cols] = ((L[:, None] - lab(c5 * 255 / 31)[None]) ** 2).sum(-1).argmin(1)
            q = lut[idx]; raw4 = bytes((q[0::2] | (q[1::2] << 4)).astype(np.uint8))
            pal16 = struct.pack('<16H', *[int(c[0] | c[1] << 5 | c[2] << 10) for c in c5])
            de = np.sqrt(((L - lab(c5[lut[cols]] * 255 / 31)) ** 2).sum(1)); w = counts / counts.sum()
            print('%-7s %-12s %dx%d 8bpp -> 4bpp, dE over the area %.2f, worst colour %.1f (%.2f%% of the area over 10)' % (g, x['name'], x['w'], x['h'], (de * w).sum(), de.max(), 100 * w[de > 10].sum()))
            cache[key] = (raw4, pal16)
        raw4, pal16 = cache[key]; texd[x['name']] = (3, x['w'], x['h'], raw4); pald[x['name'] + '_pl'] = pal16
    F[m] = lz10_enc(tex0_grow.grow(d, texd, pald))
btaf = bytearray(b'BTAF' + b'\0' * 4 + struct.pack('<HH', len(F), 0)); gm = bytearray()
for f in F:
    s = len(gm); gm += f; btaf += struct.pack('<II', s, len(gm))
    while len(gm) % 4: gm += b'\xff'
struct.pack_into('<I', btaf, 4, len(btaf))
btnf = b'BTNF' + struct.pack('<I', 16) + struct.pack('<IHH', 4, 0, 1)
gmif = b'GMIF' + struct.pack('<I', len(gm) + 8) + gm
body = bytes(btaf) + btnf + gmif
open(DST, 'wb').write(b'NARC' + struct.pack('<HHIHH', 0xFFFE, 0x0100, 16 + len(body), 16, 3) + body); print('ok', DST, 16 + len(body))
