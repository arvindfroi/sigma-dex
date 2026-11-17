"""Gravriel's overworld frames v7: frames 1-5 stay v5's float loop; frame 6 (the wind-up, wrapped in his coat) and frame 7
(the cry, thrown open) are Qwen's redraws of the cut-out puppets (grav_pose.py -> qwen_clean.py), chosen by eye.
Both come in the v2 palette and go to v5's palette (13 colours + the two ghost greens) by the nearest colour in Lab.
Frame 7 then flashes his ghost as v5's cry did: the darkest colour (the coat) goes to the dark ghost green, and a one-pixel
pale ghost-green glow rings the silhouette (not in holes inside him).
python grav_final.py V5DIR F6_idx.npy F7_idx.npy V2PAL.npy OUTDIR [LUGIA_SHEET]"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
V5, F6, F7, P2, OD = sys.argv[1:6]; LS = sys.argv[6] if len(sys.argv) > 6 else None; os.makedirs(OD, exist_ok=True)
PAL = np.load(os.path.join(V5, 'pal.npy')).astype(int); pal2 = np.load(P2).astype(float)
fr = [np.load(os.path.join(V5, f'f{k}_idx.npy')).astype(int) for k in range(1, 8)]
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
IG, IH = 14, 15                                                  # v5's ghost slots
L13 = lab(PAL[:13].astype(float)); M2 = np.array([0] + [int(((L13 - lab(c)) ** 2).sum(1).argmin()) + 1 for c in pal2])
to5 = lambda f: M2[np.clip(f, 0, len(pal2))]
f6, f7 = to5(np.load(F6).astype(int)), to5(np.load(F7).astype(int))
lum = PAL[:13] @ np.array([0.3, 0.55, 0.15]); ID = int(np.argmin(lum)) + 1
m = ndimage.binary_fill_holes(f7 > 0); f7[f7 == ID] = IG; f7[ndimage.binary_dilation(m) & ~m] = IH
fr[5], fr[6] = f6, f7
for k, f in enumerate(fr): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), PAL)
P = np.vstack([[0, 0, 0], PAL[:15]]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(fr): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if LS:
    l = Image.open(LS).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 4 + [5] * 4 + [4] + [6] * 8
gif = [Image.fromarray(np.where(fr[k][..., None] > 0, P[fr[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
