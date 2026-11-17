"""Sabertann's cry frame as a whole-body roar made on the approved sprite itself (Arvind 2026-11-17 on roar v1, mouth only:
"I didn't like that roar. It should happen with the whole body when you roar"). Frame 7 of ROAR_DIR (roar_v1: jaw
dropped, mouth open between the sabres, sails full) is warped so the whole body takes part:
  - he rears: everything above the shoulders (sails, band, head) rises RISE px; the rise fades down the body, so the neck
    and chest stretch and the paws stay on the ground; the mast, flag and the sails' skull emblem stay put (the frame has
    no room above) and the head rises over the lower sails
  - the shoulders come up and out: the gold shoulder spikes rise a further pixel and move out SPREAD-1 px
  - the front legs brace wide: the paws move out SPREAD px to each side, claws spread
  - the sails are full, the flag flies straight (frame 7 of wind_v1); with SAILX they flare out wider, like Ho-Oh's wings
  - the brows come down toward the nose (an angry face); the eyes keep their shape
Backward warp with a smooth offset field, so nothing tears: out[y, x] = src[y + dy, x + dx].
python sab_roar_body.py ROAR_DIR OUTDIR [OLD_SHEET]  -> f{1..7}_idx.npy, sheet.png, anim.gif
env: RISE (3), SPREAD (2), SAILX (1.0: the sails flare wider), TOP (16: rows above it do not rise)"""
import sys, os
import numpy as np
from PIL import Image
RD, OD = sys.argv[1:3]; OLD = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
H = os.path.dirname(os.path.abspath(__file__)); PAL = np.load(os.path.join(H, 'pxd_2_pal.npy'))
fr = [np.load(os.path.join(RD, f'f{k}_idx.npy')).astype(int) for k in range(1, 8)]
src = fr[6]; RISE = int(os.environ.get('RISE', 3)); SPREAD = int(os.environ.get('SPREAD', 2))
yy, xx = np.mgrid[0:64, 0:64].astype(float)
# vertical: full rise above row 30, fading to 0 at row 60 (the paws stay down)
dy = np.clip((60 - yy) / 30.0, 0, 1) * RISE
TOP = int(os.environ.get('TOP', 16))
dy = dy * np.clip((yy - TOP) / 10.0, 0, 1)                           # mast, flag and emblem (rows < TOP) stay; the head rises over the lower sails
# horizontal: legs and shoulders go out; nothing above row 32 moves sideways
side = np.where(xx < 31.5, 1.0, -1.0)                                # sample from the inside -> content moves out
out_amt = np.clip((yy - 32) / 16.0, 0, 1) * SPREAD
centre = np.clip((np.abs(xx - 31.5) - 10) / 6.0, 0, 1)               # the head (|x-31.5| < 10) does not move sideways
dx = side * out_amt * centre
# the sails flare out like Ho-Oh's wings in its cry: above row SAILY the picture widens SAILX times about the mast
SAILX = float(os.environ.get('SAILX', 1.0)); SAILY = 30
flare = np.clip((SAILY + 2 - yy) / 4.0, 0, 1)
dx = dx - (xx - 31.5) * (1 - 1 / SAILX) * flare
# the shoulder spikes (gold, rows 33-40 at the sides) rise a further pixel
sh = (yy >= 31) & (yy <= 42) & (np.abs(xx - 31.5) > 13)
dy = dy + np.where(sh, 1.0, 0.0)
sy = np.clip(np.round(yy + dy), 0, 63).astype(int); sx = np.clip(np.round(xx + dx), 0, 63).astype(int)
g = src[sy, sx]
g[(yy + dy > 63)] = 0
# the brows come down toward the nose: find the beige brow pixels (6) above each eye and lower their inner ends
for half in (range(20, 31), range(33, 44)):
    cols = [x for x in half if (g[30:40, x] == 6).any()]
    if not cols: continue
    inner = cols[-3:] if half.start < 31 else cols[:3]
    for x in inner:
        ys = np.nonzero(g[30:40, x] == 6)[0]
        if len(ys):
            y = 30 + ys.max()
            if g[y + 1, x] not in (0, 15, 11): g[y + 1, x], g[y, x] = 6, 2
fr[6] = g
for k, f in enumerate(fr): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(fr): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh_ = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if OLD:
    l = Image.open(OLD).convert('RGB'); z = Image.new('RGB', (max(l.width, sh_.width), l.height + sh_.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh_, (0, l.height + 8)); sh_ = z
sh_.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 5 + [5] * 5 + [6] * 8
gif = [Image.fromarray(np.where(fr[k][..., None] > 0, P[fr[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
