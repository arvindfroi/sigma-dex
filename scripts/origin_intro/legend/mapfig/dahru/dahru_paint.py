"""Dahrugula painted over Origin's sleeping Snorlax (a/0/8/1 194 KABIGON; Arvind 2026-11-17: keep the original's
perspective, and it must look like Dahrugula). Every pixel of Snorlax keeps its place; the colours become Dahrugula's
(from its DS front sprite) and its own features go on top:
  - the body green all over (Snorlax's cream belly becomes Dahrugula's light/mid/dark greens, its teal underside the dark
    greens), the outline near-black, the grass patch as it is
  - two big round koala ears with peach insides on the head (the head lies on the right, its top toward the right)
  - the face: two dark X eyes one above the other toward the top of the head, a brown nose, the open mouth with a red
    tongue toward the belly
  - a red sash round the waist (across the body, since he lies along it), and one of its orange-brown barrels with dark hoops hugged on the belly
  - the feet's pads brown, the claws cream
python dahru_paint.py KABIGON_IDX.npy A081_IN A081_OUT PREVIEW.png"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from scipy import ndimage
from narc import unpack
import btx
KI, IN, OUT, PREV = sys.argv[1:5]
src = np.load(KI).astype(int)
E = lambda k, d: int(os.environ.get(k, d))
# new palette
# v7: the follower's bright green as the main colour (Dahrugula is green all over, not dark green with a light belly)
C = dict(OUTL=(3, 11, 14), G0=(0, 48, 16), G1=(0, 109, 43), G2=(43, 176, 89), G3=(81, 208, 115), GRASS=(88, 128, 80),
         CREAM=(249, 222, 194), PEACH=(253, 173, 115), RED=(240, 72, 47), NOSE=(96, 68, 47), B1=(202, 119, 64),
         B2=(251, 131, 25), B3=(169, 78, 36), BREW=(248, 200, 80), RED_D=(168, 40, 36))
names = list(C); I = {n: k + 1 for k, n in enumerate(names)}
pal = [(0, 0, 0)] + [C[n] for n in names] + [(0, 0, 0)] * (15 - len(names))
# Snorlax index -> ours (8 cream belly -> light green, 7 -> green, 9 -> dark green, a outline -> darkest, 3/4/5 body teal
# -> dark/mid/darkest green, b -> outline, 6 grass, 1 pink mouth -> red, 2 white claws -> cream)
MAP = {8: 'G3', 7: 'G2', 9: 'G1', 10: 'G0', 4: 'G2', 3: 'G1', 5: 'G0', 11: 'OUTL', 6: 'GRASS', 1: 'RED', 2: 'CREAM', 0: None}   # by luminance
g = np.zeros_like(src)
for k, n in MAP.items():
    if n: g[src == k] = I[n]
def put(pts, n):
    for x, y in pts:
        if 0 <= x < 64 and 0 <= y < 64: g[y, x] = I[n]
def disc(cx, cy, r):
    return [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2) for x in range(int(cx - r) - 1, int(cx + r) + 2) if (x - cx) ** 2 + (y - cy) ** 2 <= r * r]
# the ears on the head's top (the head lies with its top toward the right: Snorlax's closed eyes stand one above the other
# at x 48): big round green ears with peach insides, sticking out to the right at the head's upper and lower corner
for cx, cy, r in ((E('EAR1X', 54), E('EAR1Y', 40), 3.2), (E('EAR2X', 54), E('EAR2Y', 50), 3.2)):
    d_ = disc(cx, cy, r); ring = [p for p in disc(cx, cy, r + 1.2) if p not in d_]
    for x, y in ring:                                           # outlined against the grass and against the head
        if g[y, x] in (0, I['GRASS']) or src[y, x] in (3, 4, 5, 10, 11): g[y, x] = I['OUTL']
    put(d_, 'G2'); put(disc(cx + 0.3, cy, r - 1.4), 'PEACH')
# the face: Snorlax's cream face becomes the body's green (the belly stays the light green, so the head stands apart),
# a darker chin line toward the belly, two dark X eyes near the top of the head, the koala's big brown nose between and
# below them, a lolling red tongue, flushed cheeks
for y in range(40, 51):
    for x in range(42, 53):
        if src[y, x] in (1, 2, 7, 8, 9) or (src[y, x] == 11 and x < 51): g[y, x] = I['G2']
for y in range(41, 50):
    if src[y, 42] in (7, 8, 9, 1, 2): g[y, 42] = I['G1']
EX = E('EYEX', 49)
for ey in (42, 48):                                             # each X on a light patch, so it reads as an X, not a checker
    put([(EX + dx, ey + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)], 'G3')
    put([(EX - 1, ey - 1), (EX + 1, ey - 1), (EX, ey), (EX - 1, ey + 1), (EX + 1, ey + 1)], 'OUTL')
NX = E('NOSEX', 44)
put([(NX + 1, 43), (NX + 2, 43)] + [(x, y) for y in (44, 45, 46) for x in range(NX, NX + 4)] + [(NX + 1, 47), (NX + 2, 47)], 'NOSE')
put([(NX + 1, 44)], 'B3')                                               # its shine
put([(NX - 1, 45), (NX - 1, 46)], 'RED')                                # the tongue hanging out below the nose
put([(47, 40), (47, 50)], 'PEACH')                                      # flushed cheeks
# the red sash round the waist (Arvind on v3: "the line on the belly goes the wrong way"). He lies along x, feet left and
# head right, so a band round his waist runs from the belly's top edge down over his side, across the body. It sits on
# the lower belly (left of the belly's middle) and bows like the belly's own left contour, so it reads as going round
# the round body. It is lighter red on the belly and darker on his shaded side below it
XS = E('SASHX', 29)
for y in range(E('SASHY', 44), 60):                             # above this the keg on the belly covers it
    xl = XS + int(round(1.6 * ((y - 48.5) / 10.0) ** 2))
    for x in (xl, xl + 1):
        if src[y, x] in (3, 4, 5, 7, 8, 9) and g[y, x] not in (I['OUTL'],):
            g[y, x] = I['RED'] if src[y, x] in (7, 8, 9, 10) else I['RED_D']
# the barrel hugged on the belly: a small keg lying across, orange-brown with dark hoops and a lighter top
bx, by, bw, bh = E('BX', 28), E('BY', 38), 11, 7
keg = []
for y in range(by, by + bh):
    for x in range(bx, bx + bw):
        u = (x - bx) / (bw - 1); half = E('KEG_END', 16) / 10 + E('KEG_BULGE', 19) / 10 * (1 - (2 * u - 1) ** 2)    # a keg bulges in the middle
        if abs(y - (by + (bh - 1) / 2)) > half: continue
        keg.append((x, y))
ks = set(keg)
for x, y in keg:
    edge = any((x + dx, y + dy) not in ks for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    if edge: put([(x, y)], 'OUTL')
    elif x in (bx + 2, bx + bw - 3): put([(x, y)], 'B3')                 # the hoops near both ends
    elif y == by + 1: put([(x, y)], 'B2')                                # the light along the top of the staves
    elif y == by + bh - 2: put([(x, y)], 'B3')                           # the shade underneath
    else: put([(x, y)], 'B1')
for x in (bx + 4, bx + 6): put([(x, by + 3)], 'B3')                     # stave lines
put([(bx + 5, by + 2), (bx + 5, by + 4)], 'OUTL')                       # its bung
# the feet's pads: the claws stay cream, the soles brown where Snorlax's cream feet were
for y in range(40, 60):
    for x in range(22, 28):
        if src[y, x] in (7, 8, 9) and g[y, x] != I['RED']: g[y, x] = I['G2'] if src[y, x] == 8 else I['G1']
for y in range(52, 61):                                         # the lower foot's sole: a brown pad inside a green rim
    for x in range(22, 28):
        if src[y, x] == 8 and all(src[y + dy, x + dx] in (7, 8, 9) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))): g[y, x] = I['NOSE']
# a second barrel tipped over on the grass by his side, its brew spilled (the original's grass patch, right of the body)
if E('TIPPED', 1):
    # drawn in its own little layer (open end and spill to the right), then put by his feet on the LEFT, mirrored, so the
    # open end and the spill point away from him (in the game a person stands right of his head at both of his spots,
    # Karate King Jet on Route 12, and covered it on the right: in-game check 2026-11-17); TIPSIDE=right for the old place
    lay = {}
    body_ = [(x, y) for y in range(5) for x in range(7) if not ((x in (0, 6)) and (y in (0, 4)))]
    for x, y in body_:
        edge = any((x + dx, y + dy) not in body_ for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        lay[(x, y)] = 'OUTL' if edge else ('B3' if x in (2, 4) else ('B2' if y == 1 else 'B1'))
    for q in ((6, 1), (6, 2), (6, 3), (7, 2)): lay[q] = 'OUTL'                 # the open end, dark inside
    for q in ((7, 1), (7, 3), (8, 2)): lay[q] = 'B3'
    for q in ((8, 4), (9, 4), (9, 3), (10, 4), (10, 5), (8, 5), (9, 5), (11, 5), (7, 5), (9, 6), (10, 6)): lay.setdefault(q, 'BREW')
    left = os.environ.get('TIPSIDE', 'left') == 'left'
    ox, oy = (E('TX', 10), E('TY', 55)) if left else (E('TX', 48), E('TY', 54))
    for (x, y), n in lay.items():
        X_, Y_ = (ox + 11 - x if left else ox + x), oy + y
        if 0 <= X_ < 64 and 0 <= Y_ < 64 and (n != 'BREW' or g[Y_, X_] in (0, I['GRASS'])) and g[Y_, X_] in (0, I['GRASS'], I['OUTL']):
            g[Y_, X_] = I[n]
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[194]
new = btx.encode(d, g.astype(np.uint8), pal); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
P = np.array(pal, np.uint8); BG = np.array([40, 44, 60], np.uint8)
k = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kabigon_local.png')).convert('RGBA')
kb = Image.new('RGBA', k.size, (40, 44, 60, 255)); kb.alpha_composite(k)
z = np.hstack([np.asarray(kb.convert('RGB')), np.full((64, 4, 3), 255, np.uint8), np.where(g[..., None] > 0, P[g], BG)])
Image.fromarray(z.astype(np.uint8)).resize((z.shape[1] * 6, 384), Image.NEAREST).save(PREV); print('ok', OUT)
