"""Find the orthographic view of the mesh that best matches the input picture's silhouette.
python h3d/fit_cam.py MESH.npz INPUT_RGBA.png OUTPREFIX
Camera: azimuth az (degrees, 0 = looking from -Y toward +Y, positive = camera swings toward +X), elevation el.
Saves OUTPREFIX_cam.json (az, el, roll, scale, bx, by) and OUTPREFIX_fit.png."""
import sys, json, numpy as np, cv2
from PIL import Image
d = np.load(sys.argv[1]); V = d['V'].astype(np.float64)
im = np.asarray(Image.open(sys.argv[2])); mask = im[..., 3] > 127
H, W = mask.shape
ys, xs = np.where(mask); ib = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)
small = cv2.resize(mask.astype(np.uint8), (256, 256), interpolation=cv2.INTER_NEAREST) > 0
def proj(az, el):
    a, e = np.radians(az), np.radians(el)
    # camera right / up vectors for a camera at direction (sin a, -cos a)*cos e + z sin e looking at the origin
    dv = np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])
    r = np.array([np.cos(a), np.sin(a), 0.0])
    u = np.cross(r, -dv); u /= np.linalg.norm(u)
    # camera looks along -dv; right = r; up = u
    return V @ r, V @ u
def sil(px, py, a, bx, by, S=256):
    U = np.clip(np.rint((px * a + bx) * S / W).astype(int), 0, S - 1); Vv = np.clip(np.rint((-py * a + by) * S / H).astype(int), 0, S - 1)
    s = np.zeros((S, S), np.uint8); s[Vv, U] = 1
    return cv2.morphologyEx(s, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
def score(az, el, ret=False):
    px, py = proj(az, el)
    mb = np.array([px.min(), py.min(), px.max(), py.max()])
    best = None
    for a in np.linspace(0.92, 1.08, 9) * ((ib[2] - ib[0]) / (mb[2] - mb[0]) + (ib[3] - ib[1]) / (mb[3] - mb[1])) / 2:
        bx0 = (ib[0] + ib[2]) / 2 - a * (mb[0] + mb[2]) / 2; by0 = (ib[1] + ib[3]) / 2 + a * (mb[1] + mb[3]) / 2
        for dx in (-16, -8, 0, 8, 16):
            for dy in (-16, -8, 0, 8, 16):
                s = sil(px, py, a, bx0 + dx, by0 + dy)
                iou = (s & small).sum() / (s | small).sum()
                if best is None or iou > best[0]: best = (iou, a, bx0 + dx, by0 + dy)
    return best
res = []
for az in range(-60, 61, 10):
    for el in range(int(__import__("os").environ.get("EL0", -10)), 41, 10):
        b = score(az, el); res.append((b[0], az, el, b))
res.sort(reverse=True)
print('coarse top', [(round(r[0], 3), r[1], r[2]) for r in res[:5]])
_, az0, el0, _ = res[0]
res2 = []
for az in np.arange(az0 - 8, az0 + 9, 2):
    for el in np.arange(max(el0 - 8, float(__import__("os").environ.get("EL0", -90))), el0 + 9, 2):
        b = score(az, el); res2.append((b[0], float(az), float(el), b))
res2.sort(reverse=True)
iou, az, el, b = res2[0]
print('fine best iou', round(iou, 3), 'az', az, 'el', el)
_, a, bx, by = b
json.dump(dict(az=az, el=el, scale=a, bx=bx, by=by, iou=iou, W=W, H=H), open(sys.argv[3] + '_cam.json', 'w'))
px, py = proj(az, el)
U = np.clip(np.rint(px * a + bx).astype(int), 0, W - 1); Vv = np.clip(np.rint(-py * a + by).astype(int), 0, H - 1)
s = np.zeros((H, W), np.uint8); s[Vv, U] = 1; s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) > 0
ov = np.full((H, W, 3), 255, np.uint8); ov[mask] = (120, 180, 255); ov[s & ~mask] = (255, 80, 80); ov[s & mask] = (90, 90, 90)
Image.fromarray(ov).save(sys.argv[3] + '_fit.png')
