"""Sabertann's field sprite: the cry frame roars (Arvind 2026-11-17: "on the Sabertann overworld, make him roar or open
his mouth on the frame where that should happen"). Frame 7 is the cry (Ho-Oh opens its beak there, Lugia its mouth).
Frames 1-6 stay wind_v1's. In frame 7, between and around the two sabre tusks:
  - the jaw drops: the chin (rows 52-56 of the face) moves down DROP px
  - a wide open mouth under the nose: a black rim, dark red inside, a black throat at the top, a red tongue at the
    bottom, two small white lower fangs on the lower lip
  - the tusks stay in front of the opening, hanging from the upper jaw, one pixel longer (the face stretched)
A wide mouth shape on purpose: Gravriel's narrow open beak (dark/red/dark columns) read as two big nostrils.
python sab_roar.py WIND_DIR OUTDIR [OLD_SHEET]  -> f{1..7}_idx.npy, sheet.png, anim.gif (palette: pxd_2_pal.npy)
env: DROP (2)"""
import sys, os
import numpy as np
from PIL import Image
WD, OD = sys.argv[1:3]; OLD = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
H = os.path.dirname(os.path.abspath(__file__)); PAL = np.load(os.path.join(H, 'pxd_2_pal.npy'))
BLACK, DARKRED, RED, WHITE, GREY = 1, 4, 7, 15, 11
fr = [np.load(os.path.join(WD, f'f{k}_idx.npy')).astype(int) for k in range(1, 8)]
f = fr[6].copy(); o = fr[6].copy(); DROP = int(os.environ.get('DROP', 2))
TUSK = {(y, x): o[y, x] for y in range(46, 52) for x in (28, 29, 34, 35) if o[y, x] in (9, 11, 15)}   # the sabre teeth
X0, X1 = 22, 42                                              # the face's columns
for y in range(52, 64):                                      # the jaw drops: the cheeks stretch down, the chin moves down
    src = 51 if y < 52 + DROP else y - DROP
    f[y, X0:X1] = o[src, X0:X1] if src < 64 else 0
# the open mouth: an arch under the nose, wide between the tusks, narrowing to the lower lip
MOUTH = {44: (30, 33), 45: (29, 34), 46: (28, 35), 47: (27, 36), 48: (27, 36), 49: (27, 36), 50: (27, 36), 51: (27, 36), 52: (28, 35), 53: (29, 34)}
for y, (a, b) in MOUTH.items():
    for x in range(a, b + 1):
        top, bot = MOUTH.get(y - 1), MOUTH.get(y + 1)
        rim = x in (a, b) or top is None or bot is None or not (top[0] <= x <= top[1]) or not (bot[0] <= x <= bot[1])
        f[y, x] = BLACK if rim else DARKRED
for y in (45, 46, 47):                                        # the throat
    for x in (31, 32): f[y, x] = BLACK
for y, (a, b) in ((50, (31, 32)), (51, (30, 33)), (52, (30, 33))):   # the tongue
    for x in range(a, b + 1): f[y, x] = RED
for (y, x), v in TUSK.items(): f[y, x] = v                     # the tusks hang in front of the opening ...
f[52, 28] = f[52, 35] = WHITE; f[53, 28] = f[53, 35] = GREY    # ... a pixel longer, as the jaw dropped
for x in (30, 33): f[53, x] = WHITE                            # two small lower fangs on the lower lip
fr[6] = f
for k, g in enumerate(fr): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), g.astype(np.uint8))
P = np.vstack([[0, 0, 0], PAL]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, g in enumerate(fr): row[:, k * 68:k * 68 + 64] = np.where(g[..., None] > 0, P[g], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if OLD:
    l = Image.open(OLD).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 5 + [5] * 5 + [6] * 8
gif = [Image.fromarray(np.where(fr[k][..., None] > 0, P[fr[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
