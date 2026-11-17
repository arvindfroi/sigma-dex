"""Quick software preview of the low-poly JSON: flat-shaded triangles, painter's order, 4 views.
python preview.py IN.json OUT.png"""
import sys, json, numpy as np
from PIL import Image, ImageDraw
D = json.load(open(sys.argv[1])); T = D['tris']
P = np.array([t['p'] for t in T]); C = np.array([t['c'] for t in T])
srgb = lambda c: np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)
C = np.clip(srgb(C), 0, 1)
cen = P.reshape(-1, 3).mean(0); P = P - cen; S = np.abs(P).max()
L = np.array([0.3, -0.5, 0.8]); L /= np.linalg.norm(L)
views = []
for az in (0, 90, 200, 300):
    a = np.radians(az); R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    el = np.radians(15); E = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    Q = P @ R.T @ E.T
    img = Image.new('RGB', (300, 300), (52, 60, 84)); dr = ImageDraw.Draw(img)
    n = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    shade = 0.45 + 0.55 * np.abs(n @ (E @ R @ L))
    order = np.argsort(Q[:, :, 1].mean(1))[::-1]
    for i in order:
        pts = [(150 + q[0] / S * 140, 150 - q[2] / S * 140) for q in Q[i]]
        col = tuple(int(255 * min(1, c * shade[i])) for c in C[i]); dr.polygon(pts, fill=col)
    views.append(img)
out = Image.new('RGB', (1200, 300)); [out.paste(v, (i * 300, 0)) for i, v in enumerate(views)]; out.save(sys.argv[2])
from collections import Counter; print(Counter(t['b'] for t in T).most_common())
