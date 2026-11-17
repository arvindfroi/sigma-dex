"""Textures and UVs for the part-by-part model (export_parts4.py), the way Ho-Oh's film model is textured: each polygon has
ONE clean colour from a small palette (the DS light does the shading), as tiny solid swatches; a drawn eye on the eye quads
(angry and focused: thick brow sloping down to the nose, white eye with shade, big round pupil); the sail picture reduced
into the cloth texture. Writes BASE.json in rig3d's format (p, uv, b, g, r, vb, n), BASE_tex{0,1,2}(_idx.npy), BASE_tex_pal.npy.
python build_tex4.py BASE SAILPNG FLAGPNG"""
import sys, json, numpy as np
from PIL import Image
from collections import Counter, defaultdict
B, SAIL, FLAG = sys.argv[1:4]
PAL = np.array([(12, 11, 16), (50, 48, 58), (84, 82, 94), (104, 18, 24), (168, 28, 36), (166, 104, 18), (230, 166, 28),
                (250, 214, 92), (226, 222, 204), (248, 248, 248), (168, 174, 188), (88, 56, 30), (136, 92, 48), (150, 58, 68),
                (40, 38, 46)], float)
NAMES = ['black', 'fur', 'fur_hi', 'red_dk', 'red', 'gold_dk', 'gold', 'gold_hi', 'ivory', 'white', 'grey', 'wood', 'wood_hi', 'pink', 'fur_dk']
FIXED = {'Claw': 'ivory', 'Tusk': 'ivory', 'Brow': 'black', 'EyeHole': 'black', 'SkNose': 'black', 'SkullMouth': 'black',
         'SkullHead': 'gold', 'SkullCheek': 'gold', 'SkullJaw': 'gold', 'SkullMaxilla': 'gold', 'HatEdge': 'gold', 'Rail': 'gold',
         'EyeRim': 'red_dk', 'Nose': 'gold'}
ALLOWED = {'Body': ['fur', 'gold', 'ivory', 'red_dk'], 'Hull': ['red', 'red_dk', 'black', 'gold', 'fur'],
           'Hat': ['black', 'gold'], 'Deck': ['red_dk', 'black'], 'Stern': ['gold', 'red', 'red_dk', 'black', 'fur'],
           'Mast': ['wood', 'wood_hi', 'black', 'gold', 'red_dk'], 'Sail': ['white', 'grey', 'gold'], 'Flag': ['white', 'black']}
def lab(c):
    c = np.asarray(c, float) / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
PL = lab(PAL)
def nearest(c, allowed):
    ids = [NAMES.index(a) for a in allowed]; d = np.linalg.norm(PL[ids] - lab(c), axis=1); return ids[int(d.argmin())]
P = json.load(open(B + '_parts.json'))['polys']
cls = []
for p in P:
    if p['tex'] in ('sail', 'flag', 'eye', 'emblem', 'mouth'): cls.append(None); continue
    if p['part'] in FIXED: cls.append(NAMES.index(FIXED[p['part']])); continue
    if p['part'] == 'Hull':                                   # concept: red shell on top, a black band round its edge, gold kept
        q = np.array(p['p']); fn = np.cross(q[1] - q[0], q[2] - q[0]); fn /= np.linalg.norm(fn) + 1e-9
        k_ = nearest(p['c'] if p['c'] else (60, 60, 60), ['gold', 'red', 'black'])
        cls.append(k_ if NAMES[k_] == 'gold' else NAMES.index('red' if abs(fn[2]) > 0.35 else 'black')); continue
    if p['part'] == 'Spike': cls.append(NAMES.index('gold')); continue
    if p['part'] == 'Shell': cls.append(nearest(p['c'], ['red', 'black', 'gold'])); continue
    cls.append(nearest(p['c'] if p['c'] else (60, 60, 60), ALLOWED.get(p['part'], NAMES)))
# clean up within each part: a polygon whose colour none of its neighbours share takes theirs
key = lambda q: tuple(np.round(q, 4)); edge = defaultdict(list)
for i, p in enumerate(P):
    pts = [key(q) for q in p['p']]
    for k in range(3): edge[(p['part'], frozenset((pts[k], pts[(k + 1) % 3])))].append(i)
nb = defaultdict(set)
for fs in edge.values():
    for i in fs: nb[i].update(j for j in fs if j != i)
for _ in range(3):
    new = list(cls)
    for i, c in enumerate(cls):
        if c is None or P[i]['part'] in FIXED: continue
        n = Counter(cls[j] for j in nb[i] if cls[j] is not None)
        if n and n[c] == 0 and n.most_common(1)[0][1] >= 2: new[i] = n.most_common(1)[0][0]
    cls = new
print('colours', {NAMES[k]: v for k, v in Counter(c for c in cls if c is not None).items()})
# textures
T0 = np.zeros((128, 128), int); T1 = np.zeros((64, 64), int); T2 = np.zeros((64, 32), int)
cell0 = {}; cell1 = {}
for k in range(15):                                          # texture 0: 4x4 cells of 32 px
    r, c = divmod(k, 4); T0[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = k; cell0[k] = ((c + 0.5) / 4, 1 - (r + 0.5) / 4)
for k in range(15):                                          # texture 1: rows 0-39 = 5 x 8 cells of 8 px (top), eye below
    r, c = divmod(k, 8); T1[r * 8:(r + 1) * 8, c * 8:(c + 1) * 8] = k; cell1[k] = ((c + 0.5) * 8 / 64, 1 - (r + 0.5) * 8 / 64)
EYE = ["........LLLLLLLLLL......",                            # 24 x 12, left eye; the right one is mirrored by its UVs
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
EK = {'.': 1, 'L': 2, 'K': 0, 'W': 9, 'G': 10}
E0y, E0x = 64 - 24, 0                                        # eye drawn 2x: 48 x 24 at the bottom-left of texture 1
for y, row in enumerate(EYE):
    for x, ch in enumerate(row): T1[E0y + 2 * y:E0y + 2 * y + 2, E0x + 2 * x:E0x + 2 * x + 2] = EK[ch]
EMB = ["GG....GGGG....GG",                                   # hat emblem 16 x 12: gold skull and crossbones on the black hat
       ".GG..GGGGGG..GG.",
       "..GG.GKGGKG.GG..",
       "...GGGKGGKGGG...",
       "....GGGGGGGG....",
       ".....GKGGKG.....",
       "....GGGGGGGG....",
       "...GGG.GG.GGG...",
       "..GG........GG..",
       ".GG..........GG.",
       "GG............GG",
       "................"]
for y, row in enumerate(EMB):
    for x, ch in enumerate(row): T1[40 + y, 48 + x] = {'G': NAMES.index('gold'), 'K': NAMES.index('fur_dk'), '.': NAMES.index('fur_dk')}[ch]
MOU = ["................",                                   # mouth 16 x 6 on fur (texture 1, cols 48-63, rows 52-57): a heavy
       "..K..........K..",                                   # line, corners pulled down (grumpy), a small notch under the nose
       "...KK......KK...",
       ".....KKKKKK.....",
       "........K.......",
       "................"]
for y, row in enumerate(MOU):
    for x, ch in enumerate(row): T1[52 + y, 48 + x] = NAMES.index('black') if ch == 'K' else NAMES.index('fur')
def quantize(img, allowed, size):
    a = np.asarray(Image.open(img).convert('RGB').resize(size, Image.LANCZOS)).astype(float)
    ids = [NAMES.index(x) for x in allowed]; L = lab(a); d = np.stack([np.linalg.norm(L - PL[i], axis=-1) for i in ids], -1)
    return np.array(ids)[d.argmin(-1)]
# cloth texture: the sail picture stored turned 90 degrees (rows = across the sail) so it is not squashed; the flag square below
SR = 42; T2[:, :] = NAMES.index('white')
_sail = Image.open(SAIL).convert('RGB').rotate(-90, expand=True); _sail.save('/tmp/_sail_rot.png')
T2[0:SR, :] = quantize('/tmp/_sail_rot.png', ['white', 'grey', 'gold', 'gold_dk', 'black'], (32, SR))
FS = 64 - SR; T2[SR:64, 0:FS] = quantize(FLAG, ['white', 'black', 'gold', 'gold_dk'], (FS, FS))
# planar UVs over each whole cloth piece (so the full skull always shows): in its own plane, up = Blender +Z
isl = defaultdict(list); _par = {}
def _f(x):
    while _par.setdefault(x, x) != x: x = _par[x]
    return x
for i, p in enumerate(P):
    if p['tex'] not in ('sail', 'flag'): continue
    ks = [key(q) for q in p['p']]
    for k in ks[1:]: _par[_f(k)] = _f(ks[0])
for i, p in enumerate(P):
    if p['tex'] in ('sail', 'flag'): isl[_f(key(p['p'][0]))].append(i)
CLOTHUV = {}
for root, ids in isl.items():
    Q = np.array([q for i in ids for q in P[i]['p']]); c = Q.mean(0); u_, s_, vt = np.linalg.svd(Q - c)
    nrm = vt[2]; up_ = np.array([0, 0, 1.0]) - nrm * nrm[2]; up_ /= np.linalg.norm(up_) + 1e-9; hz = np.cross(up_, nrm)
    ph, pv = (Q - c) @ hz, (Q - c) @ up_
    big = max(np.ptp(ph), np.ptp(pv)) > 0.25
    upright = abs(nrm[2]) < 0.6 and np.ptp(pv) > 0.4 and np.ptp(ph) > 0.3   # sails stand up (normal ~horizontal); flat yards / a lying spar are dropped
    for i in ids:
        out_uv = []
        for q in P[i]['p']:
            a_ = ((np.array(q) - c) @ hz - ph.min()) / max(np.ptp(ph), 1e-6); b_ = ((np.array(q) - c) @ up_ - pv.min()) / max(np.ptp(pv), 1e-6)
            if not big: out_uv.append([30.5 / 32, 1 - 62.5 / 64])                       # ropes and yards: plain white
            elif P[i]['tex'] == 'sail': out_uv.append([b_, 1 - (0.02 + 0.96 * a_) * SR / 64])   # turned picture: rows follow the width
            else: out_uv.append([(0.02 + 0.96 * a_) * FS / 32, 1 - (SR + (1 - (0.02 + 0.96 * b_)) * FS) / 64])
        CLOTHUV[i] = out_uv if (upright or P[i]['tex'] == 'flag') else None
out = []
for idx_, (p, c) in enumerate(zip(P, cls)):
    if p['tex'] == 'eye': uv = [[u * 48 / 64, v * 24 / 64] for u, v in p['uv']]    # bottom-left 48 x 24 (v=0 is the bottom)
    elif p['tex'] == 'mouth': uv = [[(48 + 0.3 + u * 15.4) / 64, 1 - (52 + 0.3 + (1 - v) * 5.4) / 64] for u, v in p['uv']]
    elif p['tex'] == 'emblem': uv = [[(48 + 0.3 + u * 15.4) / 64, 1 - (40 + 0.3 + (1 - v) * 11.4) / 64] for u, v in p['uv']]
    elif p['tex'] in ('sail', 'flag'):
        uv = CLOTHUV[idx_]
        if uv is None: continue
    else: uv = [list((cell1 if p['g'] == 1 else cell0)[c])] * 3
    out.append(dict(p=p['p'], n=p['n'], uv=uv, b=p['b'], g=p['g'], r=p['r'], vb=p['vb'], part=p['part']))
json.dump(dict(polys=out), open(B + '.json', 'w'))
for g, t in ((0, T0), (1, T1), (2, T2)):
    np.save(f'{B}_tex{g}_idx.npy', t + 1); Image.fromarray(PAL[t].astype(np.uint8)).save(f'{B}_tex{g}.png')
np.save(B + '_tex_pal.npy', PAL); print('ok', len(out))
