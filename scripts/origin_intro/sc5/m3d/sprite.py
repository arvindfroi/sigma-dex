"""Scene 5 v4, step 5: the render passes -> Moosus as a pixel sprite on the original rock (48x64 RGBA for build_sc5.py).
python sc5/m3d/sprite.py PASSDIR OUT.png [HEIGHT] [X] [TIME]
- crop to the figure, shrink to HEIGHT px tall: each pixel takes the majority class of its block (thin parts weigh more)
  and the mean light / crown height / nearness of that class
- cel shading like the original sprites: per material a few flat tones picked by the light (Suicune's crop has 3-4 per part)
- 1 px outline in the scene's dark blue round the figure, plus inner lines where a nearer part overlaps a farther one
- placed with the hooves on the rock top, the rump cut by the left edge like Suicune; at most 11 colours of its own
TIME: day (default, for comparing with Suicune) or night (aurora light from behind, for the fjord)"""
import sys, os, numpy as np
from PIL import Image
from scipy import ndimage as nd
P, OUT = sys.argv[1:3]; HT = int(sys.argv[3]) if len(sys.argv) > 3 else 36; XA = sys.argv[4] if len(sys.argv) > 4 else '-6'                # a number, or tip:N = the rightmost pixel (snout) at x N
TIME = sys.argv[5] if len(sys.argv) > 5 else 'day'
HERE = os.path.dirname(os.path.abspath(__file__))
import cv2
rd = lambda n: cv2.imread(os.path.join(P, n), cv2.IMREAD_UNCHANGED)[..., [2, 1, 0, 3]].astype(np.float64) / 65535   # 16-bit BGRA
info, nrm = rd('info.png'), rd('nrm.png')
A = info[..., 3] > 0.5
cls = np.round(info[..., 0] * 10).astype(int); t = info[..., 1]; dep = info[..., 2]
n = np.stack([nrm[..., 0] * 2 - 1, nrm[..., 1] * 2 - 1, 2 * nrm[..., 2] - 1], -1)   # Cycles camera space: +Z points away, so the stored -0.5 flip makes +Z face us
n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
L = np.array([-0.35, 0.75, 0.55]) if TIME == 'day' else np.array([0.55, 0.45, -0.7])   # night: aurora behind, to the right
L /= np.linalg.norm(L)
lit = (n * L).sum(-1)
if TIME == 'night': lit = lit * 0.9 + 0.25 * n[..., 1]                                  # a little sky light from above
ys, xs = np.nonzero(A); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
f = (y1 - y0) / HT; WT = int(np.ceil((x1 - x0) / f))
X0 = int(XA[4:]) - WT if XA.startswith('tip:') else int(XA)
W8 = np.array([1.0, 1.0, 2.2, 3.0])                                                      # pale, brown, crown, dark
C = np.full((HT, WT), -1); LIT = np.zeros((HT, WT)); T = np.zeros((HT, WT)); D = np.zeros((HT, WT))
for j in range(HT):
    for i in range(WT):
        sy0, sy1 = int(y0 + j * f), int(y0 + (j + 1) * f); sx0, sx1 = int(x0 + i * f), int(x0 + (i + 1) * f)
        a = A[sy0:sy1, sx0:sx1]
        if a.size == 0 or a.mean() < 0.42: continue
        c = cls[sy0:sy1, sx0:sx1][a]
        k = int(np.argmax(np.bincount(c, minlength=4) * W8)); m = c == k
        C[j, i] = k; LIT[j, i] = lit[sy0:sy1, sx0:sx1][a][m].mean(); T[j, i] = t[sy0:sy1, sx0:sx1][a][m].mean()
        D[j, i] = dep[sy0:sy1, sx0:sx1][a].max()
fig = C >= 0
LINE = (41, 90, 123)
if TIME == 'day':
    RAMP = {0: [(132, 118, 197), (189, 172, 238), (230, 222, 255), (255, 255, 255)],
            1: [(106, 57, 41), (164, 98, 57), (213, 148, 90)],
            3: [LINE]}
    CROWN = [(98, 205, 156), (90, 197, 222), (172, 123, 238)]
    TH = {0: (-0.05, 0.35, 0.7), 1: (0.05, 0.5)}
else:
    # night, northern lights over the fjord ahead (to the right, high, a little beyond): every material = night base +
    # one shadow layer (the originals' cel rule) + a green aurora-lit layer on the faces turned to it; the crown glows
    RAMP = {0: [(57, 57, 115), (106, 106, 172), (148, 213, 197)],
            1: [(57, 32, 41), (115, 72, 62), (139, 131, 106)],
            3: [(16, 24, 49)]}
    CROWN = [(82, 238, 156), (98, 230, 230), (197, 148, 255)]
    LINE = (16, 24, 49)
img = np.zeros((HT, WT, 3), int)
if TIME == 'night':
    AU = np.array([float(v) for v in os.environ.get('SC5_AU', '0.75,0.5,-0.2').split(',')]); AU /= np.linalg.norm(AU); AM = np.array([0.0, 0.75, 0.65]); AM /= np.linalg.norm(AM)
    AU_T, AM_T = float(os.environ.get('SC5_AUT', 0.35)), float(os.environ.get('SC5_AMT', 0.3))
    au = (n * AU).sum(-1); am = (n * AM).sum(-1)
    AUs = np.zeros((HT, WT)); AMs = np.zeros((HT, WT))
    for j in range(HT):
        for i in range(WT):
            if C[j, i] < 0: continue
            sy0, sy1 = int(y0 + j * f), int(y0 + (j + 1) * f); sx0, sx1 = int(x0 + i * f), int(x0 + (i + 1) * f)
            a = A[sy0:sy1, sx0:sx1] & (cls[sy0:sy1, sx0:sx1] == C[j, i])
            AUs[j, i] = au[sy0:sy1, sx0:sx1][a].mean(); AMs[j, i] = am[sy0:sy1, sx0:sx1][a].mean()
    for k in (0, 1, 3):
        m = C == k; r = RAMP[k]
        lv = np.where(AUs[m] > AU_T, 2, np.where(AMs[m] > AM_T, 1, 0)) if len(r) == 3 else np.zeros(m.sum(), int)
        img[m] = np.array(r)[lv]
for k in ((0, 1, 3) if TIME == 'day' else ()):
    m = C == k; th = TH.get(k, ()); lv = np.zeros(m.sum(), int)
    for v in th: lv += LIT[m] > v
    img[m] = np.array(RAMP[k])[np.minimum(lv, len(RAMP[k]) - 1)]
m = C == 2; img[m] = np.array(CROWN)[np.minimum((T[m] * 3).astype(int), 2)]
# inner lines: a farther pixel next to a much nearer one (legs behind legs, body behind the head) gets the line colour
near = np.zeros_like(fig)
for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    sh = np.roll(np.roll(D, dy, 0), dx, 1); fs = np.roll(np.roll(fig, dy, 0), dx, 1)
    near |= fs & (sh - D > 0.12)
inner = fig & near & (C != 2)
img[inner] = LINE
# the original rock, Suicune's legs filled from below (as sc5/compose.py)
o = np.array(Image.open(os.path.join(HERE, '..', 'orig_crop.png')).convert('RGBA')).astype(int); H, W = o.shape[:2]
rgb = o[..., :3]; op = o[..., 3] > 0
ROCK = [(74, 106, 164), (106, 131, 180), (139, 156, 197)]
isr = np.zeros((H, W), bool)
for c in ROCK: isr |= (rgb == c).all(-1) & op
rock = np.zeros((H, W), bool); lower = np.zeros((H, W), bool); lower[38:] = True
for x in range(W):
    yy = np.nonzero(isr[:, x] & lower[:, x])[0]
    if len(yy): rock[yy[0]:, x] = op[yy[0]:, x]
rk = rgb.copy(); bad = rock & ~isr & ~(rgb == (41, 90, 123)).all(-1)
for y, x in sorted(zip(*np.nonzero(bad)), reverse=True):
    yy = y + 1
    while yy < H and bad[yy, x]: yy += 1
    rk[y, x] = rk[yy, x] if yy < H and rock[yy, x] else ROCK[0]
if TIME == 'night':                                       # the rock at night: slate blue, its top face caught by the aurora
    NR = {(139, 156, 197): (74, 115, 123), (106, 131, 180): (49, 66, 98), (74, 106, 164): (32, 41, 74), (41, 90, 123): LINE}
    for a_, b_ in NR.items(): rk[(rk == a_).all(-1)] = b_
out = np.zeros((H, W, 4), np.uint8); out[rock, :3] = rk[rock]; out[rock, 3] = 255
# place: the lowest figure row (hooves) sinks 1 px into the rock top under it
rows = np.nonzero(fig.any(1))[0]; bot = rows.max()
hx = np.nonzero(fig[bot])[0]; tops = [np.nonzero(rock[:, X0 + x])[0][0] for x in hx if 0 <= X0 + x < W and rock[:, X0 + x].any()]
Y0 = (int(np.median(tops)) if tops else 40) + 1 - bot
fm = np.zeros((H, W), bool)
for j in range(HT):
    for i in range(WT):
        y, x = Y0 + j, X0 + i
        if fig[j, i] and 0 <= y < H and 0 <= x < W: out[y, x, :3] = img[j, i]; out[y, x, 3] = 255; fm[y, x] = True
ring = nd.binary_dilation(fm, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]]) & ~fm & ~rock
out[ring, :3] = LINE; out[ring, 3] = 255
# rock pixels right under the figure's outline: the line too (it stands ON the rock)
Image.fromarray(out).save(OUT)
own = np.unique(out[fm | ring][:, :3], axis=0)
print(OUT, 'figure', WT, 'x', HT, 'at', X0, Y0, 'own colours', len(own))
