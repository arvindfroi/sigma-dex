"""Preview of a textured film model (bind pose, unlit, nearest texels like the DS) from several angles, next to the
same model with another texture set: python preview_views.py A_BASE B_BASE OUT.png [SIZE]
A_BASE/B_BASE: BASE.json (polys with uv + g) and BASE_tex{g}.png (or BASE_albedo{g}.png with env ALB_A/ALB_B=1)"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw
AB, BB, OUT = sys.argv[1:4]; SZ = int(sys.argv[4]) if len(sys.argv) > 4 else 256
def load(base, alb):
    P = json.load(open(base + '.json'))['polys']
    T = {}
    for g in (0, 1, 2):
        f = f'{base}_albedo{g}.png' if alb else f'{base}_tex{g}.png'
        if os.path.exists(f): T[g] = np.asarray(Image.open(f).convert('RGB')).astype(float)
    return P, T
def render(P, T, yaw, pitch, size):
    V = np.array([p['p'] for p in P], float); UV = np.array([p['uv'] for p in P], float); G = [p['g'] for p in P]
    c = np.array([float(x) for x in os.environ['CENTER'].split(',')]) if os.environ.get('CENTER') else V.reshape(-1, 3).mean(0); V = V - c
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    W = V @ (Rx @ Rz).T                                         # view: looking along +y (from -y), z up
    ext = 0.55 * size / 3.6 * float(os.environ.get('ZOOM', '1')); Q = np.stack([size / 2 + ext * W[..., 0], size / 2 - ext * W[..., 2]], -1); depth = -W[..., 1]
    zb = np.full((size, size), -1e9); img = np.full((size, size, 3), 235.0)
    for i in range(len(P)):
        q = Q[i]; x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy_) = q; den = (by - cy_) * (ax - cx) + (cx - bx) * (ay - cy_)
        if abs(den) < 1e-9: continue
        l0 = ((by - cy_) * (gx - cx) + (cx - bx) * (gy - cy_)) / den; l1 = ((cy_ - ay) * (gx - cx) + (ax - cx) * (gy - cy_)) / den; l2 = 1 - l0 - l1
        ins = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
        z = l0 * depth[i, 0] + l1 * depth[i, 1] + l2 * depth[i, 2]; sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z > sub)
        if not upd.any(): continue
        sub[upd] = z[upd]; t = T.get(G[i])
        if t is None: img[y0:y1 + 1, x0:x1 + 1][upd] = (255, 0, 255); continue
        uv = l0[upd][:, None] * UV[i, 0] + l1[upd][:, None] * UV[i, 1] + l2[upd][:, None] * UV[i, 2]; h, w = t.shape[:2]
        xx = np.clip((uv[:, 0] * w).astype(int), 0, w - 1); yy = np.clip(((1 - uv[:, 1]) * h).astype(int), 0, h - 1)
        img[y0:y1 + 1, x0:x1 + 1][upd] = t[yy, xx]
    return img
ANG = [(0, 8, 'forfra'), (-60, 12, 'skra forfra'), (-90, 5, 'fra siden'), (-150, 20, 'skra bakfra'), (180, 35, 'bakfra ovenfra')]
if os.environ.get('HEADVIEW'): ANG = [(0, 5, 'forfra'), (-30, 8, 'litt fra siden'), (-60, 10, 'skra forfra'), (-90, 3, 'fra siden'), (-25, -15, 'nedenfra')]
rows = [(AB, os.environ.get('LAB_A', 'ny'), os.environ.get('ALB_A') == '1'), (BB, os.environ.get('LAB_B', 'gammel'), os.environ.get('ALB_B') == '1')]
z = Image.new('RGB', (len(ANG) * (SZ + 6), len(rows) * (SZ + 20)), 'white'); d = ImageDraw.Draw(z)
for r, (base, lab, alb) in enumerate(rows):
    P, T = load(base, alb)
    for k, (yw, pt, nm) in enumerate(ANG):
        im = render(P, T, yw, pt, SZ); z.paste(Image.fromarray(im.astype(np.uint8)), (k * (SZ + 6), r * (SZ + 20) + 18)); d.text((k * (SZ + 6) + 4, r * (SZ + 20) + 3), f'{lab}: {nm}', fill='black')
z.save(OUT); print('ok', OUT)
