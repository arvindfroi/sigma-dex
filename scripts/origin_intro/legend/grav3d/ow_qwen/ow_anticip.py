"""Gravriel's overworld frame 6 as the anticipation before the cry (Arvind 2026-11-17: "I see they also have an
anticipation frame, so Sabertann and Gravriel must have it too"). In Origin's ritual Lugia holds frame 6 (wings folded
in front of it) for about half a second, shows frame 5 for a moment, then the cry (frame 7) for about a second. Gravriel's
frame 6 was a still float with beads hanging; now he gathers himself before the green ghost flash:
  - the head bows: the head and hat sink BOW px into the shoulders
  - the arms and claws pull in toward the body (ARMS times narrower about the middle), the claws curl up a pixel
  - the ragged coat draws in and tucks up: the hem narrows (HEM times) and its tips rise TUCK px
  - the ghost starts to show: a one-pixel inner rim of the dark ghost green (the cry's coat colour) on the coat below
    the head, so the flash that follows is foreshadowed
Frames 1-5 and 7 stay frames_v5's. Backward warp, out[y, x] = src[y + dy, x + dx], so nothing tears.
python ow_anticip.py V5DIR OUTDIR [LUGIA_SHEET]   -> f{1..7}_idx.npy, pal.npy, sheet.png, anim.gif
env: BOW (2), ARMS (0.88), HEM (0.85), TUCK (2), RIM (1)"""
import sys, os
import numpy as np
from PIL import Image
V5, OD = sys.argv[1:3]; LS = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
E = lambda k, d: float(os.environ.get(k, d))
PAL = np.load(os.path.join(V5, 'pal.npy')).astype(int)
fr = [np.load(os.path.join(V5, f'f{k}_idx.npy')).astype(int) for k in range(1, 8)]
src = fr[5]
BOW, ARMS, HEM, TUCK = E('BOW', 2), E('ARMS', 0.88), E('HEM', 0.85), E('TUCK', 2)
yy, xx = np.mgrid[0:64, 0:64].astype(float)
dy = -BOW * np.clip((30 - yy) / 12.0, 0, 1) * np.clip((14 - np.abs(xx - 31.5)) / 3.0, 0, 1)   # the head bows (rows < 18, the middle columns; the arms and blade keep their shape)
dy = dy + TUCK * np.clip((yy - 40) / 10.0, 0, 1)                # the hem tucks up (from row 40, fully by row 50)
cx = 31.5
arms = np.clip((yy - 20) / 4.0, 0, 1) * np.clip((44 - yy) / 4.0, 0, 1) * np.clip((np.abs(xx - cx) - 8) / 4.0, 0, 1)
hem = np.clip((yy - 40) / 6.0, 0, 1)
dx = (xx - cx) * ((1 / ARMS - 1) * arms + (1 / HEM - 1) * hem)  # sample farther out -> the content draws in
sy = np.clip(np.round(yy + dy), 0, 63).astype(int); sx = np.clip(np.round(xx + dx), 0, 63).astype(int)
g = src[sy, sx]; g[(yy + dy < 0) | (yy + dy > 63) | (xx + dx < 0) | (xx + dx > 63)] = 0
def shift_rows(f, y0, y1, x0, x1, d):                           # the claws curl (as in ow_float.py)
    h = f.copy(); box = f[y0:y1, x0:x1].copy(); h[y0:y1, x0:x1][box > 0] = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if box[y - y0, x - x0] and 0 <= y + d < 64: h[y + d, x] = box[y - y0, x - x0]
    return h
g = shift_rows(g, 29, 38, 44, 64, -1); g = shift_rows(g, 29, 37, 6, 22, -1)
if E('RIM', 1):
    lum = PAL[:15] @ np.array([0.3, 0.55, 0.15]); ID = int(np.argmin(np.where(lum > 0, lum, 999))) + 1
    IG = int(np.argmin(np.abs(PAL[:15] - np.array([24, 72, 56])).sum(1))) + 1        # the cry's dark ghost green
    s = g > 0; p = np.pad(s, 1); inner = s & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    inner[:20] = False; g[inner & (g == ID)] = IG
    print('rim: dark', ID, 'ghost', IG, PAL[IG - 1].tolist(), 'pixels', int((inner & (g == IG)).sum()))
fr[5] = g
for k, f in enumerate(fr): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), PAL)
P = np.vstack([[0, 0, 0], PAL[:15]]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(fr): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if LS:
    l = Image.open(LS).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 4 + [5] * 4 + [4] + [6] * 8                # Origin's order before the cry: 6 held, 5, 7
gif = [Image.fromarray(np.where(fr[k][..., None] > 0, P[fr[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
