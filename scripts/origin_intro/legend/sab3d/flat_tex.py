"""Ho-Oh-style colours for a low-poly: Ho-Oh's film model is clean flat colour parts (its textures are tiny near-solid
swatches), not a painted texture. Each polygon gets ONE material (fur / gold / red / white / wood / ivory) voted from the
baked albedo inside it, the regions are cleaned over neighbouring polygons, and each polygon gets one tone of that material
from its angle to a fixed light (two or three bands). Textures 0 and 1 become grids of solid swatches and the polygons'
UVs point at the centre of their swatch; the eye quads (texture 1, bottom-left), the claw patch (texture 0, bottom-left) and
the sails (texture 2) keep their painted pixels from shade_tex3.
python flat_tex.py BASE OUT        (reads BASE.json, BASE_albedo{g}.png, BASE_tex{g}_idx.npy; writes OUT.json, OUT_tex*)"""
import sys, json, numpy as np
from PIL import Image
from collections import Counter, defaultdict
B, O = sys.argv[1], sys.argv[2]
PAL = np.load(B + '_tex_pal.npy')                     # 15 colours, idx files store palette index + 1
# palette positions (see shade_tex3): 0 black 1-3 fur, 4-5 red, 6-8 gold, 9-11 white, 12-14 wood
RAMP = {'fur': [1, 2, 3], 'gold': [6, 7, 8], 'red': [4, 5, 5], 'white': [9, 10, 11], 'wood': [4, 4, 5]}   # the dark-gold bake is the hull: red (as in shade_tex3)
NAMES = list(RAMP)
L = np.array([-0.35, -0.55, 0.75]); L /= np.linalg.norm(L)   # Blender frame: forward -Y, up +Z, light from front-left-above
D = json.load(open(B + '.json')); P = D['polys']
AL = {g: np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float) for g in (0, 1, 2)}
IDX = {g: np.load(f'{B}_tex{g}_idx.npy') for g in (0, 1, 2)}

def classify(c):
    mx, mn = c.max(), c.min(); v = mx / 255; sat = (mx - mn) / max(mx, 1)
    r, g, b = c; hue = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) + 360) % 360
    if sat < 0.28 and v >= 0.55: return 'white'
    if sat >= 0.28 and v >= 0.18:
        if hue >= 330 or hue < 22: return 'red'
        if 15 <= hue < 75 and v < 0.5: return 'wood'
        if 22 <= hue < 75: return 'gold'
    return 'fur'

rng = np.random.default_rng(1)
BARY = rng.dirichlet([1, 1, 1], 24)
cls = []
for p in P:
    if p['r'] or p['g'] == 2: cls.append(None); continue          # claws, eyes and sails keep their pixels
    A = AL[p['g']]; h, w = A.shape[:2]; votes = Counter(); uv = np.array(p['uv'], float)
    for k in range(1, len(uv) - 1):
        tri = uv[[0, k, k + 1]]
        for bc in BARY:
            u, v = bc @ tri; x = min(w - 1, max(0, int(u * w))); y = min(h - 1, max(0, int((1 - v) * h)))
            votes[classify(A[y, x])] += 1
    cls.append(votes.most_common(1)[0][0])
# neighbours: polygons sharing an edge
key = lambda q: tuple(np.round(q, 4))
edge = defaultdict(list)
for i, p in enumerate(P):
    pts = [key(q) for q in p['p']]
    for k in range(len(pts)): edge[frozenset((pts[k], pts[(k + 1) % len(pts)]))].append(i)
nb = defaultdict(set)
for fs in edge.values():
    for i in fs:
        nb[i].update(j for j in fs if j != i)
for _ in range(3):                                                  # an island polygon takes its neighbours' material
    new = list(cls)
    for i, c in enumerate(cls):
        if c is None: continue
        n = Counter(cls[j] for j in nb[i] if cls[j] is not None)
        if n and n[c] == 0 and n.most_common(1)[0][1] >= 2: new[i] = n.most_common(1)[0][0]
    cls = new
print('materials', Counter(cls))
# tone from the face normal
def normal(p):
    q = np.array(p['p'], float); n = np.cross(q[1] - q[0], q[2] - q[0]); return n / (np.linalg.norm(n) + 1e-9)
tone = []
for p, c in zip(P, cls):
    if c is None: tone.append(None); continue
    d = abs(normal(p) @ L)                                          # both faces are drawn: use |n.L|
    band = 0 if d < 0.3 else (1 if d < 0.75 else 2)
    tone.append(RAMP[c][band] + 1)                                  # idx value = palette index + 1
# swatch textures
SIZES = {0: (128, 128), 1: (64, 64)}
out_idx = {2: IDX[2]}; cellof = {}
for g, (w, h) in SIZES.items():
    t = IDX[g].copy(); cs = w // 4                                  # 4 x 4 cells; cell (3, 0) keeps the claw patch / the eye
    cells = [(r, c) for r in range(4) for c in range(4) if (r, c) != (3, 0)]
    for k in range(15):
        r, c = cells[k]; t[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs] = k + 1
        cellof[(g, k + 1)] = ((c + 0.5) * cs / w, 1 - (r + 0.5) * cs / h)
    out_idx[g] = t
for p, tv in zip(P, tone):
    if tv is None: continue
    p['uv'] = [list(cellof[(p['g'], tv)])] * len(p['p'])
json.dump(D, open(O + '.json', 'w'))
for g, t in out_idx.items():
    np.save(f'{O}_tex{g}_idx.npy', t); Image.fromarray(PAL[t - 1].astype(np.uint8)).save(f'{O}_tex{g}.png')
np.save(O + '_tex_pal.npy', PAL); print('ok', O)
