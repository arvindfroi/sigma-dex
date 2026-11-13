"""Give every vertex of the Hunyuan mesh a colour class from the drawing.
python h3d/colour.py MESH.npz CAM.json DRAWING_RGB.png OUT_labels.npy
Classes: 0 body, 1 hat, 2 red, 3 gold, 4 white, 5 eye, 6 pupil, 7 ink
1. classify the drawing's pixels (black lines are filled with the colour next to them)
2. z-buffer the mesh from the fitted camera; vertices that face it get the pixel's class
3. the hidden side copies its mirror twin (the creature is left-right symmetric about y = Y0), the rest grows over the mesh
4. a few majority passes clean up speckles"""
import sys, json, numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage
d = np.load(sys.argv[1]); V = d['V'].astype(np.float64); N = d['N'].astype(np.float64); F = d['F']
cam = json.load(open(sys.argv[2]))
img = np.asarray(Image.open(sys.argv[3]).convert('RGB')).astype(int)
OUT = sys.argv[4]
Y0 = float(__import__('os').environ.get('Y0', -0.015))
H, W = img.shape[:2]
r, g, b = img[..., 0], img[..., 1], img[..., 2]
mx, mn = img.max(-1), img.min(-1)
lab_img = np.full((H, W), -1, int)
ink = mx < 45
white = (mn > 150) & (mx - mn < 45)
red = (r > 70) & (r - g > 45) & (r - b > 35) & (g < 100)
gold = (r - b > 55) & (g - b > 35) & (r > 100) & ~red
dark = (mx < 120) & ~red & ~gold & ~ink
bg = (mn > 245)
lab_img[dark] = 0; lab_img[red] = 2; lab_img[gold] = 3; lab_img[white & ~bg] = 4
# fill lines and unclassified with the nearest classified colour
known = lab_img >= 0
idx = ndimage.distance_transform_edt(~known, return_distances=False, return_indices=True)
lab_fill = lab_img[idx[0], idx[1]]
inkmask = ink.copy()
# ---- camera from fit_cam.py
az, el = np.radians(cam['az']), np.radians(cam['el'])
dv = np.array([np.sin(az) * np.cos(el), -np.cos(az) * np.cos(el), np.sin(el)])   # toward the camera
rr = np.array([np.cos(az), np.sin(az), 0.0]); uu = np.cross(rr, -dv); uu /= np.linalg.norm(uu)
s, bx, by = cam['scale'], cam['bx'], cam['by']
PX = V @ rr * s + bx; PY = -(V @ uu) * s + by; DEP = -(V @ dv)          # smaller DEP = nearer the camera
# ---- z-buffer: paint faces far -> near with their index
zb = np.full((H, W), -1, np.int32)
order = np.argsort(-DEP[F].mean(1))
for fi in order:
    f = F[fi]
    cv2.fillConvexPoly(zb, np.stack([PX[f], PY[f]], 1).round().astype(np.int32), int(fi))
vis_face = np.zeros(len(F), bool); vis_face[np.unique(zb[zb >= 0])] = True
vis = np.zeros(len(V), bool)
for k in range(3): vis[F[vis_face, k]] = True
facing = (N @ dv)
ok = vis & (facing > 0.12)
ui = np.clip(PX.round().astype(int), 0, W - 1); vi = np.clip(PY.round().astype(int), 0, H - 1)
lab = np.full(len(V), -1, int)
lab[ok] = lab_fill[vi[ok], ui[ok]]
print('from drawing', ok.sum(), 'of', len(V), np.bincount(lab[ok], minlength=8))
# ---- mirror: hidden vertices copy their twin across y = Y0
src = np.where(lab >= 0)[0]
tree = cKDTree(V[src])
M = V.copy(); M[:, 1] = 2 * Y0 - M[:, 1]
need = np.where(lab < 0)[0]
dist, j = tree.query(M[need])
take = dist < 0.025
lab[need[take]] = lab[src[j[take]]]
print('mirrored', take.sum(), 'left', (lab < 0).sum())
# ---- grow over the mesh graph
nbr = [[] for _ in range(len(V))]
for a_, b_, c_ in F:
    nbr[a_] += [b_, c_]; nbr[b_] += [a_, c_]; nbr[c_] += [a_, b_]
nbr = [np.unique(n) for n in nbr]
front = [i for i in range(len(V)) if lab[i] >= 0]
from collections import deque
q = deque(front)
while q:
    i = q.popleft()
    for n_ in nbr[i]:
        if lab[n_] < 0: lab[n_] = lab[i]; q.append(n_)
lab[lab < 0] = 0
# ---- clean speckles: majority of neighbours, 3 passes
for _ in range(3):
    new = lab.copy()
    for i in range(len(V)):
        c = np.bincount(lab[nbr[i]], minlength=8)
        if c[lab[i]] <= 1 and c.max() >= 3: new[i] = c.argmax()
    lab = new
np.save(OUT, lab)
print('classes', np.bincount(lab, minlength=8))
