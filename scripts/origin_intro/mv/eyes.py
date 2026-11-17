"""Eye spots on the multi-view mesh, from where the eye is in the side view (side.png, seen from +X).
python mv/eyes.py MESH.npz FIT.json EXTRA.json [u,v]   (adds 'eyes': [{c, n}, mirrored] to EXTRA.json)"""
import sys, json, numpy as np
mp, fp, ep = sys.argv[1:4]
u, v = [float(t) for t in (sys.argv[4] if len(sys.argv) > 4 else '192,455').split(',')]
d = np.load(mp); V = d['V'].astype(float); N = d['N'].astype(float)
import os
VIEW = os.environ.get('EYE_VIEW', 'side')
f = json.load(open(fp))[VIEW]
if VIEW == 'side':
    yy = (u - f['cu']) / f['s']; zz = (f['cv'] - v) / f['s']
    m = (np.abs(V[:, 1] - yy) < 0.025) & (np.abs(V[:, 2] - zz) < 0.025) & (V[:, 0] > 0)
    k = np.where(m)[0][V[m, 0].argmax()]
else:                                   # front view: the eye on the face, the surface point nearest the viewer
    xx = (u - f['cu']) / f['s']; zz = (f['cv'] - v) / f['s']
    pa = np.load(os.environ['EYE_PARTS']) if os.environ.get('EYE_PARTS') else np.zeros(len(V), int)
    zz = float(os.environ.get('EYE_Z', zz))
    m = (np.abs(V[:, 0] - abs(xx)) < 0.02) & (np.abs(V[:, 2] - zz) < 0.02) & (V[:, 1] < -0.3) & (N[:, 1] < -0.5)
    k = np.where(m)[0][V[m, 1].argmin()]
near = np.linalg.norm(V - V[k], axis=1) < 0.03
n = N[near].mean(0); n /= np.linalg.norm(n)
c = V[k]
ex = json.load(open(ep))
ex['eyes'] = [dict(c=c.tolist(), n=n.tolist()), dict(c=[-c[0], c[1], c[2]], n=[-n[0], n[1], n[2]])]
json.dump(ex, open(ep, 'w'))
print('eye at', c.round(3), 'normal', n.round(2))
