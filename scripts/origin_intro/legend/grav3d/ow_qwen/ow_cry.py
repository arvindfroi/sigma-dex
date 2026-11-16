"""Gravriel's overworld frames v5: the cry turns green (Arvind on v4: "when the eyes open up more the nostrils get crazy
big ... you can rather make him a bit green like we've done"). Frames 1-6 stay v4's (ow_float.py). Frame 7, the cry:
  - the face is the base face again: beak closed, eyes as in the other frames (the open beak's dark/red/dark columns read
    as two huge nostrils)
  - the claws thrown open and the hem flared stay
  - he flashes his ghost, the green of the film's ghost and outline: his darkest colour (the coat, the bulk of him)
    goes half way to the film's ghost colour (0.35l+10, 1.05l+60, 0.8l+44), and a one-pixel glow of pale ghost green
    rings his silhouette (the film's green outline)
The palette is full (15), so the two closest colour pairs (Lab) are merged first, in every frame, to free two slots.
python ow_cry.py V4DIR BASE_idx.npy OUTDIR [LUGIA_SHEET]   -> f{1..7}_idx.npy, pal.npy, sheet.png, anim.gif
env: MIX (0.5: how far the coat goes to ghost green), HALO ('96,176,140'), MERGES (2)"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
V4, BF, OD = sys.argv[1:4]; LS = sys.argv[4] if len(sys.argv) > 4 else None; os.makedirs(OD, exist_ok=True)
PAL = np.load(os.path.join(V4, 'pal.npy')).astype(float)[:15]
fr = [np.load(os.path.join(V4, f'f{k}_idx.npy')).astype(int) for k in range(1, 8)]
base = np.load(BF).astype(int)
fr[6][8:17, 27:42] = base[8:17, 27:42]                         # the cry: the base face (beak closed, normal eyes)
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
KEEP = {13, 14, 15}                                            # white, glowing cyan, red shell: never merged
for _ in range(int(os.environ.get('MERGES', 2))):
    L = lab(PAL); best = None
    for i in range(len(PAL)):
        for j in range(i + 1, len(PAL)):
            if i + 1 in KEEP or j + 1 in KEEP: continue
            d = ((L[i] - L[j]) ** 2).sum()
            if best is None or d < best[0]: best = (d, i, j)
    _, i, j = best; n = lambda s: sum((f == s + 1).sum() for f in fr)
    keep, drop = (i, j) if n(i) >= n(j) else (j, i)
    print('merged', drop + 1, PAL[drop].astype(int).tolist(), 'into', keep + 1, PAL[keep].astype(int).tolist(), 'dE %.1f' % np.sqrt(best[0]))
    for f in fr: f[f == drop + 1] = keep + 1; f[f > drop + 1] -= 1
    PAL = np.delete(PAL, drop, 0); KEEP = {k - 1 if k > drop + 1 else k for k in KEEP}
lum = PAL @ np.array([0.3, 0.55, 0.15]); ID = int(np.argmin(lum)) + 1   # the darkest colour: the coat
ghost = lambda l: np.array([0.35 * l + 10, 1.05 * l + 60, 0.8 * l + 44])
MIX = float(os.environ.get('MIX', 0.5))
PAL = np.vstack([PAL, (1 - MIX) * PAL[ID - 1] + MIX * ghost(lum[ID - 1]), [float(v) for v in os.environ.get('HALO', '96,176,140').split(',')]])
IG, IH = len(PAL) - 1, len(PAL); assert len(PAL) <= 15, len(PAL)
c = fr[6]
for y in range(27, 39):                                         # the claw drop left a one-row gap through his right arm: close it
    for x in range(44, 64):
        if c[y, x] == 0 and c[y - 1, x] > 0 and c[y + 1, x] > 0: c[y, x] = c[y - 1, x]
m = ndimage.binary_fill_holes(c > 0)
c[c == ID] = IG                                                # the coat half way to ghost green
c[ndimage.binary_dilation(m) & ~m] = IH                        # the green glow around him (not in holes inside him)
PAL = (np.round(PAL / 8) * 8).clip(0, 248).astype(int)
print('palette', PAL.tolist())
for k, f in enumerate(fr): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), np.vstack([PAL, np.zeros((15 - len(PAL), 3), int)]))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(fr): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if LS:
    l = Image.open(LS).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 5 + [5] * 5 + [6] * 6
gif = [Image.fromarray(np.where(fr[k][..., None] > 0, P[fr[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
