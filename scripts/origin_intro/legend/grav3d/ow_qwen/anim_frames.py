"""Gravriel's 7 overworld frames from the posed sprites (anim_edit.py): one palette for all (each frame's pixels go to the
nearest colour of the v2 palette in Lab), each frame shifted so his eyes sit where they sit in the base (the head stays
put while the arms beat, like Lugia's body), a small lift on the down-stroke, and the eyes/shell checked per frame.
Frames (Lugia's order): 1 arms high, 2 half up, 3 level, 4 swept down, 5 coming back up, 6 landed, 7 the cry.
python anim_frames.py PALDIR OUTDIR up.png halfup.png level.png down.png halfdown.png landed.png cry.png
env: BOB ('0,0,1,2,1,0,0': rows lifted per frame), LUGIA (sheet to show above)"""
import sys, os
import numpy as np
from PIL import Image
PD, OD = sys.argv[1:3]; FR = sys.argv[3:10]; os.makedirs(OD, exist_ok=True)
PAL = np.load(os.path.join(PD, 'pal.npy')).astype(float); n = int((PAL.sum(1) > 0).sum()); PAL = PAL[:n]
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
PL = lab(PAL)
CY = int(np.argmin(((PL - lab([96, 224, 240])) ** 2).sum(1))) + 1                     # the glowing cyan
def to_idx(path):
    a = np.asarray(Image.open(path).convert('RGBA')).astype(float); m = a[..., 3] > 0
    idx = np.zeros((64, 64), int); L = lab(a[..., :3]); idx[m] = ((L[m][:, None] - PL[None]) ** 2).sum(-1).argmin(1) + 1; return idx
def eyes_at(idx):
    ys, xs = np.nonzero(idx[:32] == CY); return (xs.mean(), ys.mean()) if len(xs) >= 2 else None
frames = [to_idx(p) for p in FR]
base = frames[2]                                                                       # the level pose = the base sprite
BOB = [int(v) for v in os.environ.get('BOB', '0,0,1,2,1,0,0').split(',')]
def shift(f, dx, dy):
    g = np.zeros_like(f); ys, xs = np.nonzero(f); yy, xx = ys + dy, xs + dx; ok = (yy >= 0) & (yy < 64) & (xx >= 0) & (xx < 64)
    g[yy[ok], xx[ok]] = f[ys[ok], xs[ok]]; return g
# align by the head (hat, face, top of the beard: rows 0-20, the middle columns), not by the eyes (Qwen sometimes greys them)
H0, H1, X0, X1 = 0, 21, 22, 47; LB = lab(np.vstack([[0, 0, 0], PAL]))
def head_err(f, dx, dy):
    g = shift(f, dx, dy)[H0:H1, X0:X1]; b = base[H0:H1, X0:X1]; m = (g > 0) | (b > 0)
    return (((LB[g] - LB[b]) ** 2).sum(-1) * m).sum() / max(m.sum(), 1)
# the eyes of the base (glowing cyan, white outside) pasted into every pose; the cry flares them
EYE = (base > 0) & np.isin(base, [CY, int(np.argmax((PAL @ np.array([0.3, 0.55, 0.15])) * (np.arange(len(PAL)) != CY - 1))) + 1])
EYE[:8] = False; EYE[14:] = False
out = []
for k, f in enumerate(frames):
    if k == 6: dx, dy = 0, 0
    else: dx, dy = min(((dx_, dy_) for dx_ in range(-6, 7) for dy_ in range(-6, 7)), key=lambda t: head_err(f, *t))
    g = shift(f, dx, dy)
    if k < 6: g[EYE] = base[EYE]
    else:                                                                              # the cry: his eyes flare white with a cyan glow
        ys, xs = np.nonzero((g[:32] == CY) | np.isin(g[:32], [int(np.argmax(PAL @ np.array([0.3, 0.55, 0.15]))) + 1]))
        for y_, x_ in zip(ys, xs): g[y_, x_] = int(np.argmax(PAL @ np.array([0.3, 0.55, 0.15]))) + 1
        for y_, x_ in zip(ys, xs):
            for yy_, xx_ in ((y_ - 1, x_), (y_, x_ - 1), (y_, x_ + 1)):
                if 0 <= yy_ < 64 and 0 <= xx_ < 64 and g[yy_, xx_] > 0 and (yy_, xx_) not in set(zip(ys, xs)): g[yy_, xx_] = CY
    g = shift(g, 0, -BOB[k]); out.append(g); print('frame', k + 1, os.path.basename(FR[k]), 'shift', (dx, dy), 'bob', BOB[k])
for k, f in enumerate(out): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), np.vstack([PAL, np.zeros((15 - len(PAL), 3))]).astype(int))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(out): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if os.environ.get('LUGIA'):
    l = Image.open(os.environ['LUGIA']).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
# an animated preview: the beat cycle 1-5 a few times, then 6 and 7
seq = [0, 1, 2, 3, 4] * 4 + [5] * 4 + [6] * 6
gif = [Image.fromarray(np.where(out[k][..., None] > 0, P[out[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=120, loop=0); print('ok', OD)
