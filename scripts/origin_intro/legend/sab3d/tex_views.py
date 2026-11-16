"""Sabertann's film model painted with Arvind's own turnaround (2026-11-16, Arvind: "do what you did with Gravriel's
model, since that turned out really good"). Gravriel's film model got its look from his turnaround projected onto the
model as a painted 8-bpp texture; this does the same for Sabertann's approved low-poly (pt19r: shape, rig and run kept).
  - views: mv/views/front.png (seen from -Y), side.png (from +X, he faces left), back.png (from +Y); the right flank uses
    the side view too (side_mirror.png is the side view mirrored, the design is symmetric). Each view is fitted to the
    model's silhouette (scale + offset, best IoU), in the ART positions: parts the export moved are moved back first
    (stern skull: -SHIFT y / +LIFT z then 1.35x about the skull; mast, sail, flag: MASTFWD forward, 0.2 up)
  - each face takes the view that sees it best (visible share from a z-buffer x facing), so the chest under the head does
    not get the tusks. Where the model differs from the drawing, RENDERED views of the model with v30's approved flat
    textures (BASE_tex{g}.png) are used instead: the stern skull (Arvind's later wish; the drawing has a gold fin there),
    faces of other parts that fall on the drawn fin, and faces no drawing sees squarely (shell top, deck, hat crown:
    top view). Sail and flag keep their old texture (sail picture)
  - textures (8 bpp, 256 colours each, own palette); layouts 'sky2' (sky shot) and 'mid2' (pagoda shot). The film's
    texture VRAM is 256 KB for the sky and the pagoda scene together (measured 2026-11-16: declared TEX0 texture data
    261904 bytes worked, 263376 failed = the pagoda drew white); Origin's two scenes use 215568, so ours may add ~46 KB
python tex_views.py BASE VIEWDIR OUT      (BASE = sab3d/pt19r: BASE.json + BASE_tex{0,1,2}.png)
env: LAYOUT (sky|mid|big), VIS_RES (512), TOPW (0.7: top view weight), REND_SRC (tex|albedo)"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
BASE, VD, OUT = sys.argv[1:4]
E = lambda k, d: float(os.environ.get(k, d))
J = json.load(open(BASE + '.json')); P = J['polys']
# the drawn decals (eyes, brows, mouth, hat emblem) are in the painting now; dropped, they free shape room (the painted
# faces need a TEXCOORD per vertex, Ho-Oh's shapes have a fixed size)
DROP = set(x for x in os.environ.get('DROP_PARTS', 'Eye,Brow,Mouth,Emblem').split(',') if x); P = [p for p in P if p.get('part', '') not in DROP]; NF = len(P)
V = np.array([p['p'] for p in P], float)                          # NF x 3 x 3 (bind pose, Blender frame: faces -Y, +X left, Z up)
SHIFT, LIFT, MASTFWD, STERNSCALE = 0.8, 0.7, 0.7, 1.35            # export_parts7 args (pt19 = "0.8 0.7 0.7 1.35")
STERN = ('Stern', 'Skull', 'SkNose', 'EyeHole', 'EyeRim', 'Tooth')
part = [p.get('part', '') for p in P]
A = V.copy()                                                      # ART positions
sk = [i for i in range(NF) if part[i] == 'SkullHead']; SC = V[sk].reshape(-1, 3).mean(0)
for i in range(NF):
    if part[i].startswith(STERN): A[i] = SC + (V[i] - SC) / STERNSCALE + np.array([0, SHIFT, -LIFT])
    elif part[i] in ('Mast', 'Sail', 'Flag'): A[i] = V[i] + np.array([0, MASTFWD, -0.2])
OLD = set(x for x in os.environ.get('OLD_PARTS', 'Sail,Flag').split(',') if x)
# views: name, toward-viewer direction, image axes (u from a, v from z)
VIEWS = {'front': (np.array([0, -1.0, 0]), lambda Q: Q[..., 0]), 'side': (np.array([1.0, 0, 0]), lambda Q: Q[..., 1]),
         'back': (np.array([0, 1.0, 0]), lambda Q: -Q[..., 0])}
IMG = {n: np.asarray(Image.open(os.path.join(VD, n + '.png')).convert('RGB')).astype(float) for n in VIEWS}
R = 1024
def figmask(im): return im.min(-1) < 250                          # the views are on pure white (mv/prep_views.py)
def silhouette(Q, s, cu, cv, size, sel=None):
    f = size / R; m = Image.new('L', (size, size), 0); dr = ImageDraw.Draw(m)
    for i in (range(NF) if sel is None else sel):
        q = Q[i]; dr.polygon([((cu + s * a) * f, (cv - s * z) * f) for a, z in q], fill=1)
    return np.asarray(m) > 0
FIT = {}
for n, (dv, ax) in VIEWS.items():
    M = figmask(IMG[n]); M = ndimage.binary_opening(M, iterations=2); m256 = np.asarray(Image.fromarray(M.astype(np.uint8) * 255).resize((256, 256), Image.BILINEAR)) > 127
    sel = [i for i in range(NF) if not (n == 'front' and part[i] in ('Mast', 'Sail', 'Flag'))]   # the front drawing shows no mast
    Q = np.stack([ax(A), A[..., 2]], -1)                          # NF x 3 x 2 (a, z)
    qa = Q[sel].reshape(-1, 2); ys, xs = np.nonzero(M)
    s0 = (ys.max() - ys.min()) / (qa[:, 1].max() - qa[:, 1].min())
    cu0 = (xs.max() + xs.min()) / 2 - s0 * (qa[:, 0].max() + qa[:, 0].min()) / 2; cv0 = ys.max() + s0 * qa[:, 1].min()
    best = (-1, s0, cu0, cv0)
    for rng, st in ((0.12, 0.03), (0.04, 0.01), (0.012, 0.003)):
        _, sb, cub, cvb = best
        for ds in np.arange(-rng, rng + 1e-9, st):
            s = sb * (1 + ds)
            for du in np.arange(-rng * 400, rng * 400 + 1e-9, st * 400):
                for dw in np.arange(-rng * 400, rng * 400 + 1e-9, st * 400):
                    sm = silhouette(Q, s, cub + du, cvb + dw, 256, sel); iou = (sm & m256).sum() / max(1, (sm | m256).sum())
                    if iou > best[0]: best = (iou, s, cub + du, cvb + dw)
    FIT[n] = dict(iou=float(best[0]), s=float(best[1]), cu=float(best[2]), cv=float(best[3])); print('fit', n, {k: round(v, 3) for k, v in FIT[n].items()})
    # the background takes the nearest figure colour (no white bleeding at the silhouette)
    core = ndimage.binary_erosion(M, iterations=3); _, (iy, ix) = ndimage.distance_transform_edt(~core, return_indices=True); IMG[n] = IMG[n][iy, ix]
# ---- rendered views: the real model (V positions) with v30's flat textures, for the parts the drawing does not show
RSRC = os.environ.get('REND_SRC', 'tex')
ALB = {g: np.asarray(Image.open(f'{BASE}_{"albedo" if RSRC == "albedo" else "tex"}{g}.png').convert('RGB')).astype(float) for g in (0, 1, 2)}
UVO = np.array([p['uv'] for p in P], float); GO = np.array([p['g'] for p in P])
def raster(Q2, depth, size, col_fn=None):
    """Q2: NF x 3 x 2 pixel coords, depth: NF x 3 (larger = nearer). Returns z-buffer, face id buffer, colour image."""
    zb = np.full((size, size), -1e9); fb = np.full((size, size), -1, int); img = np.zeros((size, size, 3))
    for i in range(NF):
        q = Q2[i]; x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax_, ay_), (bx, by), (cx, cy) = q; den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay_ - cy)
        if abs(den) < 1e-9: continue
        l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; l1 = ((cy - ay_) * (gx - cx) + (ax_ - cx) * (gy - cy)) / den; l2 = 1 - l0 - l1
        ins = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
        if not ins.any(): continue
        z = l0 * depth[i, 0] + l1 * depth[i, 1] + l2 * depth[i, 2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z > sub)
        sub[upd] = z[upd]; fb[y0:y1 + 1, x0:x1 + 1][upd] = i
        if col_fn is not None:
            c = col_fn(i, l0[upd], l1[upd], l2[upd]); img[y0:y1 + 1, x0:x1 + 1][upd] = c
    return zb, fb, img
def alb_col(i, l0, l1, l2):
    uv = l0[:, None] * UVO[i, 0] + l1[:, None] * UVO[i, 1] + l2[:, None] * UVO[i, 2]; a_ = ALB[GO[i]]; h, w = a_.shape[:2]
    x = np.clip((uv[:, 0] * w).astype(int), 0, w - 1); y = np.clip(((1 - uv[:, 1]) * h).astype(int), 0, h - 1); return a_[y, x]
RR = int(E('REND_RES', 512)); allv = V.reshape(-1, 3)
LAYOUT = os.environ.get('LAYOUT', 'big'); TOP_LAND = LAYOUT in ('sky', 'sky2', 'mid', 'mid2', 'pag')
def ortho(ua, va, land=False):
    """fit two model axes into an RR x RR picture; returns q(Q3) -> pixel coords"""
    a_, b_ = ua(allv), va(allv); s_ = 0.92 * RR / max(np.ptp(a_), np.ptp(b_))
    c0 = RR / 2 - s_ * (a_.max() + a_.min()) / 2; c1 = RR / 2 - s_ * (b_.max() + b_.min()) / 2
    return lambda Q3: np.stack([c0 + s_ * ua(Q3), c1 + s_ * va(Q3)], -1)
# name: (toward-viewer direction, pixel mapping, depth); the right flank uses the side picture mirrored (symmetric model)
RV = {'top': (np.array([0, 0, 1.0]), ortho((lambda Q: Q[..., 1]) if TOP_LAND else (lambda Q: Q[..., 0]), (lambda Q: Q[..., 0]) if TOP_LAND else (lambda Q: Q[..., 1]))),
      'rback': (np.array([0, 1.0, 0]), ortho(lambda Q: -Q[..., 0], lambda Q: -Q[..., 2])),
      'rside': (np.array([1.0, 0, 0]), ortho(lambda Q: Q[..., 1], lambda Q: -Q[..., 2]))}
RIMG = {}
for n, (dv, qf) in RV.items():
    _, fb_, im_ = raster(qf(V), V @ dv, RR, alb_col); m_ = fb_ >= 0; _, (iy, ix) = ndimage.distance_transform_edt(~m_, return_indices=True); RIMG[n] = im_[iy, ix]
# ---- visibility per view
VR = int(E('VIS_RES', 512))
def normals(X):
    nr = np.cross(X[:, 1] - X[:, 0], X[:, 2] - X[:, 0]); nr = nr / np.maximum(np.linalg.norm(nr, axis=1), 1e-12)[:, None]
    vn = np.array([np.mean(p['n'], 0) if 'n' in p else [0, 0, 0] for p in P]); nr[np.einsum('ij,ij->i', nr, vn) < 0] *= -1; return nr
nrmA = normals(A); nrmV = normals(V)
BARY = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1 / 3, 1 / 3, 1 / 3], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]])
SCORE = {}; PIX = {}
def face_samples(Q2, depth):
    pts = np.einsum('kj,ijd->ikd', BARY, Q2); dz = np.einsum('kj,ij->ik', BARY, depth); return pts, dz
isstern = np.array([part[i].startswith(STERN) for i in range(NF)])
for n, (dv, ax) in list(VIEWS.items()) + [('side_m', (np.array([-1.0, 0, 0]), lambda Q: Q[..., 1]))]:
    vk = 'side' if n == 'side_m' else n; f_ = FIT[vk]; k = VR / R
    Q2 = np.stack([(f_['cu'] + f_['s'] * ax(A)) * k, (f_['cv'] - f_['s'] * A[..., 2]) * k], -1); depth = A @ dv
    zb, fb, _ = raster(Q2, depth, VR); pts, dz = face_samples(Q2, depth)
    xi = np.clip(pts[..., 0].astype(int), 0, VR - 1); yi = np.clip(pts[..., 1].astype(int), 0, VR - 1)
    vis = (dz >= zb[yi, xi] - 0.06).mean(1); cosv = np.clip(nrmA @ dv, 0, 1)
    # the drawn stern (a gold fin) where the art-position stern lies in this view: not for other parts' faces
    fin = np.zeros((VR, VR), bool); fin[fb >= 0] = isstern[fb[fb >= 0]]; fin = ndimage.binary_dilation(fin, iterations=int(E('FIN_GROW', 6)))
    onfin = fin[yi, xi].mean(1) > 0.3
    sc_ = vis * cosv; sc_[isstern] = 0; sc_[onfin & ~isstern] *= E('FIN_PENALTY', 0.0)
    SCORE[n] = sc_; PIX[n] = np.stack([(f_['cu'] + f_['s'] * ax(A)), (f_['cv'] - f_['s'] * A[..., 2])], -1)   # 1024-px coords
for n, (dv, qf) in RV.items():
    Q2 = qf(V); zb, fb, _ = raster(Q2, V @ dv, RR); pts, dz = face_samples(Q2, V @ dv)
    xi = np.clip(pts[..., 0].astype(int), 0, RR - 1); yi = np.clip(pts[..., 1].astype(int), 0, RR - 1)
    sc_ = (dz >= zb[yi, xi] - 0.06).mean(1) * np.clip(nrmV @ dv, 0, 1) * (E('TOPW', 0.7) if n == 'top' else E('RENDW', 0.5))
    sc_[isstern] = sc_[isstern] / (E('RENDW', 0.5) if n != 'top' else E('TOPW', 0.7)) + 0.01   # the stern only from these
    SCORE[n] = sc_; PIX[n] = Q2
# the right flank of a rendered side: mirrored picture (u from y, the model is symmetric)
dv = np.array([-1.0, 0, 0]); qf = RV['rside'][1]; Q2 = qf(V); zb, fb, _ = raster(Q2, V @ dv, RR); pts, dz = face_samples(Q2, V @ dv)
xi = np.clip(pts[..., 0].astype(int), 0, RR - 1); yi = np.clip(pts[..., 1].astype(int), 0, RR - 1)
sc_ = (dz >= zb[yi, xi] - 0.06).mean(1) * np.clip(nrmV @ dv, 0, 1) * E('RENDW', 0.5); sc_[isstern] = sc_[isstern] / E('RENDW', 0.5) + 0.01
SCORE['rside_m'] = sc_; PIX['rside_m'] = Q2
names = ['front', 'side', 'back', 'side_m', 'top', 'rback', 'rside', 'rside_m']; S = np.stack([SCORE[k] for k in names], 1); choice = S.argmax(1)
for i in range(NF):                                                # the thin mast: from the back view (keeps the sail out of the side texture)
    if part[i] == 'Mast': choice[i] = 2
from collections import Counter
print('faces per view', Counter(names[c] for c in choice), 'old', sum(1 for i in range(NF) if part[i] in OLD))
# ---- atlases: (texture, x0, y0, w, h) per picture
TS = {0: (256, 128), 1: (128, 128), 2: (128, 64)}
LAY = {'side': (0, 0, 0, 192, 128), 'top': (0, 192, 0, 64, 128), 'front': (1, 0, 0, 128, 128), 'back': (2, 0, 0, 64, 64), 'old': (2, 64, 0, 32, 64), 'rback': (2, 96, 0, 32, 32), 'rside': (2, 96, 32, 32, 32)}
if LAYOUT == 'sky':                                                # 40 KB: the close fly-by, front 128x128
    TS = {0: (128, 128), 1: (128, 128), 2: (128, 64)}
    LAY = {'side': (0, 0, 0, 128, 88), 'top': (0, 0, 88, 128, 40), 'front': (1, 0, 0, 128, 128), 'back': (2, 0, 0, 32, 64), 'old': (2, 32, 0, 32, 64), 'rback': (2, 64, 0, 32, 32), 'rside': (2, 64, 32, 64, 32)}
elif LAYOUT == 'mid':                                              # 28 KB: the pagoda shot, seen from behind
    TS = {0: (128, 128), 1: (128, 64), 2: (64, 64)}
    LAY = {'side': (0, 0, 0, 128, 88), 'top': (0, 0, 88, 128, 40), 'front': (1, 0, 0, 64, 64), 'back': (1, 64, 0, 64, 64), 'old': (2, 0, 0, 32, 64), 'rback': (2, 32, 0, 32, 32), 'rside': (2, 32, 32, 32, 32)}
elif LAYOUT == 'sky2':                                             # 28 KB, sky shot (sky + pagoda textures <= 256 KB VRAM)
    TS = {0: (128, 128), 1: (128, 64), 2: (64, 64)}
    LAY = {'side': (0, 0, 0, 128, 88), 'top': (0, 0, 88, 128, 40), 'front': (1, 0, 0, 64, 64), 'rback': (1, 64, 0, 32, 32), 'rside': (1, 64, 32, 64, 32), 'back': (2, 0, 0, 32, 64), 'old': (2, 32, 0, 32, 64)}
elif LAYOUT == 'mid2':                                             # 26 KB, pagoda: head faces in one texture (shape placement)
    TS = {0: (128, 128), 1: (128, 64), 2: (32, 64)}
    LAY = {'side': (0, 0, 0, 128, 88), 'front': (0, 0, 88, 40, 40), 'top': (0, 40, 88, 88, 40), 'back': (1, 0, 0, 64, 64), 'rback': (1, 64, 0, 32, 32), 'rside': (1, 64, 32, 64, 32), 'old': (2, 0, 0, 32, 64)}
def region(img, pix_sel, x0, y0, w, h):
    """crop img to the bounding box of the chosen faces' pixels (+ margin), scale uniformly into (x0,y0,w,h)"""
    p = pix_sel.reshape(-1, 2); lo = p.min(0) - 6; hi = p.max(0) + 6; bw, bh = hi - lo; sc = min(w / bw, h / bh)
    ox = x0 + (w - bw * sc) / 2 - lo[0] * sc; oy = y0 + (h - bh * sc) / 2 - lo[1] * sc
    PADS = 512; big = Image.fromarray(np.pad(np.clip(img, 0, 255).astype(np.uint8), ((PADS, PADS), (PADS, PADS), (0, 0)), mode='edge'))
    cx0, cy0 = (x0 - ox) / sc + PADS, (y0 - oy) / sc + PADS
    part_img = big.resize((w, h), Image.BOX, box=(cx0, cy0, cx0 + w / sc, cy0 + h / sc))
    return np.asarray(part_img).astype(float), (sc, ox, oy)
oldm = np.array([part[i] in OLD for i in range(NF)])
KEYOF = {'front': 'front', 'side': 'side', 'side_m': 'side', 'back': 'back', 'top': 'top', 'rback': 'rback', 'rside': 'rside', 'rside_m': 'rside'}
TEX = {g: np.zeros((h, w, 3)) for g, (w, h) in TS.items()}; MAP = {}
SRCIMG = {'front': IMG['front'], 'side': IMG['side'], 'back': IMG['back'], 'top': RIMG['top'], 'rback': RIMG['rback'], 'rside': RIMG['rside']}
for key in ('side', 'front', 'back', 'top', 'rback', 'rside'):
    sel_ = np.array([KEYOF[names[c]] == key for c in choice]) & ~oldm
    if not sel_.any(): continue
    pix_ = np.concatenate([PIX[nm][sel_ & (np.array(names)[choice] == nm)] for nm in names if KEYOF[nm] == key])
    g, x0, y0, w, h = LAY[key]; im_, MAP[key] = region(SRCIMG[key], pix_, x0, y0, w, h); TEX[g][y0:y0 + h, x0:x0 + w] = im_
OLDIMG = np.asarray(Image.open(f'{BASE}_albedo2.png').convert('RGB')).astype(float)
g, x0, y0, w, h = LAY['old']; TEX[g][y0:y0 + h, x0:x0 + w] = np.asarray(Image.fromarray(OLDIMG.astype(np.uint8)).resize((w, h), Image.BOX)).astype(float)
def quant(a, n=256):
    q = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:3 * n]).reshape(-1, 3); return np.asarray(q).astype(np.uint8), pal
out = []
for i, p in enumerate(P):
    q = dict(p)
    if oldm[i]:                                                   # old sail/flag picture: old uv into its region
        g, x0, y0, w, h = LAY['old']; Wg, Hg = TS[g]
        q['uv'] = [[(x0 + u * w) / Wg, 1 - (y0 + (1 - v) * h) / Hg] for u, v in p['uv']]; q['g'] = g
    else:
        c = names[choice[i]]; key = KEYOF[c]; sc, ox, oy = MAP[key]
        px = PIX[c][i]; gx = ox + px[:, 0] * sc; gy = oy + px[:, 1] * sc
        g = LAY[key][0]; Wg, Hg = TS[g]
        q['uv'] = [[float(np.clip(x / Wg, 0.002, 0.998)), float(np.clip(1 - y / Hg, 0.002, 0.998))] for x, y in zip(gx, gy)]; q['g'] = g
    q['view'] = 'old' if oldm[i] else names[choice[i]]; out.append(q)
json.dump(dict(J, polys=out, fit=FIT, layout=LAYOUT), open(OUT + '.json', 'w'))
for g, T in TEX.items():
    ix, pal = quant(T); np.save(f'{OUT}_tex{g}_idx.npy', ix); np.save(f'{OUT}_tex{g}_pal.npy', pal)
    Image.fromarray(pal[ix].astype(np.uint8)).save(f'{OUT}_tex{g}.png'); print('tex', g, ix.shape, 'colours', len(np.unique(ix)))
print('polys', len(out), 'texture KB', sum(w * h for w, h in TS.values()) // 1024)
