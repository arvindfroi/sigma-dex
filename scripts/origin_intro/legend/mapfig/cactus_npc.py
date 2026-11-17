"""Sigmanian Sudowoodo as Route 36's odd tree (a/0/8/1 186 USOKKY), drawn as clean 32x32 pixel art (2026-11-17: the
follower art read as a yellow blob next to Origin's crisp tree). Like the concept art (assets/concept-art/sigmanian-
sudowoodo 295/540): a cactus standing stiff as a saguaro, the trunk with two arms bent upward (the left lower, the right
higher), a small fork on top, rows of dark spines with light tips, two dark eye pits and a jagged mouth, two stubby feet.
The member is a swaying object: frames 0-2 = stand, lean left, lean right; 3-5 = the same with the arms a pixel
higher (names .1-.12 play 0,1,0,2; .13-.16 play 3,4,3,5). One 16-colour palette, the member written in place.
python cactus_npc.py A081_IN A081_OUT PREVIEW.png"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from scipy import ndimage
from narc import unpack
import btx
IN, OUT, PREV = sys.argv[1:4]
PAL = [(0, 0, 0), (24, 40, 16), (72, 104, 32), (152, 176, 56), (200, 208, 72), (240, 232, 120), (48, 72, 24),
       (248, 248, 216), (40, 32, 24), (112, 96, 56)] + [(0, 0, 0)] * 6
OUTL, SHADE, MID, BASE, HI, SPINE, TIP, MOUTH, SOIL = 1, 2, 3, 4, 5, 6, 7, 8, 9
def figure(arm_up=0):
    m = np.zeros((32, 32), bool)
    def rect(x0, y0, x1, y1): m[y0:y1 + 1, x0:x1 + 1] = True
    rect(13, 7, 18, 27)                                   # trunk
    rect(14, 5, 17, 6)                                    # rounded top
    rect(12, 6, 12, 7); rect(19, 6, 19, 7)                # the fork on top
    rect(11, 4, 12, 5); rect(19, 3, 20, 5)
    a = arm_up
    rect(8, 17 - a, 12, 19 - a); rect(8, 10 - a, 10, 18 - a); rect(9, 9 - a, 9, 9 - a)          # left arm, lower
    rect(19, 13 - a, 23, 15 - a); rect(21, 6 - a, 23, 14 - a); rect(22, 5 - a, 22, 5 - a)      # right arm, higher
    rect(12, 27, 14, 28); rect(17, 27, 19, 28)            # feet
    f = np.zeros((32, 32), int); f[m] = BASE
    # light from the left: the left column of each part is light, the right column shaded
    for y in range(32):
        xs = np.nonzero(m[y])[0]
        if len(xs) == 0: continue
        runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
        for r in runs:
            f[y, r[0]] = HI
            if len(r) > 2: f[y, r[-1]] = SHADE
            if len(r) > 4: f[y, r[-2]] = MID
    for y in range(32):                                   # the arms' undersides and the trunk's lower part darker
        for x in range(32):
            if m[y, x] and y + 1 < 32 and not m[y + 1, x] and f[y, x] == BASE: f[y, x] = MID
    # spines: dots on ribs, a light tip just outside the outline here and there
    for (x, y0, y1) in ((15, 8, 26), (17, 9, 26), (9, 11 - a, 17 - a), (22, 7 - a, 13 - a)):
        for y in range(y0, y1, 3):
            if m[y, x]: f[y, x] = SPINE
    # the face: eye pits, a jagged mouth
    f[11, 14] = OUTL; f[11, 17] = OUTL; f[12, 14] = SPINE; f[12, 17] = SPINE
    for x, y in ((14, 15), (15, 14), (16, 15), (17, 14)): f[y, x] = MOUTH
    # outline round the figure, then soil under the feet
    edge = ndimage.binary_dilation(m) & ~m
    f[edge] = OUTL
    for (x, y) in ((11, 3), (21, 2), (8, 8 - a), (23, 4 - a)):
        if 0 <= y < 32 and f[y, x] == OUTL: f[y, x] = TIP
    f[29, 11:21] = np.where(f[29, 11:21] == 0, SOIL, f[29, 11:21])
    return f
def lean(a, dx):
    out = np.zeros_like(a)
    for y in range(32):
        s_ = int(round(dx * max(0, 24 - y) / 24.0))
        out[y] = np.roll(a[y], s_)
        if s_ > 0: out[y, :s_] = 0
        elif s_ < 0: out[y, s_:] = 0
    return out
A, B = figure(0), figure(1)
frames = [A, lean(A, -2), lean(A, 2), B, lean(B, -2), lean(B, 2)]
raw = open(IN, 'rb').read(); from narc import unpack as _u; F = _u(raw); d = F[186]
img, n = btx.decode(d); assert n == 6, n
new = btx.encode(d, np.vstack(frames).astype(np.uint8), PAL); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
P = np.array(PAL, np.uint8); BG = np.array([40, 44, 60], np.uint8)
orig = np.asarray(img); ostrip = np.hstack([orig[k * 32:(k + 1) * 32] for k in range(6)])
o_rgb = np.where(ostrip[..., 3:4] > 0, ostrip[..., :3], BG)
n_rgb = np.hstack([np.where(fr[..., None] > 0, P[fr], BG) for fr in frames])
z = np.vstack([o_rgb, np.full((4, o_rgb.shape[1], 3), 255, np.uint8), n_rgb])
Image.fromarray(z.astype(np.uint8)).resize((z.shape[1] * 6, z.shape[0] * 6), Image.NEAREST).save(PREV); print('ok', OUT)
