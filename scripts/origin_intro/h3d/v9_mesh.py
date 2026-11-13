"""v9 mesh edits on the painted graft (vertex order kept, so labels and parts carry over):
- the snout comes forward like a dog's muzzle (Arvind: "it should protrude more, almost like a dog"); the sabres go with it
- a gold nose pad on the tip of the longer muzzle
- the paws are black again (v8 painted everything below CLAWZ white, which read as white paws); real claws are
  separate objects in build_v9.py, placed on the toe tips found here
- the hull's top is a deck: wooden planks (class 8) with dark seams (class 9) inside a black gunwale
python h3d/v9_mesh.py GRAFT.npz LABELS.npy PARTS.npy OUT.npz   (writes OUT.ply, OUT_lab.npy, OUT_part.npy, OUT_toes.json)
Hunyuan frame: the creature faces -X, Z up, mirror plane y = Y0."""
import sys, os, json, numpy as np
gp, lp, pp, out = sys.argv[1:5]
d = dict(np.load(gp)); V = d['V'].astype(float); N = d['N'].astype(float); F = d['F']; src = d['src']
lab = np.load(lp).copy(); part = np.load(pp).copy()
Y0 = -0.015; YC = float(os.environ.get('YC', -0.045))
E = lambda k, v: float(os.environ.get(k, v))
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
x, y, z = V[:, 0].copy(), V[:, 1].copy(), V[:, 2].copy()
H = src == 1
# ---------------- snout
X0, X1 = E('SN_X0', -0.80), E('SN_X1', -0.93)          # stretch starts at the eyes' front, full at the old tip
S = E('SN_LEN', 0.13)                                    # how much longer the muzzle gets
ZT0, ZT1, ZB0, ZB1 = 0.035, 0.075, -0.17, -0.32          # full between ZB0 and ZT0, fading to 0 at ZB1 / ZT1
def field(P):
    """muzzle displacement for points P (n,3): forward, narrower, the top line a little lower"""
    wx = smooth((X0 - P[:, 0]) / (X0 - X1)); zz = P[:, 2]
    wz = np.where(zz > ZT0, 1 - smooth((zz - ZT0) / (ZT1 - ZT0)), np.where(zz < ZB0, 1 - smooth((ZB0 - zz) / (ZB0 - ZB1)), 1.0))
    return wx * wz
def move(P, w):
    Q = P.copy(); Q[:, 0] -= S * w
    Q[:, 1] = YC + (Q[:, 1] - YC) * (1 - E('SN_NARROW', 0.10) * w)
    Q[:, 2] -= E('SN_DROP', 0.012) * w
    return Q
tooth = part == 6
w = np.where(H & ~tooth & (part != 1) & (part != 10), field(V), 0.0)
# the Hunyuan sabres are fused to the chin and come out lumpy: they go (part 12 = dropped in build_v9) and
# build_v9 models clean ones that hang from the moved upper lip
roots = []
for sgn in (1, -1):
    m = tooth & (np.sign(V[:, 1] - YC) == sgn)
    if not m.any(): continue
    P = V[m]; top = P[:, 2].max(); bot = P[:, 2].min()
    r = P[P[:, 2] > top - 0.03].mean(0); b = P[P[:, 2] < bot + 0.02].mean(0)
    r2, = move(r[None], field(r[None])); b2 = b + (r2 - r)
    roots.append(dict(root=r2.tolist(), tip=b2.tolist()))
part[tooth] = 12
# leftovers of the old sabres: the strips fused to the chin, in front of the chin's surface
a0 = np.array([-0.905, 0.163, -0.13]); a1 = np.array([-0.83, 0.18, -0.52])
Pq = np.stack([V[:, 0], np.abs(V[:, 1] - YC), V[:, 2]], 1)
tq = np.clip(((Pq - a0) @ (a1 - a0)) / ((a1 - a0) @ (a1 - a0)), 0, 1)
dax = np.linalg.norm(Pq - (a0 + tq[:, None] * (a1 - a0)), axis=1)
chinx = np.where(V[:, 2] < -0.22, -0.795, -0.84)
left = H & (dax < E('TOOTH_CLEAR', 0.075)) & (V[:, 2] < -0.14) & (V[:, 0] < chinx)
part[left] = 12
w[left] = 0
# the painted eyes were blotchy: paint them over with the face colour; build_v9 sets clean eyes into the slits
eyes = []
EX, EZ = E('EX', -0.80), E('EZ', -0.02)
for sgn in (1, -1):
    # the slit's floor: the head point furthest out along a sideways-forward ray at the eye's height
    od = np.array([-0.45, 0.89 * sgn, 0.0])
    m = H & (np.abs(V[:, 0] - EX) < 0.02) & (np.abs(V[:, 2] - EZ) < 0.015) & (part != 1) & (part != 10) & ((N @ od) > 0.2)
    if not m.any(): continue
    k = np.where(m)[0][((V[m] - np.array([EX, YC, EZ])) @ od).argmax()]
    near = H & (np.linalg.norm(V - V[k], axis=1) < 0.03)
    n = N[near].mean(0); n /= np.linalg.norm(n)
    eyes.append(dict(c=V[k].tolist(), n=n.tolist()))
# the painted hat emblem goes (build_v9 projects a clean one)
hx = np.abs(V[:, 1] - YC)
emb = (part == 10) & (N[:, 0] < -0.3) & (V[:, 0] < -0.6) & (hx < 0.17) & (V[:, 2] > 0.09)
lab[emb] = 1; part[emb] = 1
eb = H & ((part == 5) | (part == 9))
lab[eb] = 0; part[eb] = 0
V = move(V, w)
# ---------------- nose: re-paint on the new tip (gold pad on the top front, as in the drawing)
x, y, z = V[:, 0], V[:, 1] - YC, V[:, 2]; ay = np.abs(y)
face = H & (part != 1) & (part != 10) & (part != 12)
old_nose = part == 7
lab[old_nose] = 0; part[old_nose] = 0
tipx = x[face & (z > -0.06) & (z < 0.04) & (ay < 0.06)].min()
top_at_tip = z[face & (x < tipx + 0.03) & (ay < 0.05)].max()
nose = face & (x < tipx + E('NOSE_D', 0.045)) & (z > top_at_tip - E('NOSE_H', 0.05)) & (ay < E('NOSE_W', 0.05)) & \
       ((N[:, 0] < -0.1) | (N[:, 2] > 0.3))
lab[nose] = 3; part[nose] = 7
# ---------------- paws: black, toe tips for the claws
CLAWZ = E('CLAWZ', -0.79)
white_paw = (lab == 4) & (V[:, 2] < CLAWZ + 0.02) & (part != 12) & (src == 0)
lab[white_paw] = 0; part[white_paw] = 0
toes = {}
PAWS = {'FL': (-0.76, Y0 + 0.45), 'FR': (-0.76, Y0 - 0.45), 'BL': (0.47, Y0 + 0.30), 'BR': (0.47, Y0 - 0.30)}
for n, (cx, cy) in PAWS.items():
    pm = (src == 0) & (V[:, 2] < -0.66) & (np.hypot(V[:, 0] - cx, V[:, 1] - cy) < 0.3)
    P = V[pm]
    if len(P) < 50: continue
    c = P[:, :2].mean(0)
    rel = P[:, :2] - c; ang = np.degrees(np.arctan2(rel[:, 1], -rel[:, 0]))      # 0 = straight ahead (-X)
    rad = np.hypot(rel[:, 0], rel[:, 1])
    bins = np.arange(-80, 81, 4); prof = np.full(len(bins), -1.0); arg = np.zeros(len(bins), int)
    for i, b in enumerate(bins):
        m = np.abs(ang - b) < 2
        if m.any(): k = np.where(m)[0][rad[m].argmax()]; prof[i] = rad[k]; arg[i] = k
    # toe tips = local maxima of the outline's reach, the three best spread at least 24 degrees apart
    cand = [i for i in range(1, len(bins) - 1) if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and prof[i] > 0]
    cand.sort(key=lambda i: -prof[i]); pick = []
    for i in cand:
        if all(abs(bins[i] - bins[j]) >= 24 for j in pick): pick.append(i)
        if len(pick) == 3: break
    tips = []
    for i in sorted(pick, key=lambda i: bins[i]):
        p = P[arg[i]]
        # the claw starts at the toe's front, a little above the sole
        sole = P[np.hypot(P[:, 0] - p[0], P[:, 1] - p[1]) < 0.04][:, 2].min()
        tips.append(dict(p=[float(p[0]), float(p[1]), float(sole + 0.025)], dir=[float(-np.cos(np.radians(bins[i]))), float(np.sin(np.radians(bins[i]))), 0.0]))
    toes[n] = tips
# ---------------- after Arvind's turnaround sheet (2026-11-13)
# gold cuffs: clean bands at the front wrists (no ragged flames)
legs = (src == 0) & (V[:, 2] < -0.44) & (part != 2) & (part != 11)
oldcuff = legs & (lab == 3)
lab[oldcuff] = 0
for cy in (-0.43, 0.43):
    r = np.hypot(V[:, 0] + 0.70, V[:, 1] - cy)
    lab[legs & (r < 0.24) & (V[:, 2] > E('CUFF0', -0.68)) & (V[:, 2] < E('CUFF1', -0.55))] = 3
# hull: no thin gold line and no painted ports; the black spikes with gold feet are modelled (build_v9)
hullp = part == 2
zb = np.interp(V[:, 0], [-0.45, -0.38, -0.3, -0.2, 0.0, 0.7, 0.9], [-0.12, -0.3, -0.37, -0.41, -0.435, -0.435, -0.38])
zt_ = np.interp(V[:, 0], [-0.45, -0.2, 0.0, 0.2, 0.45, 0.7, 0.9], [-0.07, -0.04, 0.01, 0.04, 0.09, 0.1, -0.1])
frh = (V[:, 2] - zb) / np.maximum(zt_ - zb, 0.05)
B0, B1 = 0.36, 0.5
upper_red = hullp & (frh >= B1)
lab[upper_red & ((lab == 3) | (lab == 7))] = 2
spikes = []
for px in [float(v) for v in os.environ.get('SPIKES', '0.10,0.36,0.60').split(',')]:
    for sgn in (1, -1):
        m = hullp & (np.abs(V[:, 0] - px) < 0.025) & (np.abs(frh - E('SPIKE_FR', 0.74)) < 0.06) & (np.sign(V[:, 1] - Y0) == sgn) & (np.abs(N[:, 1]) > 0.3)
        if not m.any(): continue
        k = np.where(m)[0][np.abs(V[m, 1] - Y0).argmax()]
        n = N[m].mean(0); n /= np.linalg.norm(n)
        spikes.append(dict(p=V[k].tolist(), n=n.tolist()))
# gold marks on the flanks, as in the turnaround: a slash behind each front leg and one on each hind thigh
body = (src == 0) & (part == 0) & (np.abs(N[:, 1]) > 0.35)
def tri(px_, pz_, a, b, c):
    """inside the triangle a b c (x, z) points"""
    def s(p1, p2): return (px_ - p2[0]) * (p1[1] - p2[1]) - (p1[0] - p2[0]) * (pz_ - p2[1])
    d1, d2, d3 = s(a, b), s(b, c), s(c, a)
    return ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
mk = tri(V[:, 0], V[:, 2], (-0.47, -0.60), (-0.40, -0.60), (-0.40, -0.44)) | \
     tri(V[:, 0], V[:, 2], (0.30, -0.62), (0.40, -0.60), (0.43, -0.48))
lab[body & mk] = 3
# ---------------- deck on the hull's top
hull = part == 2
up = N[:, 2]
zt = np.interp(V[:, 0], [-0.45, -0.2, 0.0, 0.2, 0.45, 0.7, 0.9], [-0.07, -0.04, 0.01, 0.04, 0.09, 0.1, -0.1])
deck = hull & (up > E('DECK_UP', 0.55)) & (V[:, 2] > -0.12)
# the gunwale: deck points near the deck's edge (top view) stay black, the rest is planks
from scipy import ndimage
R = 0.01; lo = np.array([-0.6, -0.6])
gi = ((V[:, :2] - lo) / R).astype(int)
g = np.zeros((int(1.6 / R) + 2, int(1.2 / R) + 2), bool)
gi = np.clip(gi, 0, np.array(g.shape) - 1)
g[gi[deck, 0], gi[deck, 1]] = True
g = ndimage.binary_closing(g, np.ones((5, 5)))
g = ndimage.binary_fill_holes(g)
dist = ndimage.distance_transform_edt(g) * R
de = dist[gi[:, 0], gi[:, 1]]
GW = E('GUNWALE', 0.035)
plank = deck & (de > GW)
lab[deck] = 0; part[deck] = 11
lab[plank] = 8
seam = plank & (np.abs(((V[:, 1] - Y0) / E('PLANK', 0.07)) - np.round((V[:, 1] - Y0) / E('PLANK', 0.07))) < 0.11)
lab[seam] = 9
# gold rail line on the gunwale's outer edge, where the deck turns down into the hull's side
rail = hull & ~deck & (up > 0.15) & (up <= E('DECK_UP', 0.55)) & (V[:, 2] > -0.12)
lab[rail] = 3; part[rail] = 10
# deck outline for the balustrade in build_v9 (top view, in order around the deck)
import cv2
cs, _ = cv2.findContours(ndimage.binary_erosion(g, np.ones((3, 3)), iterations=2).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
c = max(cs, key=len)[:, 0, :]                            # (col, row) = (y index, x index)
outline = np.stack([c[:, 1] * R + lo[0], c[:, 0] * R + lo[1]], 1)
step = max(1, len(outline) // 90); outline = outline[::step]
ozs = []
for px_, py_ in outline:
    m = deck & (np.hypot(V[:, 0] - px_, V[:, 1] - py_) < 0.05)
    ozs.append(float(V[m, 2].max()) if m.any() else float(np.interp(px_, [-0.45, 0.0, 0.45, 0.9], [-0.06, 0.0, 0.05, 0.02])))
# ---------------- save (normals recomputed from the moved faces)
fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
NN = np.zeros_like(V)
for k in range(3): np.add.at(NN, F[:, k], fn)
NN /= np.maximum(np.linalg.norm(NN, axis=1, keepdims=True), 1e-12)
flip = (NN * N).sum(1) < 0                               # keep the original orientation convention
if flip.mean() > 0.5: NN = -NN
d['N'] = NN.astype(np.float32)
d['V'] = V.astype(np.float32); np.savez_compressed(out, **d)
np.save(out.replace('.npz', '_lab.npy'), lab); np.save(out.replace('.npz', '_part.npy'), part)
json.dump(dict(toes=toes, spikes=spikes, sabres=roots, eyes=eyes, deck=[[float(a), float(b), z_] for (a, b), z_ in zip(outline, ozs)]), open(out.replace('.npz', '_extra.json'), 'w'))
V32 = V.astype('<f4'); N32 = d['N'].astype('<f4')
with open(out.replace('.npz', '.ply'), 'wb') as f:
    f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n'
             'property float nx\nproperty float ny\nproperty float nz\nelement face %d\nproperty list uchar int vertex_indices\n'
             'end_header\n' % (len(V), len(F))).encode())
    f.write(np.concatenate([V32, N32], 1).tobytes())
    fa = np.zeros(len(F), dtype=[('n', 'u1'), ('a', '<i4'), ('b', '<i4'), ('c', '<i4')])
    fa['n'] = 3; fa['a'], fa['b'], fa['c'] = F[:, 0], F[:, 1], F[:, 2]
    f.write(fa.tobytes())
print('spikes', len(spikes), 'cuff', int((lab[legs]==3).sum()), 'marks', int((body & mk).sum()));print('snout moved', int((w > 0.5).sum()), 'sabres', roots, 'eyes', [e['c'] for e in eyes], 'nose', int(nose.sum()), 'white paw ->black', int(white_paw.sum()),
      'deck', int(deck.sum()), 'planks', int(plank.sum()), 'seams', int(seam.sum()), 'rail', int(rail.sum()),
      'toes', {k: len(v) for k, v in toes.items()}, 'outline', len(outline))
