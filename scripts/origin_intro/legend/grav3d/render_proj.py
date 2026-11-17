"""Preview of a Gravriel mesh painted from the turnaround it was made from (title3d/grav/turn_11.png: front, his-left
side, back, his-right side), each face taking the view its normal points at. Per-pixel, z-buffered, front faces only.
python render_proj.py MESH.json OUT.png [AZ=0,35,-35,180] [SCALE]        MESH.json = list of polygons (lists of xyz)"""
import sys, os, json, numpy as np
from PIL import Image
from scipy import ndimage
MJ, OUT = sys.argv[1], sys.argv[2]
AZ = [float(a) for a in (sys.argv[3] if len(sys.argv) > 3 else '0,35,-35,180').split(',')]
TURN = os.path.expanduser('~/sigma-origin/title3d/grav/turn_11.png')
T = np.asarray(Image.open(TURN).convert('RGB')).astype(float)
m = T.min(-1) < 235; col = m.sum(0) > 3; RUNS = []; s0 = None
for x, c in enumerate(list(col) + [False]):
    if c and s0 is None: s0 = x
    if not c and s0 is not None:
        if x - s0 > 40: RUNS.append((s0, x - 1))
        s0 = None
assert len(RUNS) == 4, RUNS
VIEWS = []
for a, b in RUNS:
    v = T[:, a:b + 1]; mm = v.min(-1) < 235; ys, xs = np.nonzero(mm)
    core = ndimage.binary_erosion(mm, iterations=4); _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True)
    VIEWS.append((v[iy, ix], (xs.min(), xs.max(), ys.min(), ys.max())))
polys = [np.array(p) for p in json.load(open(MJ))]
A = np.vstack(polys); lo, hi = A.min(0), A.max(0)
def sample(P, vi):
    img, (x0, x1, y0, y1) = VIEWS[vi]
    if vi == 0: u = (P[..., 0] - lo[0]) / (hi[0] - lo[0])
    elif vi == 2: u = 1 - (P[..., 0] - lo[0]) / (hi[0] - lo[0])
    elif vi == 1: u = (P[..., 1] - lo[1]) / (hi[1] - lo[1])          # his left side (+x): front (-y) at image left
    else: u = 1 - (P[..., 1] - lo[1]) / (hi[1] - lo[1])
    w = (P[..., 2] - lo[2]) / (hi[2] - lo[2])
    cx = np.clip((x0 + u * (x1 - x0)).astype(int), 0, img.shape[1] - 1); cy = np.clip((y1 - w * (y1 - y0)).astype(int), 0, img.shape[0] - 1)
    return img[cy, cx]
def view_of(n):
    if abs(n[1]) >= abs(n[0]): return 0 if n[1] < 0 else 2
    return 1 if n[0] > 0 else 3
SC = float(sys.argv[4]) if len(sys.argv) > 4 else 70
W, H = int((hi[0] - lo[0]) * SC * 1.3) + 20, int((hi[2] - lo[2]) * SC) + 20
sheet = Image.new('RGB', (W * len(AZ), H), (200, 210, 205))
for k, az in enumerate(AZ):
    a = np.radians(az); R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]); c = (lo + hi) / 2
    img = np.full((H, W, 3), 200.0); zb = np.full((H, W), 1e9)
    for P in polys:
        n = np.cross(P[1] - P[0], P[2] - P[0]); nn = np.linalg.norm(n)
        if nn == 0: continue
        n = n / nn; Q = (P - c) @ R.T; nq = R @ n
        if nq[1] >= 0: continue
        vi = view_of(n); sh = 0.75 + 0.25 * max(0.0, -nq[1])
        for tri in ([0, 1, 2], [0, 2, 3])[: len(P) - 2]:
            q = Q[tri]; p3 = P[tri]; sx = q[:, 0] * SC + W / 2; sy = H / 2 - q[:, 2] * SC
            x0_, x1_ = int(max(0, sx.min())), int(min(W - 1, sx.max())) + 1; y0_, y1_ = int(max(0, sy.min())), int(min(H - 1, sy.max())) + 1
            if x0_ >= x1_ or y0_ >= y1_: continue
            yy, xx = np.mgrid[y0_:y1_, x0_:x1_]; d = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
            if abs(d) < 1e-9: continue
            w1 = ((xx - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (yy - sy[0])) / d; w2 = ((sx[1] - sx[0]) * (yy - sy[0]) - (xx - sx[0]) * (sy[1] - sy[0])) / d; w0 = 1 - w1 - w2
            msk = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3); dep = w0 * q[0, 1] + w1 * q[1, 1] + w2 * q[2, 1]
            msk &= dep < zb[y0_:y1_, x0_:x1_]
            if not msk.any(): continue
            P3 = w0[..., None] * p3[0] + w1[..., None] * p3[1] + w2[..., None] * p3[2]
            cc = sample(P3, vi) * sh
            sub = img[y0_:y1_, x0_:x1_]; sub[msk] = cc[msk]; zb[y0_:y1_, x0_:x1_][msk] = dep[msk]
    sheet.paste(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), (k * W, 0))
sheet.save(OUT); print('ok', OUT, len(polys), 'polys')
