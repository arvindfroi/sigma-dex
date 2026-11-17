"""Debug view of a mesh npz with coordinate grid. python h3d/splat.py MESH.npz OUT.png VIEW [x0,x1,y0,y1 crop] [labels.npy]
VIEW: front (look from -X: horiz=-Y.. i.e. creature's right on the left), side (from -Y: horiz=X, vert=Z), top (from +Z: horiz=X, vert=Y)"""
import sys, numpy as np, cv2
from PIL import Image, ImageDraw
d = np.load(sys.argv[1]); V = d['V'].astype(float); N = d['N'].astype(float); F = d['F']
view = sys.argv[3]
if view == 'front': h, v, dep, nd = V[:, 1], V[:, 2], V[:, 0], -N[:, 0]   # camera at -X looking +X; screen right = +Y
elif view == 'back': h, v, dep, nd = -V[:, 1], V[:, 2], -V[:, 0], N[:, 0]
elif view == 'side': h, v, dep, nd = V[:, 0], V[:, 2], V[:, 1], -N[:, 1]
elif view == 'top': h, v, dep, nd = V[:, 0], -V[:, 1], -V[:, 2], N[:, 2]
crop = [float(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] != '-' else [h.min(), h.max(), v.min(), v.max()]
lab = np.load(sys.argv[5]) if len(sys.argv) > 5 else None
S = 900; sc = S / max(crop[1] - crop[0], crop[3] - crop[2])
X = (h - crop[0]) * sc; Y = (crop[3] - v) * sc
img = np.full((S, S, 3), 40, np.uint8); zb = np.full((S, S), 1e9)
shade = np.clip(0.35 + 0.65 * nd, 0.15, 1)
COL = np.array([(200, 200, 200), (60, 60, 75), (35, 35, 45), (180, 30, 35), (235, 185, 50), (240, 240, 250), (90, 200, 255), (20, 20, 20)])
order = np.argsort(-dep)
for f in F[np.argsort(-dep[F].mean(1))]:
    pts = np.stack([X[f], Y[f]], 1).astype(np.int32)
    c = (COL[lab[f[0]]] if lab is not None else np.array([200, 190, 180])) * shade[f].mean()
    cv2.fillConvexPoly(img, pts, tuple(int(x) for x in c))
im = Image.fromarray(img); dr = ImageDraw.Draw(im)
step = 0.1
for g in np.arange(np.ceil(crop[0] / step) * step, crop[1], step):
    x = (g - crop[0]) * sc; dr.line([(x, 0), (x, S)], fill=(0, 120, 255) if abs(g / 0.5 - round(g / 0.5)) < 1e-6 else (0, 60, 120)); dr.text((x + 2, 2), f'{g:.1f}', fill=(120, 200, 255))
for g in np.arange(np.ceil(crop[2] / step) * step, crop[3], step):
    y = (crop[3] - g) * sc; dr.line([(0, y), (S, y)], fill=(255, 120, 0) if abs(g / 0.5 - round(g / 0.5)) < 1e-6 else (120, 60, 0)); dr.text((2, y + 2), f'{g:.1f}', fill=(255, 180, 80))
im.save(sys.argv[2])
