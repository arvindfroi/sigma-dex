"""First look: the intro frames of Sabertann (v15 frames) and Gravriel (v16 sprite) shrunk to fit 64x64 like the
cutscene sprites (a/0/8/1 210 Ho-Oh, 211 Lugia), next to the originals (local only). Mode filter, 15 colours.
python legend/test_sheet.py OUT.png"""
import sys, os, numpy as np
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..')
import json
def load(path):
    im = Image.open(path)
    if im.mode == 'L':                                   # Gravriel's frames: indices into pal.json, 0 = clear
        P = np.array(json.load(open(os.path.join(os.path.dirname(path), 'pal.json')))['palette']); ix = np.array(im)
        return np.dstack([P[ix], (ix > 0) * 255]).astype(int)
    return np.array(im.convert('RGBA')).astype(int)
def shrink(path, size=62, bg=None):
    im = load(path)
    if bg is None: bg = im[0, 0, :3]
    a = (im[..., 3] > 0) if (im[..., 3] == 0).any() else (np.abs(im[..., :3] - bg).sum(-1) > 6)
    ys, xs = np.nonzero(a); im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape; s = size / max(h, w); nh, nw = max(1, round(h * s)), max(1, round(w * s))
    out = np.zeros((64, 64, 4), np.uint8); oy, ox = 64 - nh - 1, (64 - nw) // 2
    for y in range(nh):
        for x in range(nw):
            y0, y1 = int(y / s), max(int(y / s) + 1, int((y + 1) / s)); x0, x1 = int(x / s), max(int(x / s) + 1, int((x + 1) / s))
            m = a[y0:y1, x0:x1]
            if m.mean() < 0.5: continue
            px = im[y0:y1, x0:x1][m][:, :3]; k, n = np.unique(px, axis=0, return_counts=True)
            out[oy + y, ox + x, :3] = k[n.argmax()]; out[oy + y, ox + x, 3] = 255
    return Image.fromarray(out)
def row(ims, label_bg):
    W = 7 * 68; r = Image.new('RGBA', (W, 64), label_bg)
    for i, im in enumerate(ims[:7]): r.alpha_composite(im, (i * 68, 0))
    return r
ow = os.path.join(H, 'ow')
hooh = [Image.open(f'{ow}/210_hou_obj01.{i}.png') for i in range(1, 8)]
lug = [Image.open(f'{ow}/211_lug_obj01.{i}.png') for i in range(1, 8)]
sv = os.path.join(R, 'variants/v15/v5px')
sab = [shrink(f'{sv}/f{i}.png') for i in (5, 6, 7, 8, 9, 1, 9)]      # leap x4 ... landed, roar (rough mapping)
gv = os.path.join(R, 'grav/px2d_v16')
grav = [shrink(f'{gv}/{p}.png') for p in ('p0_stare', 'p1_stare', 'p2_stare', 'p1_stare', 'p0_left', 'p0_right', 'p0_glow')]
bg = (52, 60, 84, 255)
rows = [row(hooh, bg), row(sab, bg), row(lug, bg), row(grav, bg)]
sheet = Image.new('RGBA', (7 * 68, 4 * 72), (30, 30, 40, 255))
for i, r in enumerate(rows): sheet.alpha_composite(r, (0, i * 72))
sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(sys.argv[1])
