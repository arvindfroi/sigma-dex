"""Rigid-skinned preview of the textured low-poly in the rig's poses (each triangle follows its dominant bone), side view.
python pose_preview.py BASE bones.json OUT.png FRAMES"""
import sys, json, numpy as np
from PIL import Image
B, BJ, OUT, FR = sys.argv[1], sys.argv[2], sys.argv[3], [x for x in sys.argv[4].split(',')]
bones = json.load(open(BJ)); polys = json.load(open(B + '.json'))['polys']
T = np.asarray(Image.open(B + '_tex.png').convert('RGB')); TS = T.shape[0]
tris = []
for p in polys:
    for k in range(1, len(p['p']) - 1): tris.append(([p['p'][0], p['p'][k], p['p'][k + 1]], [p['uv'][0], p['uv'][k], p['uv'][k + 1]], p['b']))
rest = {k: np.array(v) for k, v in bones['rest'].items()}
W = 220; out = Image.new('RGB', (W * len(FR), W), (52, 60, 84))
allp = np.array([t[0] for t in tris]).reshape(-1, 3); cen = allp.mean(0); S = np.abs(allp - cen).max()
for fi, f in enumerate(FR):
    M = {k: np.array(v) @ np.linalg.inv(rest[k]) for k, v in bones['frames'][f].items()}
    P = []
    for t in tris:
        m = M.get(t[2], np.eye(4)); P.append([(m @ np.array(list(v) + [1]))[:3] for v in t[0]])
    P = np.array(P) - cen; U = np.array([t[1] for t in tris])
    img = np.zeros((W, W, 3), np.uint8); img[:] = (52, 60, 84); zb = np.full((W, W), -1e9)
    xs = W / 2 + P[..., 1] / S * W * 0.45; ys = W / 2 - P[..., 2] / S * W * 0.45; zs = P[..., 0]
    for i in range(len(P)):
        x0, x1 = int(max(0, xs[i].min())), int(min(W - 1, xs[i].max())) + 1; y0, y1 = int(max(0, ys[i].min())), int(min(W - 1, ys[i].max())) + 1
        if x1 <= x0 or y1 <= y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        (ax, bx, cx), (ay, by, cy) = xs[i], ys[i]; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0); z = l1 * zs[i, 0] + l2 * zs[i, 1] + l3 * zs[i, 2]; sub = zb[y0:y1, x0:x1]; m &= z > sub
        u = l1 * U[i, 0, 0] + l2 * U[i, 1, 0] + l3 * U[i, 2, 0]; v = l1 * U[i, 0, 1] + l2 * U[i, 1, 1] + l3 * U[i, 2, 1]
        tx = np.clip((u * TS).astype(int), 0, TS - 1); ty = np.clip(((1 - v) * TS).astype(int), 0, TS - 1)
        sub[m] = z[m]; img[y0:y1, x0:x1][m] = T[ty[m], tx[m]]
    out.paste(Image.fromarray(img), (fi * W, 0))
out.save(OUT)
