"""Colour the multi-view mesh straight from Arvind's turnaround views, then cut it into parts.
python mv/paint_mv.py MESH.npz VIS4.npy VIEWDIR OUT_PREFIX     -> OUT_lab.npy, OUT_part.npy, OUT_fit.json, OUT_extra.json
mv frame: the creature faces -Y, +X is its left, Z up. Views (mv/prep_views.py, 1024 px, one shared scale):
front.png seen from -Y, side.png from +X (it faces left), back.png from +Y, side_mirror.png from -X.
1. each view is fitted to the mesh's silhouette (scale + offset; the scale is shared)
2. each vertex takes the colour class voted by the views that see it, weighted by how squarely they see it
3. parts by shape and colour: hat, hull (with a planked deck on top), sail, mast, sabres, eyes, nose, claws, stern
Labels (as v9): 0 body 1 hat 2 red 3 gold 4 white 5 eye 6 pupil 7 ink 8 wood 9 seam
Parts: 0 body 1 hat 2 hull 3 sail 4 mast 5 eye 6 tusk 7 nose 8 stern 9 pupil 10 trim 11 deck 13 claw"""
import sys, os, json, numpy as np, cv2
from PIL import Image
from scipy import ndimage
mp, vp, vd, outp = sys.argv[1:5]
d = np.load(mp); V = d['V'].astype(float); N = d['N'].astype(float); F = d['F']
vis = np.load(vp)
E = lambda k, v: float(os.environ.get(k, v))
x, y, z = V.T
VIEWS = [('front', np.array([0, -1, 0]), lambda P: P[:, 0]),
         ('side', np.array([1, 0, 0]), lambda P: P[:, 1]),
         ('back', np.array([0, 1, 0]), lambda P: -P[:, 0]),
         ('side_mirror', np.array([-1, 0, 0]), lambda P: -P[:, 1])]
imgs = {n: np.array(Image.open(os.path.join(vd, n + '.png')).convert('RGB')) for n, *_ in VIEWS}
R = 1024
def sil(a, zz, s, cu, cv, size=256):
    """mesh silhouette in a view, rasterised at size/R of the view"""
    f = size / R
    U = (cu + s * a) * f; W_ = (cv - s * zz) * f
    pts = np.stack([U, W_], 1)[F].round().astype(np.int32)
    m = np.zeros((size, size), np.uint8); cv2.fillPoly(m, list(pts), 1)
    return m > 0
fit = json.load(open(os.environ['FIT'])) if os.environ.get('FIT') else {}
for name, dvec, axis in VIEWS:
    if name in fit: continue
    im = imgs[name]; mask = im.astype(int).sum(-1) < 735
    rows = np.where(mask.any(1))[0]; cols = np.where(mask.any(0))[0]
    a = axis(V)
    s0 = (rows.max() - rows.min()) / (z.max() - z.min())
    best = None
    m256 = cv2.resize(mask.astype(np.uint8), (256, 256), interpolation=cv2.INTER_AREA) > 0
    ZC = E('FITZ', 0.08)                                   # fit on the body only: the sails differ
    s0 = (rows.max() - rows.min()) / (z.max() - z.min())
    for s in s0 * np.linspace(0.90, 1.10, 9):
        cu0 = (cols.min() + cols.max()) / 2 - s * (a.min() + a.max()) / 2
        cv0 = rows.max() + s * z.min()
        for du in range(-30, 31, 6):
            for dv in range(-30, 31, 6):
                sm = sil(a, z, s, cu0 + du, cv0 + dv)
                cut = int(max(0, (cv0 + dv - s * ZC) * 256 / R))
                smc, mc = sm[cut:], m256[cut:]
                iou = (smc & mc).sum() / max((smc | mc).sum(), 1)
                if best is None or iou > best[0]: best = (iou, s, cu0 + du, cv0 + dv)
    fit[name] = dict(iou=float(best[0]), s=float(best[1]), cu=float(best[2]), cv=float(best[3]))
    print(name, 'iou %.3f' % best[0], 'scale %.1f' % best[1])
json.dump(fit, open(outp + '_fit.json', 'w'), indent=1)
# ---- colour classes from the drawing's colours
PROTO = {0: [(22, 20, 20), (40, 38, 40), (62, 60, 64), (88, 86, 92)],                # black body (with its grey light)
         2: [(150, 32, 30), (115, 24, 26), (180, 52, 46), (85, 20, 22), (200, 80, 70)],  # red
         3: [(226, 176, 46), (192, 140, 32), (242, 212, 112), (152, 104, 26), (210, 170, 80)],  # gold
         4: [(240, 240, 236), (214, 214, 208), (186, 186, 180), (160, 158, 150)],      # white
         8: [(100, 64, 38), (76, 48, 32), (126, 88, 56)]}                            # wood (masts)
pk = []; pc = []
for c, lst in PROTO.items():
    for p in lst: pk.append(p); pc.append(c)
pk = np.array(pk, float); pc = np.array(pc)
votes = np.zeros((len(V), 10))
for k, (name, dvec, axis) in enumerate(VIEWS):
    im = cv2.medianBlur(imgs[name], 3).astype(float); f = fit[name]
    u = f['cu'] + f['s'] * axis(V); v = f['cv'] - f['s'] * z
    ui = np.clip(u.round().astype(int), 0, R - 1); vi = np.clip(v.round().astype(int), 0, R - 1)
    col = im[vi, ui]
    white_bg = col.sum(-1) > 745                          # off the drawing (silhouette mismatch): no vote
    cls = pc[np.argmin(((col[:, None, :] - pk[None]) ** 2).sum(-1), 1)]
    w = np.clip(N @ dvec, 0, 1) ** 2 * vis[:, k] * ~white_bg
    np.add.at(votes, (np.arange(len(V)), cls), w)
lab = votes.argmax(1)
lab[votes.sum(1) == 0] = 0
# vertices no view saw: take the most common label of their neighbours (a few rounds)
nov = votes.sum(1) == 0
E_ = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
for it in range(12):
    if not nov.any(): break
    cnt = np.zeros((len(V), 10)); src_ok = ~nov[E_[:, 1]]
    np.add.at(cnt, (E_[src_ok, 0], lab[E_[src_ok, 1]]), 1)
    fill = nov & (cnt.sum(1) > 0); lab[fill] = cnt[fill].argmax(1); nov &= ~fill
# ---- parts
part = np.zeros(len(V), int)
ay = np.abs(x)
HATZ = E('HATZ', 0.13)
head = (y < -0.42) & (z > -0.38)
hat = (y < -0.22) & (z > HATZ) & ~((lab == 4) & (y > -0.1))
part[hat] = 1
lab[hat & (lab == 0)] = 1
part[hat & (lab == 3)] = 10
# masts and sails: behind the hat, above the shell
rig_ = (y > -0.25) & (z > 0.05) & ~hat
MX, MY = [float(t) for t in os.environ.get('MAST_XY', '-0.05,0.43').split(',')]
mast = np.zeros(len(V), bool); axis_pts = []
ax_ = np.array([MX, MY]); MR = E('MAST_R', 0.035)
for z0 in np.arange(0.0, z.max() + 0.02, 0.02):
    sl = rig_ & (z >= z0) & (z < z0 + 0.02)
    near = sl & (np.hypot(x - ax_[0], y - ax_[1]) < 0.06) & (np.abs(N[:, 1]) < 0.75) & (np.abs(N[:, 2]) < 0.7)
    if near.sum() >= 3: ax_ = 0.5 * ax_ + 0.5 * np.array([x[near].mean(), y[near].mean()])
    mast |= sl & (np.hypot(x - ax_[0], y - ax_[1]) < MR)
    axis_pts.append([float(ax_[0]), float(ax_[1]), float(z0 + 0.01)])
sail = rig_ & ~mast
lab[sail & (z < E('FLAGZ', 0.62))] = 4
part[sail] = 3; part[mast] = 4
lab[mast & (lab != 3)] = 8                                    # masts are wood (the flag's gold stays)
# hull: the shell between the head and the stern, above its lower edge (lowest red in each slice, minus the rim)
shell = (y > -0.52) & (y < 0.66) & ~hat & ~rig_
zb = np.full(len(V), 9.0)
for y0 in np.arange(-0.55, 0.7, 0.04):
    m = shell & (np.abs(y - y0) < 0.03) & (lab == 2)
    if m.sum() > 10:
        zz = np.percentile(z[m], 2); zb[np.abs(y - y0) < 0.02] = zz - E('RIM', 0.035)
zb = ndimage.minimum_filter1d(zb, 1)
hull = shell & (z > zb)
part[hull] = 2
# deck: the shell's top that faces up, inside its rim -> planks
top = hull & (N[:, 2] > E('DECK_UP', 0.6)) & (z > E('DECK_Z', -0.08))
part[top] = 11; lab[top] = 8
PL = E('PLANK', 0.06)
seam = top & (np.abs(x / PL - np.round(x / PL)) < 0.12)
lab[seam] = 9
# sabres: white below the muzzle at the front
tusk = (y < -0.8) & (z < 0.0) & (z > -0.42) & (lab == 4)              # not the white toe tips
part[tusk] = 6
# eyes: white on the side of the head under the hat brim; dark inside them = pupil
eyeb = head & (y > -0.82) & (y < -0.5) & (z > -0.08) & (z < HATZ + 0.02) & (ay > 0.08)
eye = eyeb & (lab == 4)
lab[eyeb & np.isin(lab, [4, 5, 6])] = 0
if False:
    for sgn in (1, -1):
        m = eye & (np.sign(x) == sgn)
        if not m.any(): continue
        c = V[m].mean(0); r = np.ptp(V[m], 0) / 2 + 0.01
        inside = eyeb & (np.sign(x) == sgn) & ((((V - c) / np.maximum(r, 0.01)) ** 2).sum(1) < 1)
        pup = inside & (lab == 0)
        part[pup] = 9; lab[pup] = 6
# nose: gold on the muzzle's front top
nose = (y < -0.86) & (z > -0.06) & (lab == 3) & ~hat
part[nose] = 7
# claws: white at the paws
claw = (z < E('CLAWZ', -0.58)) & (lab == 4)
lab[claw] = 0
toes = {}
for n_, (cx, cy) in dict(FL=(0.32, -0.6), FR=(-0.32, -0.6), BL=(0.29, 0.42), BR=(-0.29, 0.42)).items():
    pm = (z < -0.6) & (np.hypot(x - cx, y - cy) < 0.22)
    P = V[pm]
    if len(P) < 50: continue
    c = P[:, :2].mean(0); rel = P[:, :2] - c
    ang = np.degrees(np.arctan2(rel[:, 0], -rel[:, 1]))          # 0 = straight ahead (-Y)
    rad = np.hypot(rel[:, 0], rel[:, 1])
    bins = np.arange(-80, 81, 4); prof = np.full(len(bins), -1.0); arg = np.zeros(len(bins), int)
    for i, b in enumerate(bins):
        m = np.abs(ang - b) < 2
        if m.any(): k = np.where(m)[0][rad[m].argmax()]; prof[i] = rad[k]; arg[i] = k
    cand = [i for i in range(1, len(bins) - 1) if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and prof[i] > 0]
    cand.sort(key=lambda i: -prof[i]); pick = []
    for i in cand:
        if all(abs(bins[i] - bins[j]) >= 20 for j in pick): pick.append(i)
        if len(pick) == int(E('NCLAW', 4 if n_[0] == 'F' else 3)): break
    tips = []
    for i in sorted(pick, key=lambda i: bins[i]):
        p_ = P[arg[i]]; a_ = np.radians(bins[i])
        tips.append(dict(p=p_.tolist(), dir=[float(np.sin(a_)), float(-np.cos(a_)), 0.0]))
    toes[n_] = tips
# stern ornament: the gold piece (and what it holds) behind the shell
stern = (y > E('STERNY', 0.55)) & (z > -0.62) & ~rig_ & ((lab == 3) | (y > 0.72))
part[stern] = 8
lab[stern] = 3                                              # the stern ornament is all gold (its dark lines are ink, not paint)
# ---- clean shapes where the drawing's colours cannot land exactly (v9 lesson: a steady hand)
lab[mast] = 8                                                  # masts: wood all the way up
flag = rig_ & ~mast & (z >= E('FLAGZ', 0.62)); lab[flag] = 4; part[flag] = 14
# sabres: white along their own axis below the muzzle (the front view's white lands on them only roughly)
SB = [float(t) for t in os.environ.get('SABRE', '0.10,-0.94,-0.03,0.095,-0.93,-0.34').split(',')]
for sgn in (1, -1):
    a0 = np.array([SB[0] * sgn, SB[1], SB[2]]); a1 = np.array([SB[3] * sgn, SB[4], SB[5]])
    t_ = np.clip(((V - a0) @ (a1 - a0)) / ((a1 - a0) @ (a1 - a0)), 0, 1)
    dd = np.linalg.norm(V - (a0 + t_[:, None] * (a1 - a0)), axis=1)
    sab = (dd < E('SABRE_R', 0.04)) & (y < -0.8) & ~hat
    lab[sab] = 4; part[sab] = 6
# the gold nose on the muzzle's top front (turnaround: front view), by shape
tipy = y[(z > 0.0) & (z < 0.15) & (np.abs(x) < 0.06)].min()
nz_ = (y < tipy + E('NOSE_D', 0.05)) & (z > E('NOSE_Z', 0.055)) & (np.abs(x) < E('NOSE_W', 0.045)) & ~hat & (N[:, 2] > -0.2)
lab[nz_] = 3; part[nz_] = 7
# hat: black, with a gold rim where the thin brim turns over (crown top excluded); its emblem is drawn in build_v10
lab[hat] = 1; part[hat] = 1
from scipy.spatial import cKDTree
hi = np.where(hat)[0]; tr = cKDTree(V[hi]); RR = E('RIMR', 0.03)
rim = np.zeros(len(V), bool)
for k, nb in enumerate(tr.query_ball_point(V[hi], RR)):
    if len(nb) > 1 and (N[hi[nb]] @ N[hi[k]]).min() < -0.25: rim[hi[k]] = True
crown = hat & (z > E('CROWNZ', 0.34)) & (np.abs(x) < 0.2)
# the brim's outer edge seen from above (a thick brim has no turn-over to find)
S_ = 500; lo_ = np.array([-0.6, -1.1])
hx = ((x - lo_[0]) * S_ / 1.2).astype(int); hy = ((y - lo_[1]) * S_ / 1.2).astype(int)
mm = np.zeros((S_, S_), np.uint8); mm[np.clip(hy[hat], 0, S_ - 1), np.clip(hx[hat], 0, S_ - 1)] = 1
mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
mm = ndimage.binary_fill_holes(mm).astype(np.uint8)
dist = ndimage.distance_transform_edt(mm) * 1.2 / S_
dv_ = dist[np.clip(hy, 0, S_ - 1), np.clip(hx, 0, S_ - 1)]
cz = np.full((S_ // 5 + 1, S_ // 5 + 1), -9.0)
ci, cj = np.clip(hy // 5, 0, S_ // 5), np.clip(hx // 5, 0, S_ // 5)
np.maximum.at(cz, (ci[hat], cj[hat]), z[hat])
rim |= hat & (dv_ < E('TRIM', 0.022)) & (z > cz[ci, cj] - E('TRIMH', 0.02)) & (N[:, 2] > 0.1)
edge = []
cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
if cs:
    c = max(cs, key=len)[:, 0, :]
    for cx_, cy_ in c[::max(1, len(c) // 120)]:
        px_, py_ = cx_ * 1.2 / S_ + lo_[0], cy_ * 1.2 / S_ + lo_[1]
        m = hat & (np.hypot(x - px_, y - py_) < 0.03)
        if m.any(): k = np.where(m)[0][z[m].argmax()]; edge.append([float(px_), float(py_), float(z[k])])
# white only where the design has it on the mesh (sails, flag, sabres); elsewhere it is drawing bleed (e.g. the sabres
# projected onto the chest behind them); claws and eyes are modelled
stray_white = (lab == 4) & ~np.isin(part, [3, 6, 14])
lab[stray_white] = 0
# ---- the deck's outline for a rail (top view, in order around)
R_ = 0.01; lo = np.array([-0.6, -0.7])
gi = np.clip(((V[:, :2] - lo) / R_).astype(int), 0, [int(1.2 / R_), int(1.6 / R_)])
g = np.zeros((int(1.2 / R_) + 2, int(1.6 / R_) + 2), bool)
g[gi[top, 0], gi[top, 1]] = True
g = ndimage.binary_fill_holes(ndimage.binary_closing(g, np.ones((5, 5))))
outline = []
if g.any():
    cs, _ = cv2.findContours(g.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :]
    pts = np.stack([c[:, 1] * R_ + lo[0], c[:, 0] * R_ + lo[1]], 1)[::max(1, len(c) // 90)]
    for px_, py_ in pts:
        m = hull & (np.hypot(V[:, 0] - px_, V[:, 1] - py_) < 0.04)
        outline.append([float(px_), float(py_), float(V[m, 2].max()) if m.any() else 0.0])
np.save(outp + '_lab.npy', lab); np.save(outp + '_part.npy', part)
json.dump(fit, open(outp + '_fit.json', 'w'), indent=1)
json.dump(dict(deck=outline, toes=toes, hat_edge=edge, mast_axis=axis_pts), open(outp + '_extra.json', 'w'))
print('labels', np.bincount(lab, minlength=10), 'parts', np.bincount(part, minlength=14), 'deck outline', len(outline))
