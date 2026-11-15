"""Side-view sheet of a walk cycle on the textured low-poly (rigid per-vertex bones), to judge the animation by eye.
python walk_sheet.py BASE bones.json OUT.png [FRAMES=1..16] [AZ=90]"""
import sys, json, numpy as np
from PIL import Image
B, BJ, OUT = sys.argv[1:4]; FR = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else ','.join(str(i) for i in range(1, 17))).split(',')]
AZ = float(sys.argv[5]) if len(sys.argv) > 5 else 90
TX = {g: np.asarray(Image.open(f'{B}_tex{g}.png').convert('RGB')) for g in (0, 1, 2)}
J = json.load(open(BJ)); MERGE = {'jaw': 'head', 'flag': 'mast', 'stern': 'spine', 'root': 'spine'}
rest = {k: np.array(v) for k, v in J['rest'].items()}
D = json.load(open(B + '.json'))['polys']
LT = np.array([-0.35, -0.55, 0.75]); LT /= np.linalg.norm(LT); W = int(__import__("os").environ.get("WS", "220"))
allP = np.array([q for p in D for q in p['p']]); cen0 = (allP.max(0) + allP.min(0)) / 2; S = np.abs(allP - cen0).max() * 1.05
a = np.radians(AZ); Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
sheet = Image.new('RGB', (W * 8, W * ((len(FR) + 7) // 8)), (52, 60, 84))
for k, fr in enumerate(FR):
    F = {b: np.array(m) for b, m in J['frames'][str(fr)].items()}
    def pose(q, b):
        b = MERGE.get(b, b); return (F[b] @ np.linalg.inv(rest[b]) @ np.append(q, 1))[:3]
    tris = []; SPLIT = __import__('os').environ.get('SPLIT', '1') == '1'
    for p in D:
        for i in range(1, len(p['p']) - 1):
            idx = (0, i, i + 1); bs = [MERGE.get(p['vb'][j], p['vb'][j]) for j in idx]
            if SPLIT and len(set(bs)) > 1:                # DS style: a triangle across a joint is drawn rigidly with each bone
                for b_ in set(bs): tris.append(([pose(p['p'][j], b_) for j in idx], [p['uv'][j] for j in idx], p['g']))
            else: tris.append(([pose(p['p'][j], p['vb'][j]) for j in idx], [p['uv'][j] for j in idx], p['g']))
    P = (np.array([t[0] for t in tris]) - cen0) @ Rz.T; U = np.array([t[1] for t in tris]); G = [t[2] for t in tris]
    img = np.zeros((W, W, 3), np.uint8); img[:] = (52, 60, 84); zb = np.full((W, W), -1e9)
    xs = W / 2 + P[..., 0] / S * W * 0.48; ys = W / 2 - P[..., 2] / S * W * 0.48; zs = -P[..., 1]
    for i in range(len(P)):
        T = TX[G[i]]; th, tw = T.shape[:2]
        x0, x1 = int(max(0, xs[i].min())), int(min(W - 1, xs[i].max())) + 1; y0, y1 = int(max(0, ys[i].min())), int(min(W - 1, ys[i].max())) + 1
        if x1 <= x0 or y1 <= y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        (ax, bx, cx), (ay, by, cy) = xs[i], ys[i]; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0); z = l1 * zs[i, 0] + l2 * zs[i, 1] + l3 * zs[i, 2]; sub = zb[y0:y1, x0:x1]; m &= z > sub
        n = np.cross(P[i, 1] - P[i, 0], P[i, 2] - P[i, 0]); n /= np.linalg.norm(n) + 1e-9; sh = min(1.0, 0.6 + 0.8 * abs(n @ (Rz @ LT)))
        u = l1 * U[i, 0, 0] + l2 * U[i, 1, 0] + l3 * U[i, 2, 0]; v = l1 * U[i, 0, 1] + l2 * U[i, 1, 1] + l3 * U[i, 2, 1]
        tx = np.clip((u * tw).astype(int), 0, tw - 1); ty = np.clip(((1 - v) * th).astype(int), 0, th - 1)
        sub[m] = z[m]; img[y0:y1, x0:x1][m] = (T[ty[m], tx[m]] * sh).astype(np.uint8)
    gy_ = int(W / 2 - (allP[:, 2].min() - cen0[2]) / S * W * 0.48); img[min(W - 1, gy_), :] = (90, 100, 130)
    sheet.paste(Image.fromarray(img), ((k % 8) * W, (k // 8) * W))
sheet.save(OUT)
