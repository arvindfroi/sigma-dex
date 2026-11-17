"""Gravriel's eye glimmer (a/1/7/4 member 28, the SoulSilver path of the Lugia ritual: the creature's dark form shows
faintly in the cave and its eyes glint before it arrives). The member is a little model: plane 'karada' (body) with
the 64x64 A5I3 textures eye.1-6 (one blue tint, soft-edged alpha up to 19 of 31; 1/3/5 and 2/4/6 are two poses, getting
lighter), and a smaller plane 'me' (eyes) in front with de_ao_e7.1-3 (32x32, 2 bpp: two glinting eyes; .3 is empty).
The eye plane sits at the body texture's centre (31.5, 30.7), so Gravriel's silhouette is his overworld frame scaled up
(SCALE) with his eyes on that spot, head and shoulders filling the frame like Lugia's; the glints are redrawn as his
round owl eyes with heavy lids drooping outward, at his eye spacing. Tints, palettes and alpha levels stay Origin's.
python ow_glimmer.py NARC_IN NARC_OUT OWFRAMES_DIR [PREVIEW.png]     (written in place, same size)
env: SCALE (1.4), POSE_A (1), POSE_B (3)"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(0, os.path.join(HERE, '..'))
from narc import unpack, pack
import nitro
SRC, DST, OWD = sys.argv[1:4]; PRE = sys.argv[4] if len(sys.argv) > 4 else None
E = lambda k, d: float(os.environ.get(k, d))
F = unpack(open(SRC, 'rb').read()); d = bytearray(F[28])
o = [nitro.u32(d, 16 + 4 * k) for k in range(nitro.u16(d, 14))]; bo = [b for b in o if d[b:b + 4] == b'TEX0'][0]; t = nitro.read_tex(bytes(d), bo)
tbo, pbo = t['raw_hdr'][6], t['raw_hdr'][17]; P = {p['name']: p for p in t['pals']}
# his overworld frames and where his eyes are in them (the glowing iris pixels)
pal = np.load(os.path.join(OWD, 'pal.npy')); f = {k: np.load(os.path.join(OWD, f'f{k}_idx.npy')) for k in range(1, 8)}
eyecol = [i + 1 for i, c in enumerate(pal) if c[2] > 180 and c[1] > 150 and c[0] < 160]           # cyan iris / eye white
ys, xs = np.nonzero(np.isin(f[1], eyecol) & (np.arange(64)[:, None] < 30)); ecx, ecy = xs.mean(), ys.mean()
# eye spacing: the two clusters
left = xs < ecx; sep = xs[~left].mean() - xs[left].mean()
SC = E('SCALE', 1.4); CX, CY = 31.5, 30.7
GHOST = os.environ.get('GHOST', '1') == '1'          # v3 (Arvind: "match his colour, maybe the green ghost form"): 8 green tones
P1 = np.vstack([[0, 0, 0], pal]); LUMP = P1 @ np.array([0.3, 0.55, 0.15])
def silhouette(fr):
    m = fr > 0; out = np.zeros((64, 64), bool); lv = np.zeros((64, 64), np.uint8)
    yy, xx = np.mgrid[0:64, 0:64]; sx = ecx + (xx - CX) / SC; sy = ecy + (yy - CY) / SC
    ok = (sx >= 0) & (sx < 64) & (sy >= 0) & (sy < 64); out[ok] = m[sy[ok].astype(int), sx[ok].astype(int)]
    src = np.zeros((64, 64)); src[ok] = LUMP[fr[sy[ok].astype(int), sx[ok].astype(int)]]
    out = ndimage.binary_closing(out, iterations=1)
    dist = ndimage.distance_transform_edt(np.pad(out, 1))[1:-1, 1:-1]
    al = np.where(out, np.clip(4 * dist - 2, 1, 19), 0).astype(np.uint8)          # Lugia's ramp: 2, 6, 10, 14, 18, 19
    if GHOST:                                          # his own light and dark inside the ghost: 8 levels by the sprite's brightness
        v = src[out & (src > 0)]; q = np.percentile(v, np.linspace(0, 100, 9)[1:-1]) if len(v) else np.zeros(7)
        lv[out] = np.searchsorted(q, src[out]).clip(0, 7)
        lv[out & (src == 0)] = 0
    return al, lv
POSE = {1: int(E('POSE_A', 1)), 2: int(E('POSE_B', 3))}
sil = {k: silhouette(f[POSE[k]]) for k in (1, 2)}
def ghost(l, gain):                                    # the film's ghost colour (rig_lugia: 0.35l+10, 1.05l+60, 0.8l+44)
    return np.clip(np.array([0.35 * l + 10, 1.05 * l + 60, 0.8 * l + 44]) * gain, 0, 248)
STAGE = {1: 0.62, 2: 0.62, 3: 0.8, 4: 0.8, 5: 1.0, 6: 1.0}  # darker -> lighter like Lugia's three tints
for x in t['texs']:
    off = (x['param'] & 0xffff) << 3
    if x['name'].startswith('eye.'):
        n = int(x['name'][4:]); a, lv = sil[1 if n % 2 else 2]; assert x['fmt'] == 6 and x['w'] == 64
        d[bo + tbo + off:bo + tbo + off + 4096] = bytes(((a.astype(np.uint8) << 3) | (lv if GHOST else 0)).ravel())   # alpha, colour index
        if GHOST:
            pl = P[x['name'] + '_pl']; po = bo + pbo + pl['off']
            for j in range(8):
                c = ghost(20 + j * 24, STAGE[n]); v = int(c[0]) >> 3 | (int(c[1]) >> 3) << 5 | (int(c[2]) >> 3) << 10
                d[po + 2 * j:po + 2 * j + 2] = v.to_bytes(2, 'little')
    elif x['name'] in ('de_ao_e7.1', 'de_ao_e7.2'):
        # round owl eyes, heavy lids drooping outward; 3 = bright core, 2 = glow, 1 = rim; at his spacing in plane px
        gs = sep * SC * 1.055 / 18 * 32; g = np.zeros((32, 32), np.uint8)
        for side in (-1, 1):
            cx_, cy_ = 16 + side * gs / 2, 15.5; rx, ry = E("GLINT_RX", 5.0), E("GLINT_RY", 4.4)
            for yy in range(32):
                for xx in range(32):
                    u, v = (xx + 0.5 - cx_) / rx, (yy + 0.5 - cy_) / ry; r = u * u + v * v
                    lid = cy_ - ry * (0.15 + 0.45 * max(0.0, side * (xx + 0.5 - cx_) / rx))        # the lid line, lower toward the outside
                    if r < 1 and yy + 0.5 > lid: g[yy, xx] = 3 if r < 0.35 else 2 if r < 0.7 else 1
        raw = g.reshape(-1, 4); d[bo + tbo + off:bo + tbo + off + 256] = bytes((raw[:, 0] | raw[:, 1] << 2 | raw[:, 2] << 4 | raw[:, 3] << 6).astype(np.uint8))
F[28] = bytes(d); open(DST, 'wb').write(pack(F))
print('eye glimmer: silhouettes from frames', POSE, 'scale', SC, 'eyes at', (round(ecx, 1), round(ecy, 1)), 'spacing', round(sep, 1))
if PRE:
    t2 = nitro.read_tex(bytes(d), bo); row = []
    for x in t2['texs']:
        pl = P[x['name'] + '_pl']; pd = bytes(d[bo + pbo + pl['off']: bo + pbo + pl['off'] + 16])
        cols = np.array([((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8) for v in np.frombuffer(pd, '<u2')])
        if x['name'].startswith('eye.'):
            a = np.frombuffer(x['data'], np.uint8).reshape(64, 64); al = (a >> 3) / 31 * 2.2; rgb = cols[a & 7]
            row.append(np.clip(np.array([40, 44, 60]) * (1 - al[..., None]) + rgb * al[..., None], 0, 255))
    # the glint over the body, as in the game: plane 'me' 17 px wide centred on (CX, CY)
    x1 = [x for x in t2['texs'] if x['name'] == 'de_ao_e7.1'][0]; raw = np.frombuffer(x1['data'], np.uint8); gi = np.stack([(raw >> s) & 3 for s in (0, 2, 4, 6)], 1).reshape(32, 32)
    pl = P['de_ao_e7.1_pl']; pd = bytes(d[bo + pbo + pl['off']: bo + pbo + pl['off'] + 8]); gc = np.array([((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8) for v in np.frombuffer(pd, '<u2')])
    gim = np.asarray(Image.fromarray(gi).resize((17, 17), Image.NEAREST))
    for r_ in row[:2]:
        y0, x0 = int(round(CY - 8.5)), int(round(CX - 8.5)); sub = r_[y0:y0 + 17, x0:x0 + 17]; sub[gim > 0] = gc[gim[gim > 0]]
    z = np.concatenate([np.pad(r, ((2, 2), (2, 2), (0, 0)), constant_values=255) for r in row], 1)
    Image.fromarray(z.astype(np.uint8)).resize((z.shape[1] * 4, z.shape[0] * 4), Image.NEAREST).save(PRE); print('preview', PRE)
