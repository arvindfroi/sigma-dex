"""Qwen front view -> 64x64 pixel sprite in 15 colours + transparent (index 0), like Ho-Oh's cutscene frames:
white background keyed from the corners, cropped, scaled so the creature fills 63 px wide (or 62 high), each block takes
its most common colour (outlines win ties), 15 colours by Lab k-means, then made mirror-symmetric (left half copied).
python legend/sab/pixelize.py IN.png OUT.png [SYM=1]"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
IN, OUT = sys.argv[1:3]; SYM = (sys.argv[3] if len(sys.argv) > 3 else '1') == '1'
a = np.asarray(Image.open(IN).convert('RGB')).astype(np.float32)
H, W = a.shape[:2]
white = (a.min(-1) > 225) & (a.max(-1) - a.min(-1) < 25)
lab, n = nd.label(white); edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1]); edge.discard(0)
bg = np.isin(lab, list(edge))
fg = ~bg; ys, xs = np.nonzero(fg); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
cx = (x0 + x1) / 2; half = max(cx - x0, x1 - cx); x0, x1 = int(cx - half), int(cx + half)   # centred on the body
s = min(63 / (x1 - x0), 62 / (y1 - y0)); nw, nh = round((x1 - x0) * s), round((y1 - y0) * s)
out = np.zeros((64, 64, 3)); vis = np.zeros((64, 64), bool)
ox, oy = (64 - nw) // 2, 63 - nh
lum = lambda c: 0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2]
for y in range(nh):
    for x in range(nw):
        ya, yb = int(y0 + y / s), int(y0 + (y + 1) / s); xa, xb = int(x0 + x / s), int(x0 + (x + 1) / s)
        blk = a[ya:max(yb, ya + 1), xa:max(xb, xa + 1)].reshape(-1, 3); m = fg[ya:max(yb, ya + 1), xa:max(xb, xa + 1)].reshape(-1)
        if m.mean() < 0.5: continue
        px = blk[m]; q = (px // 24).astype(int); key = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
        v, c = np.unique(key, return_counts=True); best = v[c == c.max()]
        cands = [px[key == b].mean(0) for b in best]; col = min(cands, key=lambda cc: lum(cc))
        out[oy + y, ox + x] = col; vis[oy + y, ox + x] = True
def to_lab(c):
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
px = out[vis]; L = to_lab(px)
import os
PAL = os.environ.get('PAL')                     # a sprite whose own colours are used (Sabertann's DS front sprite: 15 colours)
if PAL:
    pa = np.asarray(Image.open(PAL).convert('RGBA')); pal = np.unique(pa[pa[..., 3] > 0][:, :3], axis=0).astype(float)[:15]
    asg = ((L[:, None] - to_lab(pal)[None]) ** 2).sum(-1).argmin(1)
else:
    rng = np.random.default_rng(2); C = L[rng.choice(len(L), 15, replace=False)]
    for _ in range(30):
        asg = ((L[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([L[asg == j].mean(0) if (asg == j).any() else C[j] for j in range(15)])
    asg = ((L[:, None] - C[None]) ** 2).sum(-1).argmin(1)
    pal = np.array([px[asg == j].mean(0) if (asg == j).any() else [0, 0, 0] for j in range(15)])
pal = np.round(np.clip(pal, 0, 255) / 255 * 31) * 255 / 31
idx = np.zeros((64, 64), int); idx[vis] = asg + 1
if SYM:
    idx[:, 32:] = idx[:, :32][:, ::-1]                           # left half mirrored (Ho-Oh's frames are 97-98 % symmetric)
img = np.zeros((64, 64, 4), np.uint8); img[..., :3] = np.vstack([[0, 0, 0], pal])[idx]; img[..., 3] = (idx > 0) * 255
Image.fromarray(img).save(OUT)
np.save(OUT.replace('.png', '_idx.npy'), idx); np.save(OUT.replace('.png', '_pal.npy'), pal)
print(OUT, 'colours', len(np.unique(idx)) - 1, 'cover', round((idx > 0).mean(), 2))
