"""Gravriel's overworld frames (LUG_OBJ01, a/0/8/1 211) rendered from his painted film model (2026-11-17, Arvind: "next
is Gravriel's overworld sprite"), so the sprite and the film are the same creature.
Lugia's 7 frames: 1-5 the wing beat (the flight cycle while it comes down), 6 wings folded (landed), 7 the cry. Gravriel
has no wings: 1-5 are his float cycle (the film's Swim_Idle_Loop, arms treading the water), 6 hanging still, 7 the cry
with the cutlass raised high (the right arm chain turned rigidly about the shoulder, like export_gravparts' POINT).
Seen from the front and a little from above, like the overworld sprites (PITCH degrees).
python ow_render.py G.json OUTDIR      -> OUTDIR/r{1..7}.png (RGBA, RES px), sheet.png
env: PITCH (18), RES (256), CYCLE ('6,18,30,42,54': film frames of the float cycle), REST (120), CRY_DIR, YAW (0)"""
import sys, os, json, math
import numpy as np
from PIL import Image
GJ, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
E = lambda k, d: float(os.environ.get(k, d))
J = json.load(open(GJ)); D = os.path.dirname(os.path.abspath(GJ))
TEX = {int(k): np.asarray(Image.open(os.path.join(D, os.path.basename(v[0]))).convert('RGB')).astype(float) for k, v in J['tex'].items()}
B = {b: np.array(m) for b, m in J['bind'].items()}; Bi = {b: np.linalg.inv(m) for b, m in B.items()}
POLYS = [p for p in J['polys'] if p.get('part') not in ('ghost', 'mist') and p.get('lab') != 'mist']
LABS = list(J.get('names', [])); GROUP = {'body': 1, 'armL': 2, 'armR': 3, 'sword': 4}
RES = int(E('RES', 256)); PITCH = math.radians(E('PITCH', 18)); YAW = math.radians(E('YAW', 0))
def frame(f): return {b: np.array(m) for b, m in J['frames'][str(min(int(f), len(J['frames']) - 1))].items()}
def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(a @ b)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + K + K @ K / (1 + c)
def raise_sword(F, D_):
    """the right arm chain rigid in its bind pose, turned about the shoulder so the blade points along D_"""
    sw = [np.array(p['p']) for p in J['polys'] if p.get('part') == 'sword']
    if not sw: return F
    SV = np.vstack(sw); hand = B['DEF-hand.R'][:3, 3]; grip = SV[np.argmin(np.linalg.norm(SV - hand, axis=1))]; tip = SV[np.argmax(np.linalg.norm(SV - grip, axis=1))]
    R3 = rot_between(tip - grip, np.array(D_, float)); Rp = np.eye(4); Rp[:3, :3] = R3
    piv0 = B['DEF-upper_arm.R'][:3, 3]; piv = F['DEF-upper_arm.R'][:3, 3]
    T = lambda t: np.block([[np.eye(3), np.array(t)[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]])
    F = dict(F)
    for b in ('DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R'): F[b] = T(piv) @ Rp @ T(-piv0) @ B[b]
    return F
def skin(F):
    K = {b: F[b] @ Bi[b] for b in B}
    def sk(q, b, w):
        v = np.append(q, 1); a = (K[b] @ v)[:3]
        if w: a = a * (1 - w[1]) + (K[w[0]] @ v)[:3] * w[1]
        return a
    return [np.array([sk(np.array(q), b, w) for q, b, w in zip(p['p'], p['vb'], p.get('vw', [None] * len(p['vb'])))]) for p in POLYS]
def render(PP, box=None):
    cy, sy = math.cos(YAW), math.sin(YAW); Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    d = np.array([0, math.cos(PITCH), -math.sin(PITCH)]); up = np.array([0, math.sin(PITCH), math.cos(PITCH)]); rt = np.array([1.0, 0, 0])
    QQ = [P @ Rz.T for P in PP]; allq = np.vstack(QQ)
    sx_all, sy_all = allq @ rt, allq @ up
    if box is None: box = (sx_all.min(), sx_all.max(), sy_all.min(), sy_all.max())
    x0b, x1b, y0b, y1b = box; sc = 0.94 * RES / max(x1b - x0b, y1b - y0b); cx = (x0b + x1b) / 2; cyy = (y0b + y1b) / 2
    img = np.zeros((RES, RES, 4)); zb = np.full((RES, RES), 1e9); lbuf = np.zeros((RES, RES), np.int16)
    for p, Q in zip(POLYS, QQ):
        n = np.cross(Q[1] - Q[0], Q[2] - Q[0])
        if n @ d >= 0: continue                                     # back faces culled (as in the film)
        uv = np.array(p['uv']); T_ = TEX[p['g']]; th, tw = T_.shape[:2]
        sxp = RES / 2 + (Q @ rt - cx) * sc; syp = RES / 2 - (Q @ up - cyy) * sc; dep = Q @ d
        for tri in ([0, 1, 2], [0, 2, 3])[: len(Q) - 2]:
            X, Y, Z, t = sxp[tri], syp[tri], dep[tri], uv[tri]
            x0, x1 = int(max(0, X.min())), int(min(RES - 1, X.max())) + 1; y0, y1 = int(max(0, Y.min())), int(min(RES - 1, Y.max())) + 1
            if x0 >= x1 or y0 >= y1: continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5; dd = (X[1] - X[0]) * (Y[2] - Y[0]) - (X[2] - X[0]) * (Y[1] - Y[0])
            if abs(dd) < 1e-9: continue
            w1 = ((xx - X[0]) * (Y[2] - Y[0]) - (X[2] - X[0]) * (yy - Y[0])) / dd; w2 = ((X[1] - X[0]) * (yy - Y[0]) - (xx - X[0]) * (Y[1] - Y[0])) / dd; w0 = 1 - w1 - w2
            m = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3); z = w0 * Z[0] + w1 * Z[1] + w2 * Z[2]; m &= z < zb[y0:y1, x0:x1]
            if not m.any(): continue
            u = w0 * t[0, 0] + w1 * t[1, 0] + w2 * t[2, 0]; v = w0 * t[0, 1] + w1 * t[1, 1] + w2 * t[2, 1]
            cc = T_[np.clip(((1 - v) * th).astype(int), 0, th - 1), np.clip((u * tw).astype(int), 0, tw - 1)]
            sub = img[y0:y1, x0:x1]; sub[m, :3] = cc[m]; sub[m, 3] = 255; zb[y0:y1, x0:x1][m] = z[m]; lbuf[y0:y1, x0:x1][m] = GROUP.get(p.get('part'), 0) * 100 + LABS.index(p.get('lab', '')) if p.get('lab', '') in LABS else 0
    return img, box, lbuf
CYC = [int(x) for x in os.environ.get('CYCLE', '6,18,30,42,54').split(',')]; REST = int(E('REST', 120))
CRY = [float(x) for x in os.environ.get('CRY_DIR', '-0.35,-0.25,0.9').split(',')]
poses = [frame(f) for f in CYC] + [frame(REST), raise_sword(frame(REST), CRY)]
PPs = [skin(F) for F in poses]
# one shared framing for all 7 (the sprite must not jump between frames)
rt = np.array([1.0, 0, 0]); up = np.array([0, math.sin(PITCH), math.cos(PITCH)])
allq = np.vstack([np.vstack(PP) for PP in PPs]); box = ((allq @ rt).min(), (allq @ rt).max(), (allq @ up).min(), (allq @ up).max())
w_, h_ = box[1] - box[0], box[3] - box[2]; m_ = max(w_, h_); cxb, cyb = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
box = (cxb - m_ / 2, cxb + m_ / 2, cyb - m_ / 2, cyb + m_ / 2)
# tight framing: the union of what is actually drawn (a few skinned points of culled faces lie far out)
al = np.zeros((RES, RES), bool)
for PP in PPs: al |= render(PP, box)[0][..., 3] > 0
ys, xs = np.nonzero(al); sc0 = 0.94 * RES / (box[1] - box[0]); cx0, cy0 = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
X0, X1 = cx0 + (xs.min() - RES / 2) / sc0, cx0 + (xs.max() + 1 - RES / 2) / sc0; Y1, Y0 = cy0 - (ys.min() - RES / 2) / sc0, cy0 - (ys.max() + 1 - RES / 2) / sc0
m_ = max(X1 - X0, Y1 - Y0); cxb, cyb = (X0 + X1) / 2, (Y0 + Y1) / 2; box = (cxb - m_ / 2, cxb + m_ / 2, cyb - m_ / 2, cyb + m_ / 2)
sheet = Image.new('RGBA', (RES * 7, RES), (40, 44, 60, 255))
for k, PP in enumerate(PPs):
    img, _, lb = render(PP, box); im = Image.fromarray(img.astype(np.uint8), 'RGBA'); im.save(os.path.join(OUT, 'r%d.png' % (k + 1))); np.save(os.path.join(OUT, 'l%d.npy' % (k + 1)), lb)
    sheet.alpha_composite(im, (k * RES, 0))
sheet.convert('RGB').save(os.path.join(OUT, 'sheet.png')); json.dump(dict(labs=LABS, groups=GROUP, box=box, pitch=E('PITCH', 18), cycle=CYC, rest=REST, cry=CRY), open(os.path.join(OUT, 'render.json'), 'w'))
print('ok', OUT, 'box', [round(x, 3) for x in box])
