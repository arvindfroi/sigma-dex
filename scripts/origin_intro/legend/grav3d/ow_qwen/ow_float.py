"""Gravriel's overworld frames v4 (Arvind on v3: "he should not flap his arms; just water dripping off him, the body and
the claws reacting to the movement, and he floats in the air"). Pixel animation on the approved v2 sprite, so the
creature stays exactly the same in every frame:
  - float: the whole figure rises and sinks (bob 0/1/2/1/0 px)
  - the ragged hem: a wave runs down the tatters (row shifts growing toward the tips), lagging the bob like cloth
  - the claws flex: the right hand's three fingers curl up a pixel and open again, the left hand's fingers out of phase
  - water drips: drops form at the tips of the tatters, the claws and the cutlass and fall (a bead, then a falling
    two-pixel drop: glowing cyan with a white glint), each tip on its own phase; drops only over empty sky
  - frame 6 (still): no wave, beads hanging at a few tips; frame 7 (the cry): the beak opens (dark mouth, red throat),
    the eyes flare, the claws spread, the hem flares out
python ow_float.py BASE_idx.npy PAL.npy OUTDIR [LUGIA_SHEET]   -> f{1..7}_idx.npy, pal.npy, sheet.png, anim.gif"""
import sys, os
import numpy as np
from PIL import Image
BF, PF, OD = sys.argv[1:4]; LS = sys.argv[4] if len(sys.argv) > 4 else None; os.makedirs(OD, exist_ok=True)
base = np.load(BF).astype(int); PAL = np.load(PF).astype(int)
WHITE, CYAN, RED, DARK = 13, 14, 15, 1                       # palette slots of the v2 palette (frames_v2/pal.npy)
rng = np.random.default_rng(int(os.environ.get('SEED', 4)))
def shift_rows(f, y0, y1, x0, x1, dy):                       # move a box up/down (claws curling)
    g = f.copy(); box = f[y0:y1, x0:x1].copy(); g[y0:y1, x0:x1][box > 0] = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if box[y - y0, x - x0] and 0 <= y + dy < 64: g[y + dy, x] = box[y - y0, x - x0]
    return g
def hem_wave(f, k, amp=1.6, flare=0):
    g = f.copy(); H0 = 46
    for y in range(H0, 64):
        a = min(amp, (y - (H0 - 2)) / 7.0)
        if flare:                                              # the cry: the left half out to the left, the right half to the right
            row = f[y].copy(); g[y] = 0; d = int(round(a * 0.8))
            for x in range(64):
                if row[x]:
                    nx = x - d if x < 32 else x + d
                    if 0 <= nx < 64: g[y, nx] = row[x]
            continue
        dx = int(round(a * np.sin(2 * np.pi * k / 5 - (y - H0) * 0.45)))
        g[y] = np.roll(f[y], dx) if dx else f[y]
        if dx > 0: g[y, :dx] = 0
        elif dx < 0: g[y, dx:] = 0
    return g
# drip sources: the tips of the tatters (lowest pixel of each strand), the claw tips, the left fingers, the cutlass tip
low = {x: max(np.nonzero(base[:, x])[0]) for x in range(64) if base[46:, x].any()}
tips = []
for x in sorted(low):
    if all(low[x] >= low.get(x + d, -1) for d in (-2, -1, 1, 2)) and low[x] > 48 and all(abs(x - t[0]) > 3 for t in tips): tips.append((x, low[x]))
claw = [(x, max(np.nonzero(base[28:37, x])[0]) + 28) for x in range(47, 63) if base[28:37, x].any()]
claw = [c for c in claw if all(c[1] >= cc[1] for cc in claw if abs(cc[0] - c[0]) <= 1)][::2][:3]
fing = [(x, max(np.nonzero(base[28:36, x])[0]) + 28) for x in range(10, 22) if base[28:36, x].any()]
fing = [c for c in fing if all(c[1] >= cc[1] for cc in fing if abs(cc[0] - c[0]) <= 1)][::3][:2]
blade = min((x, y) for y in range(20, 34) for x in range(0, 6) if base[y, x]) if base[20:34, 0:6].any() else None
SRC = tips + claw + fing + ([blade] if blade else [])
HAND = [False] * len(tips) + [True] * (len(SRC) - len(tips))          # hand/blade drops fall far and may pass in front of the coat
PH = rng.integers(0, 5, len(SRC)); FALL = [0, 1, 3, 6, 10]; FALL_H = [0, 2, 6, 11, 17]
print('drip sources', len(SRC), 'tatters', len(tips), 'claws', len(claw), 'fingers', len(fing), 'blade', blade)
def drips(f, k, srcs, ph, sparse=False):
    g = f.copy()
    for (x, y), p, hand in zip(srcs, ph, HAND):
        t = (k + p) % 5
        if sparse and t > 0: continue
        yy = y + 1 + (FALL_H if hand else FALL)[t]
        cells = [(yy, WHITE)] if t <= 1 else [(yy, CYAN), (yy + 1, WHITE)]
        for cy, c in cells:
            if 0 <= cy < 64 and (g[cy, x] == 0 or (hand and t >= 2)): g[cy, x] = c
        if not hand and not sparse:                             # water running down the strand before it drips
            gy = y - 9 + 2 * t
            if 0 <= gy < 64 and g[gy, x] > 0: g[gy, x] = WHITE if t % 2 else CYAN
    return g
def bob(f, b, dx=0):
    f = np.vstack([f[b:], np.zeros((b, 64), int)]) if b else f
    if dx: f = np.roll(f, dx, axis=1); f[:, :dx] = 0 if dx > 0 else f[:, :dx]; f[:, dx:] = 0 if dx < 0 else f[:, dx:]
    return f
BOB = [0, 1, 2, 1, 0]; SWAY = [int(v) for v in os.environ.get('SWAY', '0,1,1,0,-1').split(',')]   # a small loop: up/down and side to side
out = []
for k in range(5):
    f = hem_wave(base, k)
    if k in (1, 2): f = shift_rows(f, 30, 37, 47, 64, -1)           # right claw curls
    if k in (2, 3): f = shift_rows(f, 30, 36, 9, 22, -1)            # left fingers curl
    f = drips(f, k, SRC, PH)
    out.append(bob(f, BOB[k], SWAY[k]))
out.append(drips(base, 0, SRC, PH, sparse=True))                    # 6: still, beads hanging
f = hem_wave(base, 0, flare=1)                                      # 7: the cry
f = shift_rows(f, 28, 37, 47, 64, 1)                                 # claws thrown open (down/out)
for x0, x1 in ((30, 33), (36, 39)):                                  # the eyes flare: lids glow, eyes white
    f[10, x0:x1] = CYAN; f[11, x0:x1] = WHITE
f[13, 33:36] = [DARK, RED, DARK]; f[14, 33:36] = [DARK, RED, DARK]; f[15, 33:36] = [11, 12, 11]   # the beak wide open
out.append(f)
for k, f in enumerate(out): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f.astype(np.uint8))
np.save(os.path.join(OD, 'pal.npy'), PAL)
P = np.vstack([[0, 0, 0], PAL[:15]]); BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(out): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, P[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if LS:
    l = Image.open(LS).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png'))
seq = [0, 1, 2, 3, 4] * 5 + [5] * 5 + [6] * 6
gif = [Image.fromarray(np.where(out[k][..., None] > 0, P[out[k]], BG).astype(np.uint8)).resize((256, 256), Image.NEAREST) for k in seq]
gif[0].save(os.path.join(OD, 'anim.gif'), save_all=True, append_images=gif[1:], duration=133, loop=0); print('ok', OD)
