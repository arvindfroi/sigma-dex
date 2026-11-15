"""Software preview of a textured low-poly (export_textured.py JSON + atlas), unlit like the DS (the light is in the
texture), texture reduced to TS px and NCOL colours first. python preview_tex.py BASE OUT.png [TS=128] [NCOL=15]"""
import sys, json, numpy as np
from PIL import Image
B, OUT = sys.argv[1:3]; TS = int(sys.argv[3]) if len(sys.argv) > 3 else 128; NC = int(sys.argv[4]) if len(sys.argv) > 4 else 15
tex = Image.open(B + '.png').convert('RGB').resize((TS, TS), Image.LANCZOS).quantize(NC, dither=0).convert('RGB')
tex.save(B + f'_{TS}_{NC}.png'); T = np.asarray(tex).astype(np.uint8)
D = json.load(open(B + '.json'))['polys']
tris = []
for p in D:
    for k in range(1, len(p['p']) - 1): tris.append(([p['p'][0], p['p'][k], p['p'][k + 1]], [p['uv'][0], p['uv'][k], p['uv'][k + 1]]))
P = np.array([t[0] for t in tris], float); U = np.array([t[1] for t in tris], float)
cen = P.reshape(-1, 3).mean(0); P -= cen; S = np.abs(P).max()
W = 256; out = Image.new('RGB', (W * 4, W), (52, 60, 84))
for vi, az in enumerate((0, 90, 200, 300)):
    a = np.radians(az); R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    el = np.radians(12); E = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    Q = P @ R.T @ E.T
    img = np.zeros((W, W, 3), np.uint8); img[:] = (52, 60, 84); zb = np.full((W, W), -1e9)
    xs = W / 2 + Q[..., 0] / S * W * 0.46; ys = W / 2 - Q[..., 2] / S * W * 0.46; zs = -Q[..., 1]
    for i in range(len(Q)):
        x0, x1 = int(max(0, xs[i].min())), int(min(W - 1, xs[i].max())) + 1; y0, y1 = int(max(0, ys[i].min())), int(min(W - 1, ys[i].max())) + 1
        if x1 <= x0 or y1 <= y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        (ax, bx, cx), (ay, by, cy) = xs[i], ys[i]; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        z = l1 * zs[i, 0] + l2 * zs[i, 1] + l3 * zs[i, 2]
        sub = zb[y0:y1, x0:x1]; m &= z > sub
        u = l1 * U[i, 0, 0] + l2 * U[i, 1, 0] + l3 * U[i, 2, 0]; v = l1 * U[i, 0, 1] + l2 * U[i, 1, 1] + l3 * U[i, 2, 1]
        tx = np.clip((u * TS).astype(int), 0, TS - 1); ty = np.clip(((1 - v) * TS).astype(int), 0, TS - 1)
        sub[m] = z[m]; img[y0:y1, x0:x1][m] = T[ty[m], tx[m]]
    out.paste(Image.fromarray(img), (vi * W, 0))
out.save(OUT); print('tris', len(tris))
