"""Scene 5 v4, step 3 (replaces colour_ref.py): colour the Hunyuan mesh from its picture through the FITTED view.
python sc5/m3d/colour_fit.py MESH.npz REF.png OUT.npz
1. REF -> RGBA cutout; h3d/fit_cam.py finds the orthographic view whose silhouette matches it
2. z-buffer the faces from that view; vertices that face it take the picture's colour (5x5 median, so outlines stay out)
3. hidden vertices copy their mirror twin across the creature's middle plane (y = middle), the rest the nearest coloured one
4. classes: 0 pale (body, legs), 1 brown (head, tail, tuft), 2 crown (aurora), 3 dark (hooves, nose, eye); majority-smoothed"""
import sys, os, json, subprocess, numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage as nd
MESH, REF, OUT = sys.argv[1:4]; HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser('~/sigma-toolchain/venv312/bin/python')
img = np.asarray(Image.open(REF).convert('RGB')).astype(float); H, W = img.shape[:2]
fg = nd.binary_fill_holes(nd.binary_opening(img.min(-1) < 236, iterations=2))
rgba = np.dstack([img.astype(np.uint8), (fg * 255).astype(np.uint8)])
base = os.path.splitext(OUT)[0]; Image.fromarray(rgba).save(base + '_rgba.png')
subprocess.run([PY, os.path.join(HERE, '..', '..', 'h3d', 'fit_cam.py'), MESH, base + '_rgba.png', base], check=True)
cam = json.load(open(base + '_cam.json')); print('view', {k: round(v, 2) for k, v in cam.items() if k in ('az', 'el', 'iou')})
d = np.load(MESH); V = d['V'].astype(float); N = d['N'].astype(float); F = d['F']
az, el = np.radians(cam['az']), np.radians(cam['el'])
dv = np.array([np.sin(az) * np.cos(el), -np.cos(az) * np.cos(el), np.sin(el)])
rr = np.array([np.cos(az), np.sin(az), 0.0]); uu = np.cross(rr, -dv); uu /= np.linalg.norm(uu)
PX = V @ rr * cam['scale'] + cam['bx']; PYY = -(V @ uu) * cam['scale'] + cam['by']; DEP = -(V @ dv)
zb = np.full((H, W), -1, np.int32)
for fi in np.argsort(-DEP[F].mean(1)):
    f = F[fi]; cv2.fillConvexPoly(zb, np.stack([PX[f], PYY[f]], 1).round().astype(np.int32), int(fi))
vf = np.zeros(len(F), bool); vf[np.unique(zb[zb >= 0])] = True
vis = np.zeros(len(V), bool)
for k in range(3): vis[F[vf, k]] = True
ui = np.clip(PX.round().astype(int), 0, W - 1); vi = np.clip(PYY.round().astype(int), 0, H - 1)
ok = vis & (N @ dv > 0.15) & fg[vi, ui]
pad = np.pad(img, ((2, 2), (2, 2), (0, 0)), mode='edge')
col = np.full((len(V), 3), -1.0)
win = np.stack([pad[vi[ok] + dy, ui[ok] + dx] for dy in range(5) for dx in range(5)], 1)
col[ok] = np.median(win, 1)
Y0 = (V[:, 1].min() + V[:, 1].max()) / 2
src = np.where(ok)[0]; t = cKDTree(V[src]); M = V.copy(); M[:, 1] = 2 * Y0 - M[:, 1]
need = np.where(~ok)[0]; dist, j = t.query(M[need]); take = dist < 0.03
col[need[take]] = col[src[j[take]]]; have = col[:, 0] >= 0
t2 = cKDTree(V[have]); _, j2 = t2.query(V[~have]); col[~have] = col[have][j2]
r, g, b = col[:, 0], col[:, 1], col[:, 2]
cls = np.zeros(len(V), int)
cls[(r - b > 45) & (r > g + 10)] = 1
cls[((g > r + 25) & (g > 120)) | ((b - g > 55) & (r - g > 20))] = 2
cls[col.max(1) < 85] = 3
_, nb = cKDTree(V).query(V, 12)
for _ in range(3):
    cnt = np.stack([(cls[nb] == k).sum(1) for k in range(4)], 1); cls = cnt.argmax(1)
np.savez_compressed(OUT, V=V, F=F, N=N, col=col.astype(np.float32), cls=cls)
print('from picture', ok.sum(), 'mirrored', take.sum(), 'classes', np.bincount(cls, minlength=4))
