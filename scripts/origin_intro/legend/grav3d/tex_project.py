"""Gravriel looks like his artwork (Arvind 2026-11-16: "he doesn't look enough like the original artwork"): the film model
gets a painted texture projected from the turnaround the 3D model was made from (title3d/grav/turn_11.png: front, side,
back, side, in the model's own pose), instead of flat colour swatches.
  - texture 0 (lugia_s, 64x64): the front view (40 px wide) and the back view (24 px) side by side, 15 colours
  - texture 1 (lugia_foot, 32x32): the face (hat brim to the top of the beard) from the front view, sharper, 15 colours
Each view is fitted to the mesh's own projection (bounding box of the figure). A face takes the front view when it faces
the camera side (normal toward -y), else the back view; front faces in the head box take the face texture. The eye and
socket parts are left out (the painted face has the eyes). The cutlass keeps its steel swatch... from the painting too.
python tex_project.py G.json TURN.png OUT_PREFIX      -> OUT.json (polys with uv + g), OUT_tex0.png/_idx.npy, OUT_tex1..."""
import sys, os, json
import numpy as np
from PIL import Image
GJ, TURN, OUT = sys.argv[1:4]
E = lambda k, d: float(os.environ.get(k, d))
J = json.load(open(GJ)); polys = [p for p in J['polys'] if p['lab'] not in ('eye', 'socket')]
T = np.asarray(Image.open(TURN).convert('RGB')).astype(float); H_, W_ = T.shape[:2]
_m = T.min(-1) < E('WHITE', 235); _col = _m.sum(0) > 3; RUNS = []; _s = None      # the four figures, split at white columns
for _x, _c in enumerate(list(_col) + [False]):
    if _c and _s is None: _s = _x
    if not _c and _s is not None:
        if _x - _s > 40: RUNS.append((_s, _x - 1))
        _s = None
assert len(RUNS) == 4, RUNS
from scipy import ndimage
def view(k):
    a, b = RUNS[k]; v = T[:, a:b + 1].copy(); m = (v.min(-1) < E('WHITE', 235)); ys, xs = np.nonzero(m)
    core = ndimage.binary_erosion(m, iterations=int(E('ERODE', 5)))              # inside the outline (its edge pixels are light)
    _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)   # outline and background take the nearest inner colour
    v = v[iy, ix]; return v, (xs.min(), xs.max(), ys.min(), ys.max())
FRONT, FB = view(0); BACK, BB = view(2)
P = np.array([q for p in polys for q in p['p']]).reshape(-1, 3, 3)
xmin, xmax = P[..., 0].min(), P[..., 0].max(); zmin, zmax = P[..., 2].min(), P[..., 2].max()
def to_img(q, box, mirror):
    x0, x1, y0, y1 = box; u = (q[0] - xmin) / (xmax - xmin); u = 1 - u if mirror else u
    return x0 + u * (x1 - x0), y1 - (q[2] - zmin) / (zmax - zmin) * (y1 - y0)
# atlas 0: front (40 px) | back (24 px), 64 tall; the figure boxes squeezed into those strips
FW, BW, AH = int(E('FW', 40)), 64 - int(E('FW', 40)), 64
def strip(img, box, w, h):
    x0, x1, y0, y1 = box; crop = Image.fromarray(img[y0:y1 + 1, x0:x1 + 1].astype(np.uint8)); return np.asarray(crop.resize((w, h), Image.LANCZOS)).astype(float)
A0 = np.full((64, 64, 3), 255.0); A0[:, :FW] = strip(FRONT, FB, FW, AH); A0[:, FW:] = strip(BACK, BB, BW, AH)
# head box (face texture): top of the hat brim to the top of the beard, in mesh z, centred in x
HZ0, HZ1 = E('HEAD_Z0', 0.62), E('HEAD_Z1', 0.90)                 # fractions of the height (beak/eyes ~0.80)
HX = E('HEAD_HALF_X', 0.16)                                        # half width as a fraction of the figure width
cxm = (xmin + xmax) / 2
fz0, fz1 = zmin + HZ0 * (zmax - zmin), zmin + HZ1 * (zmax - zmin); fx0, fx1 = cxm - HX * (xmax - xmin), cxm + HX * (xmax - xmin)
ia, ib = to_img((fx0, 0, fz1), FB, False), to_img((fx1, 0, fz0), FB, False)
fc = Image.fromarray(FRONT[int(ia[1]):int(ib[1]) + 1, int(ia[0]):int(ib[0]) + 1].astype(np.uint8)).resize((32, 32), Image.LANCZOS)
A1 = np.asarray(fc).astype(float)
def quant(a, n=15, seed=1):
    # k-means over the figure colours (the background is already figure colour), saturated colours weighted up so the
    # greens, the sea-green skin and the blue eyes keep their own entries
    X = a.reshape(-1, 3); mx = X.max(1); mn = X.min(1); sat = (mx - mn) / np.maximum(mx, 1); w = 1 + 3 * sat
    rng = np.random.default_rng(seed); C = X[[rng.choice(len(X), p=w / w.sum())]]
    for _ in range(n - 1):
        d2 = ((X[:, None] - C[None]) ** 2).sum(-1).min(1); C = np.vstack([C, X[rng.choice(len(X), p=d2 * w / (d2 * w).sum())]])
    for _ in range(25):
        lab = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([np.average(X[lab == k], 0, weights=w[lab == k]) if (lab == k).any() else C[k] for k in range(n)])
    lab = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
    return lab.reshape(a.shape[:2]), np.clip(np.round(C), 0, 255).astype(int)
A1 = np.clip(A1 * E('FACE_GAIN', 1.25), 0, 255)                   # the painting is dark for the DS film light
I0, P0 = quant(A0); I1, P1 = quant(A1)
MIST = [int(x) for x in os.environ.get('MISTC', '176,214,190').split(',')]
I1[30:32, 30:32] = 15; P1 = np.vstack([P1, [MIST]])
out = []
for p, q3 in zip(polys, P):
    n = np.cross(q3[1] - q3[0], q3[2] - q3[0]); front = n[1] <= 0                          # faces toward -y = his front
    c = q3.mean(0); inhead = front and fz0 <= c[2] <= fz1 and fx0 <= c[0] <= fx1
    uv = []
    for q in q3:
        if inhead:
            u = (q[0] - fx0) / (fx1 - fx0); v = (q[2] - fz0) / (fz1 - fz0); uv.append([min(max(u, 0.01), 0.99), min(max(v, 0.01), 0.99)])
        else:
            x, y = to_img(q, FB if front else BB, not front)
            box = FB if front else BB; u = (x - box[0]) / (box[1] - box[0]); v = 1 - (y - box[2]) / (box[3] - box[2])
            u = u * FW / 64 if front else (FW + u * BW) / 64
            uv.append([min(max(u, 0.003), 0.997), min(max(v, 0.01), 0.99)])
    if os.environ.get('HYBRID', '1') == '1' and not inhead: out.append(dict(p, g=0)); continue   # body: colour swatches (clearer at DS size)
    out.append(dict(p, uv=uv, g=1 if inhead else 0))
J['polys'] = out; J['tex'] = {'0': [OUT + '_tex0.png', OUT + '_tex0_idx.npy', P0.tolist()], '1': [OUT + '_tex1.png', OUT + '_tex1_idx.npy', P1.tolist()]}
Image.fromarray(P0[I0].astype(np.uint8)).save(OUT + '_tex0.png'); np.save(OUT + '_tex0_idx.npy', I0)
Image.fromarray(P1[I1].astype(np.uint8)).save(OUT + '_tex1.png'); np.save(OUT + '_tex1_idx.npy', I1)
json.dump(J, open(OUT + '.json', 'w')); print('polys', len(out), 'face', sum(p['g'] for p in out), 'front box', FB, 'back box', BB)
