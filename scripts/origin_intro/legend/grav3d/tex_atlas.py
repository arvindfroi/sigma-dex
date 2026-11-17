"""v7: Gravriel painted from the turnaround his 3D model was made from (title3d/grav/turn_11.png: front, his-left side,
back, his-right side), as real textures with UVs, the way the Pokémon film models carry their detail:
  - texture 0 (lugia_s, shape 0): the FRONT view, W0 x H0 (128x128), 256 colours (8 bpp)
  - texture 1 (lugia_foot, shape 1): back + both sides, W1 x H1 (256x128), 255 colours + the mist colour (index 255, a
    4x4 block in the bottom-right corner) for the film's mist layers
Each face takes the view its normal points at: a side view only when |nx| > SIDE_K * |ny| (the head's flanks took the
side view's profile face and showed a second face beside the real one otherwise), else front or back. The figure box in
each view is mapped to the whole model's box (cutlass included), which is how the intro model was built from the sheet.
python tex_atlas.py G.json OUT     -> OUT.json (polys with uv + g, tex, mist_uv), OUT_tex0.png/_idx.npy, OUT_tex1..."""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage
GJ, OUT = sys.argv[1:3]
E = lambda k, d: float(os.environ.get(k, d))
TURN = os.path.expanduser(os.environ.get('TURN', '~/sigma-origin/title3d/grav/turn_11.png'))
T = np.asarray(Image.open(TURN).convert('RGB')).astype(float)
m = T.min(-1) < 235; col = m.sum(0) > 3; RUNS = []; s0 = None
for x, c in enumerate(list(col) + [False]):
    if c and s0 is None: s0 = x
    if not c and s0 is not None:
        if x - s0 > 40: RUNS.append((s0, x - 1))
        s0 = None
assert len(RUNS) == 4, RUNS
VIEWS = []
for a, b in RUNS:                    # each figure cropped to its box; outline and background take the nearest inner colour
    v = T[:, a:b + 1]; mm = v.min(-1) < 235; ys, xs = np.nonzero(mm)
    core = ndimage.binary_erosion(mm, iterations=int(E('ERODE', 4))); _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)
    v = v[iy, ix]; VIEWS.append(v[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
W0, H0, W1, H1 = int(E('W0', 128)), int(E('H0', 128)), int(E('W1', 128)), int(E('H1', 64))   # 24 KB: 48 KB got overwritten in the film
GAIN = E('GAIN', 1.0)
def fit(img, h):                     # resize a view to height h, keeping its aspect
    w = max(1, int(round(img.shape[1] * h / img.shape[0])))
    return np.asarray(Image.fromarray(np.clip(img * GAIN, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(float)
# atlas 0: the front view, centred; atlas 1: back | his-left side | his-right side, left to right, mist block at the corner
A0 = np.zeros((H0, W0, 3)); f0 = fit(VIEWS[0], H0); assert f0.shape[1] <= W0, f0.shape
ox0 = (W0 - f0.shape[1]) // 2; A0[:, ox0:ox0 + f0.shape[1]] = f0; A0[:, :ox0] = f0[:, :1]; A0[:, ox0 + f0.shape[1]:] = f0[:, -1:]
RECT = {0: (0, ox0, f0.shape[1], H0)}
A1 = np.zeros((H1, W1, 3)); x = 0
for vi in (2, 1, 3):
    fv = fit(VIEWS[vi], H1); RECT[vi] = (1, x, fv.shape[1], H1); A1[:, x:x + fv.shape[1]] = fv; x += fv.shape[1] + 1
assert x - 1 <= W1 - 5, ('atlas 1 too narrow', x)
A1[:, x - 1:] = A1[:, x - 2:x - 1]
# the eyes are a few pixels at film size: the blue of the eyes (top of each view) is lifted to a pale glowing cyan
def eye_glow(a):
    if os.environ.get('EYE_GLOW', '1') != '1': return a
    h = a.shape[0]; top = a[: int(h * E('EYE_TOP', 0.3))]
    r, g, b = top[..., 0], top[..., 1], top[..., 2]; msk = (b > r + 25) & (b > 110) & (g > r)
    top[msk] = np.clip(top[msk] * 0.3 + np.array([170, 238, 255]) * 0.7, 0, 255); return a
A0 = eye_glow(A0); A1 = eye_glow(A1)
def quant(a, n):
    q = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:3 * n]).reshape(-1, 3); return np.asarray(q).astype(np.uint8), pal
BPP = int(E('BPP', 8)); NC = 256 if BPP == 8 else 16; FMT = 4 if BPP == 8 else 3
I0, P0 = quant(A0, NC); I1, P1 = quant(A1, NC - 1)
MIST = [int(v) for v in os.environ.get('MISTC', '176,214,190').split(',')]
P1 = np.vstack([P1, np.zeros((NC - 1 - len(P1), 3), int)]) if len(P1) < NC - 1 else P1
P1 = np.vstack([P1, [MIST]]); I1[H1 - 4:, W1 - 4:] = NC - 1
J = json.load(open(GJ)); polys = J['polys']
A = np.vstack([np.array(p['p']) for p in polys]); lo, hi = A.min(0), A.max(0)
SIDE_K = E('SIDE_K', 1.6)
def view_of(n):
    if abs(n[0]) > SIDE_K * abs(n[1]): return 1 if n[0] > 0 else 3
    return 0 if n[1] < 0 else 2
def uv_of(q, vi):
    if vi == 0: u = (q[0] - lo[0]) / (hi[0] - lo[0])
    elif vi == 2: u = 1 - (q[0] - lo[0]) / (hi[0] - lo[0])
    elif vi == 1: u = (q[1] - lo[1]) / (hi[1] - lo[1])
    else: u = 1 - (q[1] - lo[1]) / (hi[1] - lo[1])
    w = (q[2] - lo[2]) / (hi[2] - lo[2])
    g, rx, rw, rh = RECT[vi]; Wt, Ht = (W0, H0) if g == 0 else (W1, H1)
    px = rx + min(max(u, 0.0), 1.0) * (rw - 1) + 0.5; py = (1 - min(max(w, 0.0), 1.0)) * (rh - 1) + 0.5
    return g, [px / Wt, 1 - py / Ht]
out = []; cnt = [0, 0, 0, 0]
for p in polys:
    P = np.array(p['p']); n = np.cross(P[1] - P[0], P[2] - P[0])
    if len(P) == 4: n = n + np.cross(P[2] - P[0], P[3] - P[0])
    vi = view_of(n / (np.linalg.norm(n) + 1e-12)); cnt[vi] += 1
    uvs = [uv_of(q, vi) for q in P]; out.append(dict(p, uv=[u for _, u in uvs], g=uvs[0][0]))
J['polys'] = out
J['tex'] = {'0': [OUT + '_tex0.png', OUT + '_tex0_idx.npy', P0.tolist(), W0, H0, FMT], '1': [OUT + '_tex1.png', OUT + '_tex1_idx.npy', P1.tolist(), W1, H1, FMT]}
J['mist_uv'] = [(W1 - 2) / W1, 1 - (H1 - 2) / H1]
Image.fromarray(P0[I0].astype(np.uint8)).save(OUT + '_tex0.png'); np.save(OUT + '_tex0_idx.npy', I0)
Image.fromarray(P1[I1].astype(np.uint8)).save(OUT + '_tex1.png'); np.save(OUT + '_tex1_idx.npy', I1)
json.dump(J, open(OUT + '.json', 'w')); print('polys', len(out), 'front/left/back/right', cnt, 'atlas rects', RECT)
