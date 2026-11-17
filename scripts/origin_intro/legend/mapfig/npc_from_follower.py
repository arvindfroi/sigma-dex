"""A story map figure (a plain NPC sheet in a/0/8/1) made from one of our followers (2026-11-17, Arvind: "make 1 and 2":
the Route 36 odd tree USOKKY, member 186, becomes Sigmanian Sudowoodo). An NPC sheet holds 12 frames of 32x32 stacked
top to bottom in the order N0, W-A, W0, W-B, E0, E-A, E-B, N-A, N-B, S0, S-A, S-B (docs/TRAINERS_AND_ASSETS.md 1.3);
our follower sheet is 128x64, columns up, down, left, right and rows step 1, 2. Stand = step 1; step A = step 2; step B
= step 2 mirrored for north and south (the walk swings both ways), step 2 again for west and east. One 16-colour
palette (index 0 see-through); the member keeps its size and is written in place.
A 6-frame member is a swaying object (USOKKY: names .1-.12 play frames 0,1,0,2 and .13-.16 play 3,4,3,5): stand, lean left,
lean right from the front view's step 1, then the same from step 2.
python npc_from_follower.py A081_IN A081_OUT MEMBER FOLLOWER.png PREVIEW.png   (env CLEAN=k: k colours, lone pixels removed)"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from narc import unpack
from g2d import lz10_dec
import btx
IN, OUT, M, FOL, PREV = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[M]; assert d[:4] == b'BTX0', d[:4]
img, n = btx.decode(d); print('member', M, 'frames in texture', n)
f = np.asarray(Image.open(FOL).convert('RGBA')); assert f.shape[:2] == (64, 128), f.shape
K = int(os.environ.get('CLEAN', 0))
if K:                                                           # fewer colours and no lone pixels (the follower art is noisy)
    from sklearn.cluster import KMeans
    on = f[..., 3] > 0; cols_ = f[on][:, :3].astype(float)
    km = KMeans(K, n_init=8, random_state=0).fit(cols_); cen = np.round(km.cluster_centers_ / 8) * 8
    lab_ = np.zeros(f.shape[:2], int) - 1; lab_[on] = km.labels_
    for _ in range(2):                                          # a pixel unlike all 8 neighbours takes their commonest colour
        new_ = lab_.copy()
        for y in range(1, f.shape[0] - 1):
            for x in range(1, f.shape[1] - 1):
                if lab_[y, x] < 0: continue
                nb = lab_[y - 1:y + 2, x - 1:x + 2].ravel(); nb = np.delete(nb, 4); nb = nb[nb >= 0]
                if len(nb) >= 6 and (nb == lab_[y, x]).sum() == 0: new_[y, x] = np.bincount(nb).argmax()
        lab_ = new_
    f = f.copy(); f[on, :3] = cen[lab_[on]].astype(np.uint8)
cell = lambda c, r: f[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32]
UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3
flip = lambda a: a[:, ::-1]
order = [cell(UP, 0), cell(LEFT, 1), cell(LEFT, 0), cell(LEFT, 1), cell(RIGHT, 0), cell(RIGHT, 1), cell(RIGHT, 1),
         cell(UP, 1), flip(cell(UP, 1)), cell(DOWN, 0), cell(DOWN, 1), flip(cell(DOWN, 1))]
def lean(a, dx):                                                 # the top of the figure sways dx pixels (bottom stays put)
    out = np.zeros_like(a)
    for y in range(32):
        s_ = int(round(dx * max(0, (22 - y)) / 22.0))
        out[y] = np.roll(a[y], s_, axis=0)
        if s_ > 0: out[y, :s_] = 0
        elif s_ < 0: out[y, s_:] = 0
    return out
if n == 6:                                                      # a swaying object (USOKKY): stand, lean one way, lean the other, twice
    order = [cell(DOWN, 0), lean(cell(DOWN, 0), -2), lean(cell(DOWN, 0), 2), cell(DOWN, 1), lean(cell(DOWN, 1), -2), lean(cell(DOWN, 1), 2)]
else:
    assert n >= 12, n
    order = order + [cell(DOWN, 0)] * (n - 12)
cols = []
for a in order:
    for px in a[a[..., 3] > 0][:, :3]:
        t = tuple(int(v) for v in px)
        if t not in cols: cols.append(t)
assert len(cols) <= 15, len(cols)
pal = [(0, 0, 0)] + cols + [(0, 0, 0)] * (15 - len(cols))
frames = np.zeros((n * 32, 32), np.uint8)
for k, a in enumerate(order):
    for y in range(32):
        for x in range(32):
            if a[y, x, 3] > 0: frames[k * 32 + y, x] = pal.index(tuple(int(v) for v in a[y, x, :3]))
new = btx.encode(d, frames, pal)
assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
chk, n2 = btx.decode(new); a = np.asarray(chk)
strip = np.hstack([a[k * 32:(k + 1) * 32] for k in range(n2)])
bg = Image.new('RGBA', (strip.shape[1], 32), (40, 44, 60, 255)); bg.alpha_composite(Image.fromarray(strip)); bg.convert('RGB').resize((strip.shape[1] * 4, 128), Image.NEAREST).save(PREV)
print('written', OUT, 'colours', len(cols))
