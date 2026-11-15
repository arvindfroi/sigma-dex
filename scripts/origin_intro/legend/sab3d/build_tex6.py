"""Ho-Oh-style textures from the v5 bakes: Ho-Oh's film textures are tiny solid swatches, so whole areas share one UV and the
triangle strips stay long and cheap. Each polygon of the faithful low-poly gets the DOMINANT palette colour of the high-poly
bake inside it (the hull stripe, the gold leg rings, the deck, the skull's eyes come out where they are) and points at that
colour's swatch. Kept as pictures: the sail/flag texture (baked), and the drawn decals in texture 1 (eye, mouth, hat emblem,
gold brim patch). Claws ivory.  python build_tex6.py BASE   (reads BASE.json + BASE_albedo{g}.png from export_parts5)"""
import sys, json, numpy as np
from PIL import Image
sys.argv = [sys.argv[0], sys.argv[1]]
import importlib.util
B = sys.argv[1]
spec = importlib.util.spec_from_file_location('bt5', __file__.replace('build_tex6.py', 'build_tex5.py'))
src5 = open(__file__.replace('build_tex6.py', 'build_tex5.py')).read()
# reuse build_tex5's palette, classifier and decal drawings without running its main loop
head5 = src5[:src5.index('for g, (w, h) in SIZES.items():')]
ns = {}; exec(head5, ns)
PAL, NAMES, lab, PL, majority, mode_down, swallow, EYE, MOUTH = (ns[k] for k in ('PAL', 'NAMES', 'lab', 'PL', 'majority', 'mode_down', 'swallow', 'EYE', 'MOUTH'))
def classify(al):
    L = lab(al); d = np.stack([np.linalg.norm(L - PL[k], axis=-1) for k in range(len(PAL))], -1); cls = d.argmin(-1)
    mx_ = al.max(-1); mn_ = al.min(-1); sat = (mx_ - mn_) / np.maximum(mx_, 1); Y = al @ np.array([0.3, 0.59, 0.11]); dark = (sat < 0.3) & (mx_ < 70)
    cls[dark & (Y < 14)] = NAMES.index('black'); cls[dark & (Y >= 14) & (Y < 30)] = NAMES.index('fur_dk'); cls[dark & (Y >= 30)] = NAMES.index('fur')
    return cls
import os, shutil
if not os.path.exists(B + '_bake.json'): shutil.copy(B + '.json', B + '_bake.json')     # keep the baked UVs for re-runs
D = json.load(open(B + '_bake.json')); P = D['polys']
CLS = {}; ALB = {}
for g in (0, 1, 2):
    al = np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float); ALB[g] = al; CLS[g] = majority(classify(al), len(PAL), 3)
rng = np.random.default_rng(3); BARY = rng.dirichlet([1, 1, 1], 40)
def dominant(p):
    c = CLS[p['g']]; H_, W_ = c.shape; uv = np.array(p['uv'], float); votes = np.zeros(len(PAL))
    for k in range(1, len(uv) - 1):
        tri = uv[[0, k, k + 1]]
        for bc in BARY:
            u, v = bc @ tri; x = min(W_ - 1, max(0, int(u * W_))); y = min(H_ - 1, max(0, int((1 - v) * H_))); votes[c[y, x]] += 1
    return int(votes.argmax())
# swatch layouts: texture 0 = 4x4 cells of 32 px; texture 1 = 5 rows x 8 cells of 8 px at the top, decals in the bottom strip
T1 = np.ones((64, 64), int); cell = {0: {}, 1: {}}
for k in range(15):
    r, c = divmod(k, 8); T1[r * 8:(r + 1) * 8, c * 8:(c + 1) * 8] = k; cell[1][k] = ((c + 0.5) * 8 / 64, 1 - (r + 0.5) * 8 / 64)
K = {'.': 1, 'L': 2, 'K': 0, 'W': 9, 'G': 10}
for y, row in enumerate(EYE):
    for x, ch in enumerate(row): T1[52 + y, x] = K[ch]
for y, row in enumerate(MOUTH):
    for x, ch in enumerate(row): T1[52 + y, 25 + x] = 0 if ch == 'K' else 1
EMB = ["GG....GGGG....GG", ".GG..GGGGGG..GG.", "..GG.GKGGKG.GG..", "...GGGKGGKGGG...", "....GGGGGGGG....", ".....GKGGKG.....",
       "....GGGGGGGG....", "...GGG.GG.GGG...", "..GG........GG..", ".GG..........GG.", "GG............GG", "................"]
for y, row in enumerate(EMB):
    for x, ch in enumerate(row): T1[52 + y, 42 + x] = {'G': 6, 'K': 14, '.': 14}[ch]
T1[52:56, 59:63] = NAMES.index('gold')
from collections import Counter
used = Counter()
# texture 0 = the baked atlas (DS size) for the detailed parts; the flat parts point at solid swatches placed in its empty corners
BAKED = {'Hull', 'Deck', 'Stern', 'SkullHead', 'SkullCheek', 'SkullJaw', 'SkullMaxilla', 'SkullMouth', 'EyeRim', 'EyeHole', 'SkNose'}
LEGB = {'FL_up', 'FL_lo', 'FR_up', 'FR_lo', 'BL_up', 'BL_lo', 'BR_up', 'BR_lo'}
def baked(p): return p['g'] == 0 and (p['part'] in BAKED or (p['part'] == 'Body' and p['b'] in LEGB))
T0 = swallow(mode_down(CLS[0], 128, 128, len(PAL)), len(PAL)); T0[T0 == NAMES.index('fur_dk')] = NAMES.index('fur')
from PIL import ImageDraw
mask = Image.new('L', (128, 128), 0); dr = ImageDraw.Draw(mask)
for p in P:
    if baked(p): dr.polygon([(u * 128, (1 - v) * 128) for u, v in p['uv']], fill=255, outline=255)
M = np.array(mask) > 0; M = np.pad(M, 2)[0:132, 0:132]; M = np.array([[M[y:y + 5, x:x + 5].any() for x in range(128)] for y in range(128)])   # 2 px margin
free = [(y, x) for y in range(0, 128, 4) for x in range(0, 128, 4) if not M[y:y + 4, x:x + 4].any()]
need = list(range(len(PAL))); assert len(free) >= len(need), len(free)
for k, (y, x) in zip(need, free): T0[y:y + 4, x:x + 4] = k; cell[0][k] = ((x + 2) / 128, 1 - (y + 2) / 128)
print('swatch cells placed in empty texture-0 blocks:', len(free), 'free')
for p in P:
    if p['g'] == 2 or p['r'] >= 2 and p['r'] != 6 or baked(p): continue   # sail/flag, detailed parts keep their picture; decals their drawing
    if p['r'] == 6: k = NAMES.index('gold')
    elif p['r'] == 1: k = NAMES.index('ivory')
    else: k = dominant(p)
    if k == NAMES.index('fur_dk') and p['part'] != 'Hat': k = NAMES.index('fur')       # near-black is the hat's; fur stays fur
    used[NAMES[k]] += 1; p['uv'] = [list(cell[p['g']][k])] * len(p['p'])
print('colours', dict(used))
# the cloth texture: baked picture, quantised and reduced (as build_tex5)
al = ALB[2]; t2 = mode_down(CLS[2], 64, 32, len(PAL)); t2 = swallow(t2, len(PAL))
for g, t in ((0, T0), (1, T1), (2, t2)):   # T0: the atlas with the swatches
    Image.fromarray(PAL[t].astype(np.uint8)).save(f'{B}_tex{g}.png'); np.save(f'{B}_tex{g}_idx.npy', t + 1)
np.save(B + '_tex_pal.npy', PAL); json.dump(D, open(B + '.json', 'w')); print('ok', len(P))
