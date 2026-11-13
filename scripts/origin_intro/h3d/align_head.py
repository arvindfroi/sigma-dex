"""Move the head-only Hunyuan mesh into the body mesh's frame. Both were made from the same drawing, so their fitted
cameras (fit_cam.py) plus the crop offset give the exact place in the picture plane; the depth along the view is
the one that makes the head mirror-symmetric about the body's plane y = Y0.
python h3d/align_head.py BODY_CAM.json HEAD.npz HEAD_CAM.json OFFSET.json OUT.npz"""
import sys, json, os, numpy as np
from scipy.spatial import cKDTree
bc, hp, hc, offp, out = sys.argv[1:6]
Y0 = float(os.environ.get('Y0', -0.015))
def basis(c):
    az, el = np.radians(c['az']), np.radians(c['el'])
    dv = np.array([np.sin(az) * np.cos(el), -np.cos(az) * np.cos(el), np.sin(el)])
    rr = np.array([np.cos(az), np.sin(az), 0.0]); uu = np.cross(rr, -dv); uu /= np.linalg.norm(uu)
    return rr, uu, dv
B = json.load(open(bc)); Hc = json.load(open(hc)); off = json.load(open(offp))
rb, ub, db = basis(B); rh, uh, dh = basis(Hc)
d = dict(np.load(hp)); W_ = d['V'].astype(float); N_ = d['N'].astype(float)
a = W_ @ rh * Hc['scale'] + Hc['bx'] + off['dx']           # drawing pixels
b = -(W_ @ uh) * Hc['scale'] + Hc['by'] + off['dy']
dep = (W_ @ dh) * Hc['scale'] / B['scale']                  # body units, up to an offset
r = (a - B['bx']) / B['scale']; u = -(b - B['by']) / B['scale']
def place(D): return r[:, None] * rb + u[:, None] * ub + (dep + D)[:, None] * db
sub = np.random.default_rng(0).choice(len(W_), min(6000, len(W_)), replace=False)
best = None
for D in np.linspace(-0.6, 0.6, 121):
    P = place(D)[sub]
    M = P.copy(); M[:, 1] = 2 * Y0 - M[:, 1]
    e = np.median(cKDTree(P).query(M)[0])
    if best is None or e < best[0]: best = (e, D)
for D in np.linspace(best[1] - 0.01, best[1] + 0.01, 41):
    P = place(D)[sub]; M = P.copy(); M[:, 1] = 2 * Y0 - M[:, 1]
    e = np.median(cKDTree(P).query(M)[0])
    if e < best[0]: best = (e, D)
V = place(best[1])
R = np.stack([rb, ub, db], 1) @ np.stack([rh, uh, dh], 0)      # rotation head frame -> body frame
N = N_ @ R.T
print('mirror error (median) %.4f at D %.3f; scale head->body %.3f; head x %.3f..%.3f z %.3f..%.3f' % (
      best[0], best[1], Hc['scale'] / B['scale'], V[:, 0].min(), V[:, 0].max(), V[:, 2].min(), V[:, 2].max()))
d['V'] = V.astype(np.float32); d['N'] = N.astype(np.float32)
np.savez_compressed(out, **d)
