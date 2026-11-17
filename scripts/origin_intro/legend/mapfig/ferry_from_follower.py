"""Mooceon as the ride-on Pokemon in Lapras's place (a/0/8/1 228 RAPURASU, 11 map figures: Alto Mare, One to Four Island,
Route 40, Route 47; Arvind 2026-11-17: Lapras is the only Pokemon you ride, so it becomes Mooceon). The member holds 8
frames of 32x32: 0 up A, 5 up B, 6 down A, 7 down B, 2 left A, 1 left B, 3 right A, 4 right B (names .1-.4 play 0,5,0,5;
.5-.8 6,7,6,7; .9-.12 2,1,2,1; .13-.16 3,4,3,4), Lapras swimming with water rings round it.
Each frame here is Mooceon's follower frame for the same facing and step (columns up, down, left, right; rows step 1, 2),
its legs cut off below the waterline WL and lowered SINK pixels into the water, with Lapras's own water rings (its light
pixels below row 18) laid round it. One 16-colour palette; the member written in place.
python ferry_from_follower.py A081_IN A081_OUT FOLLOWER.png PREVIEW.png   env WL (26), SINK (2)"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from narc import unpack
import btx
IN, OUT, FOL, PREV = sys.argv[1:5]
E = lambda k, d: int(os.environ.get(k, d))
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[228]
img, n = btx.decode(d); assert n == 8, n
lap = np.asarray(img).reshape(8, 32, 32, 4)
f = np.asarray(Image.open(FOL).convert('RGBA')); assert f.shape[:2] == (64, 128)
cell = lambda c, r: f[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32].copy()
UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3
WHICH = {0: (UP, 0), 5: (UP, 1), 6: (DOWN, 0), 7: (DOWN, 1), 2: (LEFT, 0), 1: (LEFT, 1), 3: (RIGHT, 0), 4: (RIGHT, 1)}
WL, SINK = E('WL', 26), E('SINK', 2)
frames = []
for k in range(8):
    body = cell(*WHICH[k]); body[WL:] = 0
    body = np.vstack([np.zeros((SINK, 32, 4), np.uint8), body[:32 - SINK]])
    L = lap[k]; lum = L[..., :3].astype(float) @ np.array([0.3, 0.55, 0.15])
    c3 = L[..., :3].astype(int); sat = c3.max(-1) - c3.min(-1)
    ring = (L[..., 3] > 0) & (lum > 185) & ((sat < 40) | (c3[..., 2] > c3[..., 0] + 20)); ring[:18] = False   # white or light blue only
    outf = body.copy()
    front = ring.copy(); front[:WL + SINK - 1] = False                       # rings in front of her below the waterline
    outf[front] = L[front]
    behind = ring & (body[..., 3] == 0); outf[behind] = L[behind]
    frames.append(outf)
cols = []
for a in frames:
    for px in a[a[..., 3] > 0][:, :3]:
        t = tuple(int(v) // 8 * 8 for v in px)
        if t not in cols: cols.append(t)
if len(cols) > 15:                                              # merge the closest colours until 15 remain
    C = np.array(cols, float)
    while len(C) > 15:
        dd = ((C[:, None] - C[None]) ** 2).sum(-1); np.fill_diagonal(dd, 1e9); i, j = np.unravel_index(dd.argmin(), dd.shape)
        C[i] = (C[i] + C[j]) / 2; C = np.delete(C, j, 0)
    cols = [tuple(int(v) for v in c) for c in C]
pal = [(0, 0, 0)] + cols + [(0, 0, 0)] * (15 - len(cols)); Cn = np.array(cols, float)
idx = np.zeros((8 * 32, 32), np.uint8)
for k, a in enumerate(frames):
    m = a[..., 3] > 0
    idx[k * 32:(k + 1) * 32][m] = ((a[m][:, :3][:, None].astype(float) - Cn[None]) ** 2).sum(-1).argmin(1) + 1
new = btx.encode(d, idx, pal); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
chk, _ = btx.decode(new); a = np.asarray(chk)
order = [0, 5, 6, 7, 2, 1, 3, 4]
BG = np.array([40, 44, 60], np.uint8)
top = np.hstack([np.where(lap[k][..., 3:4] > 0, lap[k][..., :3], BG) for k in order])
bot = np.hstack([np.where(a[k * 32:(k + 1) * 32][..., 3:4] > 0, a[k * 32:(k + 1) * 32][..., :3], BG) for k in order])
z = np.vstack([top, np.full((3, top.shape[1], 3), 255, np.uint8), bot])
Image.fromarray(z).resize((z.shape[1] * 5, z.shape[0] * 5), Image.NEAREST).save(PREV); print('ok', OUT, 'colours', len(cols))
