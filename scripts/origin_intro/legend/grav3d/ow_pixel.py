"""Gravriel's overworld frames as DS pixel art: ow_render.py's 7 renders -> 64x64, 15 colours + clear, like Lugia's
LUG_OBJ01 frames (front view, a dark outline round the figure, one palette for all 7).
  - one framing for all frames: the union of the figures, scaled to HEIGHT px high (<= 64 wide), feet on the bottom row
  - palette: k-means (Lab) over all frames' figure pixels -> 14 colours, plus the outline colour (darkest, OUTLINE)
  - each sprite pixel takes the most common palette colour of its block among the figure's pixels (no blur); a pixel
    is figure when at least COVER of its block is
  - outline: figure pixels next to a clear pixel (4-neighbours) take the outline colour
python ow_pixel.py RENDER_DIR OUT_DIR   -> OUT_DIR/f{1..7}_idx.npy, pal.npy (15 x RGB, index 1..15), sheet.png (x4)
env: HEIGHT (62), COVER (0.5), OUTLINE ('18,30,32'), SEED (3)"""
import sys, os, json
import numpy as np
from PIL import Image
RD, OD = sys.argv[1:3]; os.makedirs(OD, exist_ok=True)
E = lambda k, d: float(os.environ.get(k, d))
R = [np.asarray(Image.open(os.path.join(RD, 'r%d.png' % k)).convert('RGBA')).astype(float) for k in range(1, 8)]
LB = [np.load(os.path.join(RD, 'l%d.npy' % k)) for k in range(1, 8)] if os.path.exists(os.path.join(RD, 'l1.npy')) else None
RJ = json.load(open(os.path.join(RD, 'render.json'))); LABS = RJ.get('labs', [])
# v2: the film's painting is dark for the film light; the sprite stands on a dim cave floor: lift and saturate
GAM, GAIN, SAT = E('GAMMA', 0.72), E('GAIN', 1.08), E('SAT', 1.25)
for r in R:
    c = 255 * np.clip((r[..., :3] / 255) ** GAM * GAIN, 0, 1); m = c.mean(-1, keepdims=True); r[..., :3] = np.clip(m + (c - m) * SAT, 0, 255)
al = np.zeros(R[0].shape[:2], bool)
for r in R: al |= r[..., 3] > 127
ys, xs = np.nonzero(al); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
H_ = int(E('HEIGHT', 62)); s = min(H_ / (y1 - y0), 64 / (x1 - x0)); nw, nh = int(round((x1 - x0) * s)), int(round((y1 - y0) * s))
ox, oy = (64 - nw) // 2, 64 - nh
def lab(c):
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
# palette from all frames' figure pixels (subsampled)
px = np.vstack([r[r[..., 3] > 127][:, :3] for r in R]); rng = np.random.default_rng(int(E('SEED', 3))); px = px[rng.choice(len(px), min(len(px), 60000), replace=False)]
L = lab(px); K = int(E('KMEANS', 13)); C = L[rng.choice(len(L), K, replace=False)]
for _ in range(40):
    a = ((L[:, None] - C[None]) ** 2).sum(-1).argmin(1); C = np.array([L[a == k].mean(0) if (a == k).any() else C[k] for k in range(K)])
a = ((L[:, None] - C[None]) ** 2).sum(-1).argmin(1); PAL = np.array([px[a == k].mean(0) if (a == k).any() else [0, 0, 0] for k in range(K)])
OUTL = np.array([float(v) for v in os.environ.get('OUTLINE', '18,30,32').split(',')]); EYE = np.array([float(v) for v in os.environ.get('EYEC', '150,240,255').split(',')])
order = np.argsort(lab(PAL)[:, 0]); PAL = np.vstack([OUTL[None], EYE[None], PAL[order]])   # 1 = outline, 2 = glowing eye, then dark -> light
PL = lab(PAL)
out = []
for k, r in enumerate(R):
    idx = np.zeros((64, 64), np.uint8)
    q = ((lab(r[..., :3])[:, :, None] - PL[None, None, 2:]) ** 2).sum(-1).argmin(-1) + 3      # source pixels -> palette 3..15
    # the eyes: cyan pixels of the face glow (the film's eye glow), so 1-2 px eyes survive the shrink
    cc = r[..., :3]; eye = (cc[..., 2] > cc[..., 0] + 40) & (cc[..., 1] > cc[..., 0] + 25) & (cc.mean(-1) > 110)
    if LB is not None: eye &= np.isin(LB[k] % 100, [LABS.index(x) for x in ('mask', 'skin', 'bone') if x in LABS]) & (LB[k] // 100 == 1)
    q[eye] = 2; lg = np.zeros((64, 64), np.int16)
    fg = r[..., 3] > 127
    for yy in range(nh):
        for xx in range(nw):
            ya, yb = int(y0 + yy / s), max(int(y0 + (yy + 1) / s), int(y0 + yy / s) + 1); xa, xb = int(x0 + xx / s), max(int(x0 + (xx + 1) / s), int(x0 + xx / s) + 1)
            m = fg[ya:yb, xa:xb]
            if m.mean() < E('COVER', 0.5): continue
            v = q[ya:yb, xa:xb][m]; bc = np.bincount(v); idx[oy + yy, ox + xx] = 2 if (len(bc) > 2 and bc[2] >= 0.25 * m.sum()) else bc.argmax()
            if LB is not None: lv = LB[k][ya:yb, xa:xb][m]; lg[oy + yy, ox + xx] = np.bincount(lv - lv.min()).argmax() + lv.min()
    f = idx > 0; edge = f & ~(np.pad(f, 1)[:-2, 1:-1] & np.pad(f, 1)[2:, 1:-1] & np.pad(f, 1)[1:-1, :-2] & np.pad(f, 1)[1:-1, 2:])
    idx[edge] = 1
    if LB is not None and os.environ.get('INNER', '1') == '1':
        # dark lines between the big parts, drawn on the part behind (DS sprites separate their parts like this)
        def grp(v):
            part, l_ = v // 100, (LABS[v % 100] if 0 <= v % 100 < len(LABS) else '')
            if part == 4: return 6
            if part in (2, 3): return 5
            return {'mask': 4, 'bone': 4, 'hat': 3, 'shell': 3, 'weed': 2}.get(l_, 1)
        G = np.vectorize(grp)(lg) * f
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = np.roll(np.roll(G, dy, 0), dx, 1); line = f & (nb > G) & (nb > 0) & (idx != 2)
            idx[line] = 1
    out.append(idx); np.save(os.path.join(OD, 'f%d_idx.npy' % (k + 1)), idx)
np.save(os.path.join(OD, 'pal.npy'), PAL.round().astype(int))
BG = np.array([40, 44, 60]); sh = np.zeros((64, 64 * 7 + 6 * 4, 3)) + 255
for k, idx in enumerate(out):
    im = np.where(idx[..., None] > 0, np.vstack([[0, 0, 0], PAL])[idx], BG); sh[:, k * 68:k * 68 + 64] = im
Image.fromarray(sh.astype(np.uint8)).resize((sh.shape[1] * 4, 256), Image.NEAREST).save(os.path.join(OD, 'sheet.png'))
json.dump(dict(height=H_, size=[nw, nh], offset=[ox, oy], palette=PAL.round().astype(int).tolist()), open(os.path.join(OD, 'pixel.json'), 'w'), indent=1)
print('ok', OD, 'figure', nw, 'x', nh, 'at', ox, oy)
