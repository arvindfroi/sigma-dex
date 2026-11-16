"""Sabertann's field sprite with wind (Arvind 2026-11-17: on Sabertann "I expect that with the flags too" - the same life
as Gravriel's float). The 7 frames were one picture with a 0/1/2/1/0 px bob. Now, on the same approved picture
(eyes2 variant 5):
  - the mast is whole (it had a gap) with a small white flag with a gold mark at its top, under the tip so the bob
    never cuts it off; the flag flutters through three shapes (its free end lifts and drops)
  - the sails billow: a wave runs down their outer edges (left and right halves move out and back in by a pixel)
  - frame 6 (landed): the sails at rest, the flag hanging flat; frame 7 (the cry): the sails full out, the flag straight
python sab_wind.py BASE_idx.npy OUTDIR [OLD_SHEET]  -> f{1..7}_idx.npy, sheet.png, anim.gif (palette: pxd_2_pal.npy)"""
import sys, os
import numpy as np
from PIL import Image
BF, OD = sys.argv[1:3]; OLD = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
H = os.path.dirname(os.path.abspath(__file__))
base = np.load(BF).astype(int); PAL = np.load(os.path.join(H, 'pxd_2_pal.npy'))
WHITE, GREY, GOLD, MAST = 15, 11, 13, 2
MX = 31                                                         # the mast's columns 31-32
FLAGS = {'flat': ["bbbbb", "bfdfb", "bfffb", "bbbbb"], 'up': ["bbbbb", "bfdfb", "bffbb", "bbb.."], 'down': ["bbb..", "bfdbb", "bfffb", "bbbbb"]}
CODE = {'b': GREY, 'f': WHITE, 'd': GOLD}
def mast_and_flag(f, shape):
    g = f.copy()
    for y in range(2, 8):                                       # the whole mast from its tip down into the sail
        for x in (MX, MX + 1):
            if g[y, x] == 0 or y < 7: g[y, x] = MAST if y > 2 else 3
    for r, row in enumerate(FLAGS[shape]):
        for c, ch in enumerate(row):
            if ch != '.': g[3 + r, MX + 2 + c] = CODE[ch]
    return g
def billow(f, k, full=False, rest=False):
    """the sails' outer halves move out (d > 0) or in by d pixels per row; the side flaps (rows 15-27) twice as far"""
    g = f.copy(); Y0, Y1, XL, XR = 7, 30, 20, 44
    for y in range(Y0, Y1):
        amp = 2 if 15 <= y <= 27 else 1
        d = amp if full else 0 if rest else int(round(amp * np.sin(2 * np.pi * k / 5 - (y - Y0) * 0.28)))
        if d == 0: continue
        left, right = f[y, :XL].copy(), f[y, XR:].copy(); a = abs(d)
        if d > 0:
            g[y, :XL - a] = left[a:]; g[y, XL - a:XL] = left[-1]
            g[y, XR + a:] = right[:-a]; g[y, XR:XR + a] = right[0]
        else:
            g[y, a:XL] = left[:-a]; g[y, :a] = 0
            g[y, XR:64 - a] = right[a:]; g[y, 64 - a:] = 0
    return g
def bob(f, b): return np.vstack([f[b:], np.zeros((b, 64), int)]) if b else f
BOB = [0, 1, 2, 1, 0]; FL = ['up', 'flat', 'down', 'flat', 'up']
out = [bob(mast_and_flag(billow(base, k), FL[k]), BOB[k]) for k in range(5)]
out.append(mast_and_flag(billow(base, 0, rest=True), 'flat'))
out.append(mast_and_flag(billow(base, 0, full=True), 'flat'))
for k, f in enumerate(out): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(out): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if OLD:
    l = Image.open(OLD).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 5 + [5] * 5 + [6] * 6
gif = [Image.fromarray(np.where(out[k][..., None] > 0, P[out[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
