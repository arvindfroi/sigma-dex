"""Paint the grafted mesh (graft.py): the body keeps v7's rules (paint.py); the seed-1 head gets its own rules,
measured on that head: gold nose on the snout's top front, white sabre teeth from the mouth corners, open angry eyes
(white, pupil toward the nose, heavy brow slanting down to the nose) in the carved eye slits, black hat with a gold
rim and a gold skull and crossbones on the crown's front.
python h3d/paint8.py GRAFT.npz PROJ.npy OUT.npy   (also writes OUT_part.npy)"""
import sys, os, runpy, numpy as np
from scipy import ndimage
import cv2
gp, pp, out = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(here, 'paint.py'), gp, pp, out]
runpy.run_path(sys.argv[0], run_name='__main__')
lab = np.load(out); part = np.load(out.replace('.npy', '_part.npy'))
d = np.load(gp); V = d['V'].astype(float); N = d['N'].astype(float); src = d['src']
YC = float(os.environ.get('YC', -0.045))                 # the seed-1 head's own middle (it sits a little off Y0)
x, y, z = V[:, 0], V[:, 1] - YC, V[:, 2]; ay = np.abs(y)
H = src == 1
lab[H] = 0; part[H] = 0
# ---- hat: the brim over the face from z 0.05, the side brims lower down
hat = H & ((z > 0.05) | ((z > 0.0) & (ay > 0.30)))
# the ears sit under the side brims: anything more than 0.06 below the brim's top in its (x, y) cell is head, not hat
gx = ((x + 1.0) / 0.025).astype(int); gy = ((y + 0.8) / 0.025).astype(int)
top = np.full((gx.max() + 2, gy.max() + 2), -9.0)
np.maximum.at(top, (gx[hat], gy[hat]), z[hat])
ear = hat & (ay > 0.25) & (x > -0.74) & (z < top[gx, gy] - 0.06)
hat &= ~ear
lab[hat] = 1; part[hat] = 1
# gold rim along the brim's edge, as in the drawing: the brim is a thin sheet, and at its edge the surface turns over,
# so a rim point has a neighbour within RR whose normal points the other way; the crown's top edge stays black
from scipy.spatial import cKDTree
hi = np.where(hat)[0]; tr = cKDTree(V[hi])
RR = float(os.environ.get('RIMR', 0.02))
rim = np.zeros(len(V), bool)
for k, nb in enumerate(tr.query_ball_point(V[hi], RR)):
    if len(nb) > 1 and (N[hi[nb]] @ N[hi[k]]).min() < -0.25: rim[hi[k]] = True
crown = hat & (z > 0.13) & (ay < 0.26)
trim = rim & ~crown
lab[trim] = 3; part[trim] = 10
# emblem on the crown's front: skull + crossed bones
ef = hat & (N[:, 0] < -0.3) & (x < -0.62) & (ay < 0.16) & (z > 0.1)
ez, ey = z - float(os.environ.get('EMZ', 0.205)), y
sk = (ez / 0.034) ** 2 + (ey / 0.036) ** 2 < 1
b1 = (np.abs((ez + 0.045) - 0.5 * ey) < 0.011) & (np.abs(ey) < 0.07) & (ez < -0.02)
b2 = (np.abs((ez + 0.045) + 0.5 * ey) < 0.011) & (np.abs(ey) < 0.07) & (ez < -0.02)
holes = (ez / 0.011) ** 2 + ((np.abs(ey) - 0.014) / 0.01) ** 2 < 1
lab[ef & (sk | b1 | b2) & ~holes] = 3; part[ef & (sk | b1 | b2)] = 10
# ---- face (not hat)
face = H & ~hat
nose = face & (x < -0.912) & (z > -0.004) & (z < 0.032) & (ay < 0.042) & ((N[:, 0] < -0.2) | (N[:, 2] > 0.4))
lab[nose] = 3; part[nose] = 7
# teeth: thin curved cylinders from the mouth corners down to the chest
a0 = np.array([-0.905, 0.163, -0.13]); a1 = np.array([-0.83, 0.18, -0.41])
P = np.stack([x, ay, z], 1); t = np.clip(((P - a0) @ (a1 - a0)) / ((a1 - a0) @ (a1 - a0)), 0, 1)
dax = np.linalg.norm(P - (a0 + t[:, None] * (a1 - a0)), axis=1)
TR = float(os.environ.get('TOOTHR', 0.047))
tooth = face & (dax < TR) & (z < -0.115) & (z > -0.43)
lab[tooth] = 4; part[tooth] = 6
# eyes in the carved slits: centre x -0.785, z -0.027, on the head's side
EX, EZ = float(os.environ.get('EX', -0.80)), float(os.environ.get('EZ', -0.022))
side = face & (ay > 0.07) & (N[:, 0] < 0.15) & (x < -0.68)            # sideways or forward, not backward
brow_z = EZ + 0.022 + 0.24 * (x - EX)                     # lower toward the nose: angry
ea = ((x - EX) / 0.07) ** 2 + ((z - EZ) / 0.027) ** 2 < 1
eye = side & ea & (z < brow_z - 0.006)
lab[eye] = 5; part[eye] = 5
pupil = side & ea & (((x - (EX - 0.028)) / 0.022) ** 2 + ((z - EZ + 0.004) / 0.02) ** 2 < 1) & (z < brow_z - 0.006)
lab[pupil] = 6; part[pupil] = 9
brow = side & (np.abs(z - brow_z - 0.006) < 0.011) & (x > EX - 0.075) & (x < EX + 0.07)
lab[brow] = 7; part[brow] = 9
np.save(out, lab); np.save(out.replace('.npy', '_part.npy'), part)
print('head: hat', hat.sum(), 'ear', ear.sum(), 'trim', trim.sum(), 'nose', nose.sum(), 'teeth', tooth.sum(), 'eye', eye.sum(), 'pupil', pupil.sum(), 'brow', brow.sum())
