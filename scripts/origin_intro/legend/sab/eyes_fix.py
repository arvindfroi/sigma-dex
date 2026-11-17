"""Sabertann's field sprite (7 frames): take away the gold hat studs that read as yellow eyes and draw the concept's eyes
under the brim (white, black pupil, thick brow sloping down to the nose). The frames are one picture bobbed up/down; the
hat emblem ('a' gold at cols 31-32 above row 36) gives the offset.  python eyes_fix.py VARIANT -> eyes/f{n}_idx.npy, sheet"""
import sys, numpy as np
from PIL import Image
V = sys.argv[1] if len(sys.argv) > 1 else 'a'
STUDS = [(0, 27), (0, 36), (1, 26), (1, 37), (2, 30), (2, 33)]       # rows relative to the emblem row; mirrored pairs
# left eye, rows relative to the emblem row (face is 4-6 rows lower), col c mirrors to 63 - c. 1 black, 2 near-black, 15 white
EYES = {
 'a': {(4, 25): 1, (4, 26): 1, (4, 27): 1, (4, 28): 1, (5, 25): 15, (5, 26): 15, (5, 27): 1, (5, 28): 1, (5, 29): 1, (6, 25): 2, (6, 26): 2, (6, 27): 2},
 'b': {(4, 25): 1, (4, 26): 1, (4, 27): 1, (5, 25): 15, (5, 26): 15, (5, 27): 15, (5, 28): 1, (5, 29): 1, (6, 25): 2, (6, 26): 1, (6, 27): 15, (6, 28): 2},
 'c': {(4, 24): 1, (4, 25): 1, (4, 26): 1, (4, 27): 1, (5, 24): 15, (5, 25): 15, (5, 26): 1, (5, 27): 15, (5, 28): 1, (5, 29): 1, (6, 25): 2, (6, 26): 2, (6, 27): 2},
}[V]
pal = np.load('pxd_2_pal.npy'); P = np.vstack([[60, 70, 100], pal]).astype(np.uint8)
def show(a): return Image.fromarray(P[a]).resize((384, 384), Image.NEAREST)
out = []
for n in range(1, 8):
    a = np.load(f'f{n}_idx.npy').copy()
    ny = min(y for y in range(26, 38) if a[y, 31] == 10 and a[y, 32] == 10)
    for dy, c in STUDS:
        for cc in (c, 63 - c):
            if a[ny + dy, cc] == 14: a[ny + dy, cc] = 2
    for (dy, c), v in EYES.items(): a[ny + dy, c] = v; a[ny + dy, 63 - c] = v
    np.save(f'eyes/f{n}_idx.npy', a); out.append(a)
W = Image.new('RGB', (394 * 3, 384), 'white')
for i, a in enumerate([np.load('f1_idx.npy'), out[0], out[6]]): W.paste(show(a), (i * 394, 0))
W.save(f'eyes/sheet_{V}.png')
