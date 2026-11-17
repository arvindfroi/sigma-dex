"""Cel textures like the intro sprites: each baked texel is classed as fur / gold / red / white, lit into one of three
tones of that material's ramp (Sabertann's DS colours), cleaned with a majority filter, reduced by the most common colour,
and inner black lines drawn where two materials meet. The claw patch (bottom-left of texture 0) and a hand-drawn eye
(bottom-left of texture 1: white eye, black pupil, heavy brow) are painted in. python shade_tex3.py BASE"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
B = sys.argv[1]; SIZES = {0: (128, 128), 1: (64, 64), 2: (32, 64)}
PAL = np.array([(1, 1, 1), (26, 23, 30), (53, 50, 51), (89, 87, 85), (79, 25, 23), (143, 15, 25), (145, 92, 17), (205, 134, 0),
                (237, 199, 1), (176, 178, 187), (229, 228, 229), (247, 247, 247), (52, 32, 14), (92, 60, 28), (132, 94, 48)], float)
CLASS = {'fur': [1, 2, 3], 'gold': [6, 7, 8], 'red': [4, 5, 5], 'white': [9, 10, 11], 'wood': [4, 4, 5]}
CEN = {'fur': [(26, 23, 30), (53, 50, 51), (89, 87, 85), (1, 1, 1), (136, 122, 116)], 'gold': [(145, 92, 17), (205, 134, 0), (237, 199, 1), (236, 229, 147), (237, 221, 90)],
       'red': [(79, 25, 23), (143, 15, 25)], 'white': [(176, 178, 187), (229, 228, 229), (247, 247, 247)], 'wood': [(60, 36, 12), (108, 84, 36)]}
names = list(CLASS); LINE = 0
def to_lab(c):
    c = np.asarray(c, float) / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
cl_lab = [(k, to_lab(np.array(v, float))) for k, v in CEN.items()]
L = np.array([-0.35, -0.55, 0.75]); L /= np.linalg.norm(L)
def mode_down(a, h, w, n):
    H, W = a.shape; fy, fx = H // h, W // w
    blk = a[:h * fy, :w * fx].reshape(h, fy, w, fx).transpose(0, 2, 1, 3).reshape(h, w, -1)
    out = np.zeros((h, w), int)
    for y in range(h):
        for x in range(w): out[y, x] = np.bincount(blk[y, x], minlength=n).argmax()
    return out
def majority(a, n, it=2):
    for _ in range(it):
        cnt = np.stack([nd.uniform_filter((a == k).astype(float), 3) for k in range(n)]); a = cnt.argmax(0)
    return a
for g, (w, h) in SIZES.items():
    al = np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float)
    nm = np.asarray(Image.open(f'{B}_normal{g}.png').convert('RGB')).astype(float) / 255 * 2 - 1
    mx = al.max(-1); mn = al.min(-1); v = mx / 255; sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    r, gg, b = al[..., 0], al[..., 1], al[..., 2]
    hue = (np.degrees(np.arctan2(np.sqrt(3) * (gg - b), 2 * r - gg - b)) + 360) % 360
    cls = np.full(v.shape, names.index('fur'))
    cls[(sat < 0.28) & (v >= 0.55)] = names.index('white')
    col = (sat >= 0.28) & (v >= 0.18)
    cls[col & ((hue >= 330) | (hue < 22))] = names.index('red')
    cls[col & (hue >= 22) & (hue < 75)] = names.index('gold')
    cls[col & (hue >= 15) & (hue < 75) & (v < 0.5)] = names.index('wood')
    best = (None, cls)
    mat = majority(best[1], len(names), 2)
    ndot = np.clip((nm * L).sum(-1), 0, 1); band = np.digitize(ndot, [0.35, 0.75])
    tone = np.zeros(mat.shape, int)
    for ci, k in enumerate(names): tone[mat == ci] = np.array(CLASS[k])[band[mat == ci]]
    tone = majority(tone, 15, 1)
    t = mode_down(tone, h, w, 15); m = mode_down(mat, h, w, len(names))
    # inner lines on the darker side of a material border
    lum = PAL[:, 0] * 0.3 + PAL[:, 1] * 0.59 + PAL[:, 2] * 0.11; line = np.zeros(t.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        a1, b1 = m[:h - dy, :w - dx], m[dy:, dx:]; ta, tb = t[:h - dy, :w - dx], t[dy:, dx:]; diff = a1 != b1
        line[:h - dy, :w - dx] |= diff & (lum[ta] <= lum[tb]); line[dy:, dx:] |= diff & (lum[tb] < lum[ta])
    if g == 0:                                                 # claw patch: ivory, shaded toward the tip
        for y in range(h - 8, h):
            for x in range(0, 8): t[y, x] = 10 if (x + (h - 1 - y)) < 7 else 9
    if g == 1:                                                 # the eye, 16 x 12 at the bottom-left: white, black pupil, heavy brow
        E = ["................",                           # after the concept: a narrow white eye under a thick brow that
             "...........11111",                           # slopes down toward the nose (grumpy); a round black pupil with
             "......1111111111",                           # white on every side so it does not merge with the outline
             "..11111111111111",
             ".1111aaaaaaa111.",
             ".1aaaa111aaaaa1.",
             ".1aaa11111aaa1..",
             ".1aaaa111aaa1...",
             "..11111111111...",
             "................",
             "................",
             "................"]
        key = {'1': 0, 'b': 0, 'a': 10, '.': 2}
        for yy, row in enumerate(E):
            for xx, ch in enumerate(row): t[h - 12 + yy, xx] = key[ch]
    Image.fromarray(PAL[t].astype(np.uint8)).save(f'{B}_tex{g}.png'); np.save(f'{B}_tex{g}_idx.npy', t + 1)
np.save(f'{B}_tex_pal.npy', PAL); print('ok')
