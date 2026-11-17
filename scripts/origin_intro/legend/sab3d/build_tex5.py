"""DS textures from the v5 bakes (export_parts5.py): every baked texel goes to the nearest of 15 palette colours (Lab), a
majority filter at the bake size, the most common colour per block down to the DS size, single stray texels swallowed;
then the drawn decals in texture 1's bottom strip: the eye (24 x 12: angry and focused, lit brow, shaded white, pupil ahead)
and the mouth (16 x 12, Arvind: no smile; a line from the nose down to where the mouth starts, the corners pulled down).
python build_tex5.py BASE        (reads BASE_albedo{g}.png; writes BASE_tex{g}.png, BASE_tex{g}_idx.npy, BASE_tex_pal.npy)"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
B = sys.argv[1]
PAL = np.array([(12, 11, 16), (56, 54, 66), (92, 90, 104), (104, 18, 24), (168, 28, 36), (166, 104, 18), (230, 166, 28),
                (250, 214, 92), (226, 222, 204), (248, 248, 248), (168, 174, 188), (88, 56, 30), (136, 92, 48), (60, 38, 20),
                (22, 21, 28)], float)
NAMES = ['black', 'fur', 'fur_hi', 'red_dk', 'red', 'gold_dk', 'gold', 'gold_hi', 'ivory', 'white', 'grey', 'wood', 'wood_hi', 'wood_dk', 'fur_dk']
SIZES = {0: (128, 128), 1: (64, 64), 2: (32, 64)}
def lab(c):
    c = np.asarray(c, float) / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
PL = lab(PAL)
def majority(a, n, size=3):
    cnt = np.stack([nd.uniform_filter((a == k).astype(float), size) for k in range(n)]); return cnt.argmax(0)
def mode_down(a, h, w, n):
    H, W = a.shape; fy, fx = H // h, W // w
    blk = a[:h * fy, :w * fx].reshape(h, fy, w, fx).transpose(0, 2, 1, 3).reshape(h, w, -1)
    return np.apply_along_axis(lambda v: np.bincount(v, minlength=n).argmax(), 2, blk)
def swallow(m, n):                                            # a texel whose colour none of its 8 neighbours share takes theirs
    out = m.copy(); H, W = m.shape
    for y in range(H):
        for x in range(W):
            nb = m[max(0, y - 1):y + 2, max(0, x - 1):x + 2].ravel(); k = m[y, x]
            if (nb == k).sum() <= 1: out[y, x] = np.bincount(nb, minlength=n).argmax()
    return out
EYE = ["........LLLLLLLLLL......",
       ".....LLLKKKKKKKKKKKL....",
       "...LLKKKKKKKKKKKKKKKK...",
       "..KKKKKKKKKKKKKKKKKKKK..",
       ".KKWWWWWWWWKKKKKKKKKKK..",
       ".KWWWWWWWWWWWWKKKKKKK...",
       ".KWWWWWWKKKKWWWWWKKK....",
       ".KWWWWWKKKKKKWWWWWK.....",
       ".KGWWWWKKKKKKWWWWGK.....",
       "..KGGGGGKKKKGGGGGK......",
       "...KKKKKKKKKKKKKK.......",
       "........................"]
MOUTH = ["......KKKK......",                                 # under the gold nose: the line down, then the mouth, corners down
         ".......KK.......",
         ".......KK.......",
         ".......KK.......",
         ".......KK.......",
         "......KKKK......",
         "....KKK..KKK....",
         "...KK......KK...",
         "..KK........KK..",
         "..K..........K..",
         "................",
         "................"]
for g, (w, h) in SIZES.items():
    al = np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float)
    L = lab(al); d = np.stack([np.linalg.norm(L - PL[k], axis=-1) for k in range(len(PAL))], -1); cls = d.argmin(-1)
    # the dark neutrals are split by brightness (the hat bakes ~28, the fur ~38, ink ~8): ink black, hat near-black, fur grey
    mx_ = al.max(-1); mn_ = al.min(-1); sat = (mx_ - mn_) / np.maximum(mx_, 1); Y = al @ np.array([0.3, 0.59, 0.11])
    dark = (sat < 0.3) & (mx_ < 70)
    cls[dark & (Y < 14)] = NAMES.index('black'); cls[dark & (Y >= 14) & (Y < 30)] = NAMES.index('fur_dk'); cls[dark & (Y >= 30)] = NAMES.index('fur')
    cls = majority(cls, len(PAL), 3)
    t = mode_down(cls, h, w, len(PAL)); t = swallow(t, len(PAL)); t = swallow(t, len(PAL))
    if g == 1:
        K = {'.': 1, 'L': 2, 'K': 0, 'W': 9, 'G': 10}
        for y, row in enumerate(EYE):
            for x, ch in enumerate(row): t[h - 12 + y, x] = K[ch]
        for y, row in enumerate(MOUTH):
            for x, ch in enumerate(row): t[h - 12 + y, 25 + x] = 0 if ch == 'K' else 1
    if g == 1:
        EMB = ["GG....GGGG....GG", ".GG..GGGGGG..GG.", "..GG.GKGGKG.GG..", "...GGGKGGKGGG...", "....GGGGGGGG....", ".....GKGGKG.....",
               "....GGGGGGGG....", "...GGG.GG.GGG...", "..GG........GG..", ".GG..........GG.", "GG............GG", "................"]
        t[h - 12:h - 8, 59:63] = NAMES.index('gold')                                              # hat trim patch
        for y, row in enumerate(EMB):
            for x, ch in enumerate(row): t[h - 12 + y, 42 + x] = {'G': 6, 'K': 0, '.': 0}[ch]          # gold on the black hat
    Image.fromarray(PAL[t].astype(np.uint8)).save(f'{B}_tex{g}.png'); np.save(f'{B}_tex{g}_idx.npy', t + 1)
np.save(f'{B}_tex_pal.npy', PAL); print('ok', B)
