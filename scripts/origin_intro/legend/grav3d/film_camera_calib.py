import numpy as np, json, sys
from PIL import Image
mk = [[float(v) for v in m.split(',')] for m in open('/tmp/g6dbg/markers.txt').read().strip().split(';')]
im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int)[:192]
obs = []
for m in mk:
    d = np.abs(im - np.array(m[3:])).max(-1); ys, xs = np.nonzero(d < 20)
    if len(xs) >= 4: obs.append((m[:3], [xs.mean(), ys.mean()], len(xs)))
for o in obs: print(o)
A = []
for X, (u, v), _ in obs:
    Xh = list(X) + [1]; A.append([0] * 4 + [-w for w in Xh] + [v * w for w in Xh]); A.append(Xh + [0] * 4 + [-u * w for w in Xh])
_, _, Vt = np.linalg.svd(np.array(A)); P = Vt[-1].reshape(3, 4)
err = [float(np.hypot(*(lambda p: (p[0] / p[2] - u, p[1] / p[2] - v))(P @ np.append(X, 1)))) for X, (u, v), _ in obs]
print('reprojection err px', np.round(err, 2))
_, _, Vt2 = np.linalg.svd(P); Cc = Vt2[-1]; Cc = Cc[:3] / Cc[3]; print('camera centre', Cc.round(1))
Q, Rr = np.linalg.qr(np.linalg.inv(P[:, :3])); Kc = np.linalg.inv(Rr); Rc = Q.T
s_ = np.diag(np.sign(np.diag(Kc))); Kc = Kc @ s_; Rc = s_ @ Rc
if np.linalg.det(Rc) < 0: Rc = -Rc
Kc = Kc / Kc[2, 2]; print('K', Kc.round(2)); print('R rows (cam x,y,z in world)', Rc.round(3))
json.dump(dict(P=P.tolist(), C=Cc.tolist(), K=Kc.tolist(), R=Rc.tolist()), open('/tmp/g6dbg/camera.json', 'w'))
