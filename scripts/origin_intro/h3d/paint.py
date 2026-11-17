"""Paint colour classes on the Hunyuan mesh by region (seed 3; creature faces -X, Z up, mirror plane y = Y0).
python h3d/paint.py MESH.npz PROJ_LABELS.npy OUT_labels.npy
Classes: 0 body, 1 hat, 2 red, 3 gold, 4 white, 5 eye, 6 pupil, 7 ink (brow / mast)
The drawing's projection (colour.py) is only used for the sail and flag emblems; the rest follows the shapes."""
import sys, os, numpy as np, cv2
from scipy import ndimage
d = np.load(sys.argv[1]); V = d['V'].astype(float); N = d['N'].astype(float); F = d['F']; T = d['thick']
proj = np.load(sys.argv[2])
Y0 = float(os.environ.get('Y0', -0.015))
x, y, z = V[:, 0], V[:, 1] - Y0, V[:, 2]
ay = np.abs(y); nz = N[:, 2]
lab = np.zeros(len(V), int)

head = x < -0.42
hat = head & ((z > 0.0) | ((z > -0.1) & (ay > 0.3)))
upper = (~head) & (x > -0.55) & (z > -0.44)                    # hull + rigging
# poles: in horizontal slices they are small round blobs; sails are long thin curves
pole = np.zeros(len(V), bool)
R = 0.008
for z0 in np.arange(-0.06, 0.95, 0.02):
    sl = np.where(upper & (z >= z0) & (z < z0 + 0.02) & (x > -0.1))[0]
    if len(sl) == 0: continue
    gx = ((x[sl] + 0.2) / R).astype(int); gy = ((y[sl] + 0.6) / R).astype(int)
    g = np.zeros((gx.max() + 3, gy.max() + 3), np.uint8); g[gx, gy] = 1
    g = cv2.dilate(g, np.ones((3, 3), np.uint8))
    lb, n = ndimage.label(g)
    for k, sli in enumerate(ndimage.find_objects(lb), 1):
        ext = max(sli[0].stop - sli[0].start, sli[1].stop - sli[1].start) * R
        if ext < 0.075:
            mem = lb[gx, gy] == k
            # at hull level only count it if it sticks out above the hull top
            pole[sl[mem]] = True
hull_top = np.interp(x, [-0.45, -0.2, 0.0, 0.2, 0.45, 0.7, 0.9], [-0.07, -0.04, 0.01, 0.04, 0.09, 0.1, -0.1])
pole &= (z > hull_top - 0.01) | (z > 0.12)
pole |= upper & (z > hull_top + 0.015) & (z < 0.125) & (x > -0.2)       # the masts between the hull and the sail
cloth = upper & (z > 0.1) & ~pole
hull = upper & ~cloth & ~pole
# ---- hull: red, black bottom rim and wale band, thin gold line above the band, gold-lit ports, gold rail on top
zb = np.interp(x, [-0.45, -0.38, -0.3, -0.2, 0.0, 0.7, 0.9], [-0.12, -0.3, -0.37, -0.41, -0.435, -0.435, -0.38])
zt = hull_top
fr = (z - zb) / np.maximum(zt - zb, 0.05)
lab[hull] = 2
lab[hull & (fr < 0.1)] = 0
B0, B1 = float(os.environ.get('BAND0', 0.36)), float(os.environ.get('BAND1', 0.5))
lab[hull & (fr > B0) & (fr < B1)] = 0
lab[hull & (fr >= B1) & (fr < B1 + 0.05)] = 3
# gun ports as in the drawing: three black pointed arches in the red strip above the band, rear two thirds of
# the hull, each with a gold cannon muzzle sticking out at its foot (env PORTS = x positions)
side = hull & (ay > 0.12) & (np.abs(N[:, 1]) > 0.35)
PORTS = [float(v) for v in os.environ.get('PORTS', '0.12,0.38,0.63').split(',')]
for px in PORTS:
    u = (x - px) / 0.075; v = (fr - (B1 + 0.2)) / 0.14
    arch = (v > -1) & (v < 1) & (np.abs(u) < (1 - v) * 0.55)
    lab[side & arch] = 7
    muzzle = ((u - 0.15) / 0.42) ** 2 + ((v + 0.72) / 0.32) ** 2 < 1
    lab[side & muzzle] = 3
lab[pole] = 7
# ---- cloth: white with the drawing's gold emblem (projection); its dark bits become white
lab[cloth] = np.where(proj[cloth] == 3, 3, 4)
# ---- hat: black, gold trim along the brim's outer edge (top-view outline), gold emblem in front
lab[hat] = 1
S = 500; lo = np.array([-1.05, -0.85])
def to_px(px_, py_): return ((px_ - lo[0]) * S / 1.9).astype(int), ((py_ - lo[1]) * S / 1.9).astype(int)
hx, hy = to_px(x[hat], y[hat])
m = np.zeros((S, S), np.uint8); m[np.clip(hy, 0, S - 1), np.clip(hx, 0, S - 1)] = 1
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
dist = ndimage.distance_transform_edt(m) * 1.9 / S
ax_, ay_ = to_px(x, y)
dv = dist[np.clip(ay_, 0, S - 1), np.clip(ax_, 0, S - 1)]
trim = hat & (dv < float(os.environ.get('TRIM', 0.02))) & (z < 0.025 + 0.1 * (ay / 0.7) ** 2) & (nz > -0.3)
lab[trim] = 3
front = hat & (N[:, 0] < -0.35) & (ay < 0.11) & (z > 0.02) & (z < 0.2)
ez, ey = z - 0.105, y
skull = (ez / 0.038) ** 2 + (ey / 0.04) ** 2 < 1
bone1 = (np.abs((ez + 0.04) - 0.55 * ey) < 0.012) & (np.abs(ey) < 0.075) & (ez < -0.015)
bone2 = (np.abs((ez + 0.04) + 0.55 * ey) < 0.012) & (np.abs(ey) < 0.075) & (ez < -0.015)
eyeh = (ez / 0.012) ** 2 + ((np.abs(ey) - 0.016) / 0.011) ** 2 < 1
lab[front & (skull | bone1 | bone2) & ~eyeh] = 3
# ---- face
nose = (x < -0.885) & (z > -0.085) & (z < -0.04) & (ay < 0.06) & (N[:, 0] < -0.45)
lab[nose] = 3
tusk = (x < -0.8) & (z < -0.205) & (z > -0.42) & (ay < 0.27) & (ay > 0.05)
lab[tusk] = 4
ECY, ECZ = float(os.environ.get('ECY', 0.15)), float(os.environ.get('ECZ', -0.062))
face = head & ~hat & (x > -0.86) & (x < -0.6) & (z > -0.12) & (z < 0.0) & (N[:, 0] < 0.1)
slant = ECZ - 0.28 * (ay - ECY)                                   # inner end lower: an angry look
ea = ((ay - ECY) / 0.085) ** 2 + ((z - slant) / 0.036) ** 2
lab[face & (ea < 1) & (z < slant + 0.012 + 0.3 * (ay - ECY))] = 5   # the top is cut by a slanted brow: angry
lab[face & (((ay - (ECY - 0.022)) / 0.026) ** 2 + ((z - slant + 0.004) / 0.024) ** 2 < 1)] = 6
brow = face & (np.abs(z - (slant + 0.024 + 0.3 * (ay - ECY))) < 0.012) & (ay > 0.06) & (ay < 0.25)
lab[brow] = 7
# ---- legs: gold cuffs on the forelegs with a ragged top, white claws
legs = (z < -0.44) & ~hull
for cy in (-0.43, 0.43):
    r = np.hypot(x + 0.70, V[:, 1] - cy)
    ang = np.arctan2(V[:, 1] - cy, x + 0.70)
    top = -0.535 + 0.03 * np.sin(ang * 7) + 0.015 * np.sin(ang * 17 + 1)
    cuff = legs & (r < 0.24) & (z > -0.675) & (z < top)
    lab[cuff] = 3
claw = legs & (z < float(os.environ.get('CLAWZ', -0.79))) & (lab != 3)
lab[claw] = 4
# ---- stern ornament (will be replaced by the gold skull): gold for now
stern = (x > 0.74) & (z > -0.5) & (z < 0.12) & ~cloth & ~pole
lab[stern] = 3
np.save(sys.argv[3], lab)
# parts (for the outline step and the rig): 0 body 1 hat 2 hull 3 sail 4 mast 5 eye 6 tusk 7 nose 8 stern 9 facemark 10 trim
part = np.zeros(len(V), int)
part[hat] = 1; part[hat & (lab == 3)] = 10
part[hull] = 2; part[cloth] = 3; part[pole] = 4
part[lab == 5] = 5; part[tusk] = 6; part[nose] = 7; part[(lab == 6) | (lab == 7) & head] = 9
part[stern] = 8
np.save(sys.argv[3].replace('.npy', '_part.npy'), part)
print('classes', np.bincount(lab, minlength=8), 'pole', pole.sum(), 'cloth', cloth.sum())
