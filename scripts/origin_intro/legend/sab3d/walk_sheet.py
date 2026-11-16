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
_zc = __import__('os').environ.get('ZC')                         # ZC=x,y,z ZS=half-size: zoom on a point (close-ups)
if _zc: cen0 = np.array([float(t) for t in _zc.split(',')]); S = float(__import__('os').environ.get('ZS', '1.2'))
a = np.radians(AZ); Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
_el = np.radians(float(__import__('os').environ.get('EL', '0'))); Rz = np.array([[1, 0, 0], [0, np.cos(_el), -np.sin(_el)], [0, np.sin(_el), np.cos(_el)]]) @ Rz   # EL: look from above
sheet = Image.new('RGB', (W * 8, W * ((len(FR) + 7) // 8)), (52, 60, 84))
for k, fr in enumerate(FR):
    F = {b: np.array(m) for b, m in J['frames'][str(fr)].items()}
    K = {b: F[b] @ np.linalg.inv(rest[b]) for b in F}
    def helperK(a, c):                                     # as rig3d: halfway rotation about the joint (child's rest head)
        from scipy.spatial.transform import Rotation as Rot, Slerp
        KA, KB = K[a], K[c]; pB = rest[c][:3, 3]
        Rt = Slerp([0, 1], Rot.from_matrix([KA[:3, :3], KB[:3, :3]]))([0.5]).as_matrix()[0]
        pt = ((KA @ np.append(pB, 1))[:3] + (KB @ np.append(pB, 1))[:3]) / 2; M = np.eye(4); M[:3, :3] = Rt; M[:3, 3] = pt - Rt @ pB; return M
    PAR = {b: (MERGE.get(J['parent'][b], J['parent'][b]) if J['parent'].get(b) else None) for b in J['rest']}
    SM = __import__('os').environ.get('SMOOTH', '1') == '1'; HK = {}
    def eff(a, vw):
        if not SM or not vw: return a
        b2 = MERGE.get(vw[0], vw[0]); w = vw[1]
        if w < 0.25 or b2 == a: return a
        if PAR.get(b2) == a: return ('h', a, b2)
        if PAR.get(a) == b2: return ('h', b2, a)
        return a
    def pose(q, b, vw=None):
        b = eff(MERGE.get(b, b), vw)
        if isinstance(b, tuple):
            if b not in HK: HK[b] = helperK(b[1], b[2])
            M = HK[b]
        else: M = K[b]
        LASTR[0] = M[:3, :3]; return (M @ np.append(q, 1))[:3]
    LASTR = [np.eye(3)]
    def posen(q, n, b, vw=None):
        x = pose(q, b, vw); nn = LASTR[0] @ np.array(n if n is not None else [0, 0, 1.0]); return x, nn / (np.linalg.norm(nn) + 1e-9)
    tris = []; SPLIT = __import__('os').environ.get('SPLIT', '1') == '1'
    for p in D:
        for i in range(1, len(p['p']) - 1):
            idx = (0, i, i + 1); bs = [MERGE.get(p['vb'][j], p['vb'][j]) for j in idx]
            if SPLIT and len(set(bs)) > 1:                # DS style: a triangle across a joint is drawn rigidly with each bone
                for b_ in set(bs): tris.append(([pose(p['p'][j], b_) for j in idx], [p['uv'][j] for j in idx], p['g']))
            else:
                pn = [posen(p['p'][j], (p.get('n') or [None] * 3)[j], p['vb'][j], (p.get('vw') or [None] * 3)[j]) for j in idx]
                tris.append(([x for x, _ in pn], [p['uv'][j] for j in idx], p['g'], [nn for _, nn in pn]))
    P = (np.array([t[0] for t in tris]) - cen0) @ Rz.T; U = np.array([t[1] for t in tris]); G = [t[2] for t in tris]
    NV = np.array([t[3] if len(t) > 3 else [np.zeros(3)] * 3 for t in tris]) @ Rz.T
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
        nn_ = l1[..., None] * NV[i, 0] + l2[..., None] * NV[i, 1] + l3[..., None] * NV[i, 2]; nn_ /= np.linalg.norm(nn_, axis=-1, keepdims=True) + 1e-9
        sh = np.clip(0.55 + 0.75 * np.abs(nn_ @ (Rz @ LT)), 0, 1.1)
        u = l1 * U[i, 0, 0] + l2 * U[i, 1, 0] + l3 * U[i, 2, 0]; v = l1 * U[i, 0, 1] + l2 * U[i, 1, 1] + l3 * U[i, 2, 1]
        tx = np.clip((u * tw).astype(int), 0, tw - 1); ty = np.clip(((1 - v) * th).astype(int), 0, th - 1)
        sub[m] = z[m]; img[y0:y1, x0:x1][m] = np.clip(T[ty[m], tx[m]] * sh[m][:, None], 0, 255).astype(np.uint8)
    gy_ = int(W / 2 - (allP[:, 2].min() - cen0[2]) / S * W * 0.48); img[min(W - 1, gy_), :] = (90, 100, 130)
    sheet.paste(Image.fromarray(img), ((k % 8) * W, (k // 8) * W))
sheet.save(OUT)
