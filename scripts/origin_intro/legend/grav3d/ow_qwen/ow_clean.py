"""Gravriel's 7 overworld frames from Qwen's grid-drawn pixel sprite (ds_ow.py, seed 2), cleaned by hand-placed rules the
way Sabertann's field sprite was (legend/sab/eyes_fix2.py): Qwen left the eyes pale grey and the shoulder shell
grey-brown. The two closest colour pairs are merged to free two palette slots: glowing cyan (his eyes) and red-orange
(the shell on his left shoulder). Frames: 1-5 his float (bob 0/1/2/1/0 px, the ragged hem sways a pixel), 6 still,
7 the cry (lids lift, the eyes flare white with cyan glow).
python ow_clean.py SPRITE.png OUTDIR [SCENE_BG.png]  -> f{1..7}_idx.npy, pal.npy (15), sheet.png
env: EYES ('30,37,11': outer-left eye x, outer-right eye x, eye row), SHELL_BOX ('41,46,12,16': x0 x1 y0 y1 box), LIFT (40),
     EDGE ('' or 'r,g,b': silhouette edge colour), HEM (46: first row of the swaying hem)"""
import sys, os, json
import numpy as np
from PIL import Image
SP, OD = sys.argv[1:3]; BGF = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
E = lambda k, d: os.environ.get(k, d)
a = np.asarray(Image.open(SP).convert('RGBA')).astype(int)
cols = [tuple(c) for c in np.unique(a[a[..., 3] > 0][:, :3], axis=0)]; idx = np.zeros((64, 64), int)
for y in range(64):
    for x in range(64):
        if a[y, x, 3] > 0: idx[y, x] = cols.index(tuple(a[y, x, :3])) + 1
PAL = np.array(cols, float)
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def merge_closest():
    global PAL, idx
    L = lab(PAL); n = len(PAL); best = None
    for i in range(n):
        for j in range(i + 1, n):
            dd = ((L[i] - L[j]) ** 2).sum()
            if best is None or dd < best[0]: best = (dd, i, j)
    _, i, j = best; ci, cj = (idx == i + 1).sum(), (idx == j + 1).sum()
    keep, drop = (i, j) if ci >= cj else (j, i)
    idx[idx == drop + 1] = keep + 1; idx[idx > drop + 1] -= 1; PAL = np.delete(PAL, drop, 0)
    print('merged colour', drop + 1, 'into', keep + 1)
while len(PAL) > (12 if os.environ.get('EDGE') else 13): merge_closest()   # free slots: cyan, red (+ the edge colour)
CYAN, RED = np.array([96, 224, 240.0]), np.array([184, 84, 60.0])
PAL = np.vstack([PAL, CYAN, RED]); IC, IR = len(PAL) - 1, len(PAL)
# lift the darkest colours a little (he hovers over dark cave water)
LIFT = float(E('LIFT', 40))
for i in range(len(PAL) - 2):
    l_ = PAL[i] @ np.array([0.3, 0.55, 0.15])
    if 0 < l_ < LIFT: PAL[i] = PAL[i] * (LIFT / l_) ** 0.6
lum = PAL @ np.array([0.3, 0.55, 0.15]); IW = int(np.argmax(np.where(np.arange(len(PAL)) < len(PAL) - 2, lum, -1))) + 1   # the brightest (eye white)
ID = int(np.argmin(lum[:-2])) + 1                                                                                        # the darkest (lids)
# the shell: the grey-brown blob on his left shoulder (viewer's right) turns red-orange
sx0, sx1, sy0, sy1 = (int(v) for v in E('SHELL_BOX', '41,46,12,16').split(','))
box = idx[sy0:sy1, sx0:sx1]; pale = np.isin(box, [i + 1 for i in range(len(PAL) - 2) if lum[i] > 70]); box[pale] = IR
ex0, ex1, ey = (int(v) for v in E('EYES', '30,37,11').split(','))
def eyes(f, cry):
    for xs in ((ex0, ex0 + 1, ex0 + 2), (ex1 + 1, ex1, ex1 - 1)):   # outer -> inner
        for j, x in enumerate(xs):
            f[ey - 1, x] = IC if cry else ID                         # heavy lid (lifted, glowing, in the cry)
            f[ey, x] = IW if (cry or j == 0) else IC                 # white outside, glowing cyan toward the beak
    return f
base = idx.copy(); HEM = int(E('HEM', 46))
BOB = [0, 1, 2, 1, 0]; SWAY = [0, 1, 1, 0, -1]
frames = []
for k in range(7):
    f = base.copy()
    if k < 5:
        hem = f[HEM:].copy(); f[HEM:] = 0; f[HEM:] = np.roll(hem, SWAY[k], axis=1)
    f = eyes(f, k == 6)
    b = BOB[k] if k < 5 else 0
    if b: f = np.vstack([f[b:], np.zeros((b, 64), int)])
    frames.append(f)
EDGE = E('EDGE', '')
if EDGE:
    PAL = np.vstack([PAL, [float(v) for v in EDGE.split(',')]]); assert len(PAL) <= 15
    ie = len(PAL)
    for f in frames:
        s_ = f > 0; pd = np.pad(s_, 1); e_ = s_ & ~(pd[:-2, 1:-1] & pd[2:, 1:-1] & pd[1:-1, :-2] & pd[1:-1, 2:]); f[e_] = ie
assert len(PAL) <= 15, len(PAL)
PAL = (np.round(PAL / 8) * 8).clip(0, 248).astype(int)
for k, f in enumerate(frames): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), np.vstack([PAL, np.zeros((15 - len(PAL), 3), int)]))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(frames): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST).save(os.path.join(OD, 'sheet.png'))
print('ok', OD, 'colours', len(PAL), 'eye white', IW, 'cyan', IC, 'red', IR)
