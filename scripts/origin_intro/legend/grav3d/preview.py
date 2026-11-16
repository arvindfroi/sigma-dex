"""Quick look at export_gravfilm.py's output: rigid per-vertex skinning, painter's algorithm, flat colours with a simple
light. python preview.py G.json OUT.png [FRAMES=0,110,130,150,165,180,200,230] [AZ=0,35]"""
import sys, json, numpy as np
from PIL import Image, ImageDraw
J = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FR = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '0,110,130,150,165,180,200,230').split(',')]
AZ = [float(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '0,35').split(',')]
PAL = {n: c for n, c in zip(J['names'], J['palette'])}; PAL['eye'] = [120, 255, 230]; PAL['socket'] = [8, 10, 10]
B = {b: np.array(m) for b, m in J['bind'].items()}; Bi = {b: np.linalg.inv(m) for b, m in B.items()}
polys = J['polys']; W, H = 260, 300; sc = 34
L = np.array([0.3, -0.6, 0.75]); L /= np.linalg.norm(L)
sheet = Image.new('RGB', (W * len(FR), H * len(AZ)), (200, 205, 210)); dr = ImageDraw.Draw(sheet)
for r, az in enumerate(AZ):
    a = np.radians(az); Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    for c_, f in enumerate(FR):
        M = {b: np.array(m) @ Bi[b] for b, m in J['frames'][str(f)].items()}
        tris = []
        for p in polys:
            P = np.array([(M[b] @ np.append(q, 1))[:3] for q, b in zip(p['p'], p['vb'])]) @ Rz.T
            n = np.cross(P[1] - P[0], P[2] - P[0]); nn = np.linalg.norm(n)
            sh = 0.55 + 0.45 * abs(n @ L) / nn if nn > 1e-9 else 0.8
            col = tuple(int(min(255, v * sh)) for v in PAL[p['lab']])
            tris.append((P[:, 1].mean(), P, col))
        tris.sort(key=lambda t: -t[0])                                   # far (+y) first: the camera looks from -y
        ox, oy = c_ * W + W / 2, r * H + H * 0.55
        for _, P, col in tris:
            dr.polygon([(ox + x * sc, oy - z * sc) for x, y, z in P], fill=col)
        dr.text((c_ * W + 4, r * H + 4), 'frame %d az %d' % (f, az), fill='black')
sheet.save(OUT); print('ok', OUT)
