"""Clean, flat textures like Ho-Oh's (its film textures are near-solid colour fields): every baked texel is classed as
fur / gold / red / white / wood, the class map is cleaned hard (majority filter, then islands smaller than MIN texels at the
final size are swallowed by their surroundings), and each material gets ONE colour. No light bands and no ink lines in the
texture: the shading comes from the DS light on the model, as on Ho-Oh. Kept painted bits: the claw patch (texture 0,
bottom-left) and the eye (texture 1, bottom-left 16x12: angry and focused, lit brow ridge, shaded white, pupil ahead).
python clean_tex.py BASE OUT [MIN=4]      (reads BASE_albedo{g}.png, BASE.json; writes OUT_tex{g}*, OUT_tex_pal.npy, OUT.json)"""
import sys, json, shutil, numpy as np
from PIL import Image
from scipy import ndimage as nd
B, O = sys.argv[1], sys.argv[2]; MIN = int(sys.argv[3]) if len(sys.argv) > 3 else 4
SIZES = {0: (128, 128), 1: (64, 64), 2: (32, 64)}
PAL = np.array([(1, 1, 1), (26, 23, 30), (53, 50, 51), (89, 87, 85), (79, 25, 23), (143, 15, 25), (145, 92, 17), (205, 134, 0),
                (237, 199, 1), (176, 178, 187), (229, 228, 229), (247, 247, 247), (52, 32, 14), (92, 60, 28), (132, 94, 48)], float)
NAMES = ['fur', 'gold', 'red', 'white', 'wood']
FLAT = {'fur': 2, 'gold': 7, 'red': 5, 'white': 10, 'wood': 5}        # one palette colour per material (wood = the hull: red)
def majority(a, n, size=3, it=2):
    for _ in range(it):
        cnt = np.stack([nd.uniform_filter((a == k).astype(float), size) for k in range(n)]); a = cnt.argmax(0)
    return a
def mode_down(a, h, w, n):
    H, W = a.shape; fy, fx = H // h, W // w
    blk = a[:h * fy, :w * fx].reshape(h, fy, w, fx).transpose(0, 2, 1, 3).reshape(h, w, -1)
    return np.apply_along_axis(lambda v: np.bincount(v, minlength=n).argmax(), 2, blk)
def swallow_islands(m, n, minsize):
    for _ in range(3):
        changed = False
        for k in range(n):
            lab, cnt = nd.label(m == k)
            for i in range(1, cnt + 1):
                reg = lab == i
                if reg.sum() >= minsize: continue
                ring = nd.binary_dilation(reg) & ~reg
                if ring.any(): m[reg] = np.bincount(m[ring], minlength=n).argmax(); changed = True
        if not changed: break
    return m
EYE = ["................",            # angry and focused: lit brow ridge (3), hard brow down to the nose (0), white (10) with
       "..........3333..",            # a shaded lower part (9), pupil (0) looking ahead, dark lower lid (1)
       "......33330000..",
       "...333000000000.",
       ".33000000000000.",
       ".0000a9a0000000.",
       ".0aaaaaa000000..",
       ".0aaa00aaa000...",
       ".09aa00aaa9.0...",
       "..1999999911....",
       "...11111111.....",
       "................"]
KEY = {'0': 0, '1': 1, '3': 3, '9': 9, 'a': 10, '.': 2}
for g, (w, h) in SIZES.items():
    al = np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float)
    mx = al.max(-1); mn = al.min(-1); v = mx / 255; sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    r, gg, b = al[..., 0], al[..., 1], al[..., 2]
    hue = (np.degrees(np.arctan2(np.sqrt(3) * (gg - b), 2 * r - gg - b)) + 360) % 360
    cls = np.full(v.shape, 0)
    cls[(sat < 0.28) & (v >= 0.55)] = 3
    col = (sat >= 0.28) & (v >= 0.18)
    cls[col & ((hue >= 330) | (hue < 22))] = 2
    cls[col & (hue >= 22) & (hue < 75)] = 1
    cls[col & (hue >= 15) & (hue < 75) & (v < 0.5)] = 4
    cls = majority(cls, 5, 5, 2)
    m = mode_down(cls, h, w, 5)
    m = swallow_islands(m, 5, MIN)
    t = np.vectorize(lambda k: FLAT[NAMES[k]])(m)
    if g == 0:                                                 # claw patch: ivory, shaded toward the tip
        for y in range(h - 8, h):
            for x in range(0, 8): t[y, x] = 10 if (x + (h - 1 - y)) < 7 else 9
    if g == 1:
        for yy, row in enumerate(EYE):
            for xx, ch in enumerate(row): t[h - 12 + yy, xx] = KEY[ch]
    Image.fromarray(PAL[t].astype(np.uint8)).save(f'{O}_tex{g}.png'); np.save(f'{O}_tex{g}_idx.npy', t + 1)
np.save(f'{O}_tex_pal.npy', PAL); shutil.copy(B + '.json', O + '.json'); print('ok', O)
