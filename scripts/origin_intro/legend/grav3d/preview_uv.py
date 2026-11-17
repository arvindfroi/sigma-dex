"""Textured preview of a tex_atlas.py JSON: per-vertex skinning (two bones), per-pixel UV into the two atlases, z-buffer,
front faces only (the film culls back faces). python preview_uv.py G.json OUT.png [FRAMES=0,245] [AZ=0,30] [SCALE=40]"""
import sys, os, json, numpy as np
from PIL import Image
J = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FR = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '0,245').split(',')]
AZ = [float(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '0,30').split(',')]
SC = float(sys.argv[5]) if len(sys.argv) > 5 else 40
D = os.path.dirname(os.path.abspath(sys.argv[1]))
TEX = {int(k): np.asarray(Image.open(os.path.join(D, os.path.basename(v[0]))).convert('RGB')).astype(float) for k, v in J['tex'].items()}
B = {b: np.array(m) for b, m in J['bind'].items()}; Bi = {b: np.linalg.inv(m) for b, m in B.items()}
A = np.vstack([np.array(p['p']) for p in J['polys']]); lo, hi = A.min(0), A.max(0); c = (lo + hi) / 2
W, H = int((hi[0] - lo[0]) * SC * 1.4) + 20, int((hi[2] - lo[2]) * SC * 1.15) + 20
sheet = Image.new('RGB', (W * len(FR), H * len(AZ)), (190, 215, 205))
for fi, f in enumerate(FR):
    F = {b: np.array(m) for b, m in J['frames'][str(min(f, len(J['frames']) - 1))].items()}
    K = {b: F[b] @ Bi[b] for b in B}
    def sk(q, b, w):
        v = np.append(q, 1); a = (K[b] @ v)[:3]
        if w: a = a * (1 - w[1]) + (K[w[0]] @ v)[:3] * w[1]
        return a
    PP = [np.array([sk(np.array(q), b, w) for q, b, w in zip(p['p'], p['vb'], p.get('vw', [None] * len(p['vb'])))]) for p in J['polys']]
    for ai, az in enumerate(AZ):
        a = np.radians(az); R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        img = np.full((H, W, 3), 0.0); img[:] = (190, 215, 205); zb = np.full((H, W), 1e9)
        for p, P in zip(J['polys'], PP):
            Q = (P - c) @ R.T; n = np.cross(Q[1] - Q[0], Q[2] - Q[0])
            if n[1] >= 0: continue
            uv = np.array(p['uv']); T_ = TEX[p['g']]; th, tw = T_.shape[:2]
            for tri in ([0, 1, 2], [0, 2, 3])[: len(P) - 2]:
                q = Q[tri]; t = uv[tri]; sx = q[:, 0] * SC + W / 2; sy = H / 2 - q[:, 2] * SC
                x0, x1 = int(max(0, sx.min())), int(min(W - 1, sx.max())) + 1; y0, y1 = int(max(0, sy.min())), int(min(H - 1, sy.max())) + 1
                if x0 >= x1 or y0 >= y1: continue
                yy, xx = np.mgrid[y0:y1, x0:x1]; d = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
                if abs(d) < 1e-9: continue
                w1 = ((xx - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (yy - sy[0])) / d; w2 = ((sx[1] - sx[0]) * (yy - sy[0]) - (xx - sx[0]) * (sy[1] - sy[0])) / d; w0 = 1 - w1 - w2
                msk = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3); dep = w0 * q[0, 1] + w1 * q[1, 1] + w2 * q[2, 1]; msk &= dep < zb[y0:y1, x0:x1]
                if not msk.any(): continue
                u = w0 * t[0, 0] + w1 * t[1, 0] + w2 * t[2, 0]; v = w0 * t[0, 1] + w1 * t[1, 1] + w2 * t[2, 1]
                cc = T_[np.clip(((1 - v) * th).astype(int), 0, th - 1), np.clip((u * tw).astype(int), 0, tw - 1)]
                sub = img[y0:y1, x0:x1]; sub[msk] = cc[msk]; zb[y0:y1, x0:x1][msk] = dep[msk]
        sheet.paste(Image.fromarray(img.astype(np.uint8)), (fi * W, ai * H))
sheet.save(OUT); print('ok', OUT)
