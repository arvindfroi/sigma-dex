"""Gravriel v4: the intro sprite drawn from his front view (grav/views/front.png, the Qwen turnaround of Arvind's design)
instead of the 3D render. He only rises straight up and stares, so a 2D picture keeps the design's face and hat exactly.
python grav/grav2d.py OUTDIR        -> OUTDIR/p{pose}_{eyes}.png (palette index images), pal.json, preview.png, head.png
Poses: sway phases of the beard, rags and arms. The picture is warped at full size, then shrunk, so all poses match.
The head (hat, mask, beak) never moves inside the picture, so its tiles are shared by every pose and eye state.
Eyes: drawn per pixel like the concept art (round, heavy outward-drooping lids, white, cyan iris, dark pupil) and
pasted over the shrunk face: closed, half, open looking down-left, open staring at the camera, staring with a glint.
Colours: graded into the scene's night fog, a moonlit rim on the hat and shoulders, fixed tones for the mask, beak and
eyes, k-means for the rest; one 15-colour palette shared by everything."""
import sys, os, json
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
SC = float(os.environ.get('G2_SCALE', 0.22))
POSES = int(os.environ.get('G2_POSES', 3))
src = np.asarray(Image.open(os.path.join(HERE, 'views', 'front.png')).convert('RGB')).astype(np.float32)
Hs, Ws = src.shape[:2]
yy, xx = np.mgrid[0:Hs, 0:Ws]
# alpha: distance from the white paper; the figure is the big connected part
dw = 765 - src.sum(-1)
fg = dw > 30
lab_, n = nd.label(fg); big = np.argmax(nd.sum(fg, lab_, range(1, n + 1))) + 1
fg = nd.binary_fill_holes(lab_ == big)
alpha = np.clip(dw / 90, 0, 1) * fg
alpha = np.where(nd.binary_erosion(fg, iterations=2), 1.0, alpha)
# face zones in the source (front view): the owl mask under the hat brim, the beak, the two eyes
EYES = [dict(cx=512.5, cy=213, rx=27, ry=16), dict(cx=603.5, cy=213, rx=27, ry=17)]   # viewer's left, right
MASK = dict(x0=470, x1=650, y0=180, y1=256)
BEAK = dict(x0=526, x1=567, y0=194, y1=252)
face = src.copy()
for e in EYES:                     # eyes out: the mask's own grey, pixel eyes go on top after shrinking
    m = ((xx - e['cx']) / (e['rx'] + 3)) ** 2 + ((yy - e['cy']) / (e['ry'] + 3)) ** 2 < 1
    ring = (((xx - e['cx']) / (e['rx'] + 10)) ** 2 + ((yy - e['cy']) / (e['ry'] + 8)) ** 2 < 1) & ~m
    face[m] = np.median(src[ring & (src.sum(-1) > 150) & (src.sum(-1) < 420)], 0)
HEAD_Y = 262                       # the beard starts below this row; above it nothing sways
def warp(img, a, ph):
    t = 2 * np.pi * ph
    w = np.clip((yy - HEAD_Y) / 420.0, 0, 1) ** 1.3                 # more the further down a strand hangs
    side = np.clip(np.abs(xx - 560) / 300.0, 0, 1)                   # arms and side rags swing a bit more
    dx = (8 * np.sin(t + yy / 140.0) * w + 6 * side * np.sin(t + 1.2) * w).astype(np.float32)
    dy = (2.5 * np.sin(t + xx / 90.0) * w).astype(np.float32)
    mx = (xx - dx).astype(np.float32); my = (yy - dy).astype(np.float32)
    out = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    oa = cv2.remap(a.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out, oa
w_, h_ = int(round(Ws * SC)), int(round(Hs * SC))
def shrink(img, a):
    pm = cv2.resize(img * a[..., None], (w_, h_), interpolation=cv2.INTER_AREA)
    aa = cv2.resize(a, (w_, h_), interpolation=cv2.INTER_AREA)
    return pm / np.maximum(aa[..., None], 1e-4), aa > 0.5
FOG = np.array([30, 58, 60], np.float32)
G = float(os.environ.get('G2_GAIN', 0.8))
BACKLIT = os.environ.get('G2_LIGHT', 'backlit') == 'backlit'
def grade(rgb):                    # into the night fog: a bit darker, toward teal; warm parts keep their warmth
    if BACKLIT:
        # v7, like Ho-Oh and Lugia: the moon is behind him, so his front is in shade and takes the scene's colour.
        # Colours lose half their strength, turn toward the fog's teal, and get darker toward the water.
        lum = (rgb * np.array([0.3, 0.55, 0.15])).sum(-1, keepdims=True)
        c = lum + (rgb - lum) * 0.88
        warm0 = (rgb[..., :1] - rgb[..., 2:3] > 18) & (lum > 100)       # v10: beak and shell keep their warmth
        c = c * np.where(warm0, np.array([0.97, 0.96, 0.92]), np.array([0.84, 0.97, 1.0]))
        rows = np.arange(rgb.shape[0])[:, None, None] / (WAIST_SRC * SC)
        v = np.interp(rows, [0.0, 0.35, 1.0], [0.96, 0.88, 0.74])
        return np.clip(c * v + FOG * 0.10, 0, 255)
    lum = rgb.mean(-1, keepdims=True)
    tint = rgb * np.array([0.82, 0.97, 1.0]) * G + FOG * 0.12
    warm = (rgb[..., :1] - rgb[..., 2:3] > 25) & (lum > 120)
    return np.clip(np.where(warm, rgb * (G + 0.06) + FOG * 0.06, tint), 0, 255)
WAIST_SRC = 568                    # the coat's waist in the front view: his waterline when he has risen
frames = []
for k in range(POSES):
    w_img, w_a = warp(face, alpha, k / POSES)
    rgb, a = shrink(w_img, w_a)
    frames.append((grade(rgb), a))
# palette: fixed tones + k-means for the rest
NAMES = ['eyeW', 'iris', 'pupil', 'rim', 'maskL', 'maskD', 'beakL', 'beakD', 'shell']
FIXED = np.array([[216, 248, 240], [96, 208, 224], [8, 16, 24], [128, 176, 160],
                  [120, 128, 116], [80, 90, 84], [184, 172, 140], [128, 118, 96], [150, 76, 56]], np.float32)
if BACKLIT:                        # v7: mask, beak and shell in shade too; the rim is the moon's pale green; eyes still glow
    FIXED = np.array([[208, 240, 232], [88, 200, 216], [8, 16, 24], [152, 200, 168],
                      [96, 112, 108], [64, 78, 76], [168, 160, 128], [112, 108, 88], [120, 72, 60]], np.float32)
if BACKLIT:                        # v10 design check: the kelp beard needs its own greens (the card's lime strands over
    # the black coat; k-means gave only grey-olive), the shell its orange-red. The pupil shares the darkest colour.
    NAMES = ['eyeW', 'iris', 'rim', 'maskL', 'maskD', 'beakL', 'beakD', 'shell', 'kelpD', 'kelpL']
    FIXED = np.array([[208, 240, 232], [88, 200, 216], [152, 200, 168], [104, 116, 108], [68, 80, 76],
                      [184, 168, 128], [128, 116, 88], [152, 84, 60], [64, 100, 44], [120, 160, 64]], np.float32)
K = 15 - len(FIXED)
def lab(c):
    L = cv2.cvtColor(np.clip(c, 0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    L[:, 1:] = (L[:, 1:] - 128) * float(os.environ.get('G2_CHROMA', 2.2)); return L
def zone(z):                       # a source rectangle -> mask in the shrunk picture
    m = np.zeros((h_, w_), bool)
    m[int(z['y0'] * SC):int(np.ceil(z['y1'] * SC)), int(z['x0'] * SC):int(np.ceil(z['x1'] * SC))] = True
    return m
FACEZ = zone(MASK); BEAKZ = zone(BEAK)
pix = np.concatenate([f[0][f[1] & ~FACEZ] for f in frames])
pl = lab(pix)
rng = np.random.default_rng(3)
idx0 = [int(np.argmin(pix.sum(1)))]                 # start from the darkest, then k-means++
for _ in range(K - 1):
    d = ((pl[:, None] - pl[idx0][None]) ** 2).sum(-1).min(1); idx0.append(int(rng.choice(len(pl), p=d / d.sum())))
Cl = pl[idx0].copy(); C = pix[idx0].copy()
for it in range(30):
    d = ((pl[:, None] - Cl[None]) ** 2).sum(-1); l = d.argmin(1)
    for j in range(K):
        if (l == j).any(): Cl[j] = pl[l == j].mean(0); C[j] = pix[l == j].mean(0)
C = C[np.argsort(C.sum(1))]
PAL = (np.round(np.concatenate([C, FIXED]) / 8) * 8).clip(0, 248)
I = {nm: K + 1 + i for i, nm in enumerate(NAMES)}          # palette index (1-based; 0 = transparent)
DARK = 1
if 'pupil' not in I: I['pupil'] = DARK
def quant_to(rgb, ids):
    ids = np.array(ids)
    d = ((lab(rgb.reshape(-1, 3))[:, None] - lab(PAL[ids - 1])[None]) ** 2).sum(-1)
    return ids[d.argmin(-1)].reshape(rgb.shape[:2])
general = list(range(1, K + 1)) + [I['maskL'], I['maskD'], I['beakL'], I['beakD'], I['shell']] + [I[k] for k in ('kelpD', 'kelpL') if k in I]
def quant(rgb, a):
    idx = quant_to(rgb, general)
    lum = rgb.mean(-1)
    sat = rgb.max(-1) - rgb.min(-1)
    redish = (rgb[..., 0] - rgb[..., 2] > 30) & (rgb[..., 0] - rgb[..., 1] > 22) & (rgb[..., 0] > 80)
    if BACKLIT: redish = (rgb[..., 0] - rgb[..., 2] > 16) & (rgb[..., 0] - rgb[..., 1] > 12) & (rgb[..., 0] > 60)
    idx[redish & ~BEAKZ] = I['shell']                          # the red shell on his shoulder
    fz = FACEZ & ~BEAKZ & ((sat < 40) | (lum < 52))          # only the grey mask (and its dark cracks), not the beard
    if BACKLIT:   # v7: the beard's dark green under the mask is beard, not a crack (it made a dark line under his face)
        fz = FACEZ & ~BEAKZ & (sat < 22)
    # the mask: two greys and the darkest (its cracks and the hat's shadow line)
    idx[fz] = np.where(lum[fz] < 52, DARK, np.where(lum[fz] < 82, I['maskD'], I['maskL']))
    # the beak: beige, its shade, its dark outline; grey/green around it falls back to the mask rule
    bz = BEAKZ & ((sat < 40) | (lum < 52) | (rgb[..., 0] - rgb[..., 2] > 12))
    warm = (rgb[..., 0] - rgb[..., 2] > 12) & (lum > 95)
    if BACKLIT: warm = (rgb[..., 0] - rgb[..., 2] > 5) & (lum > 72)
    idx[bz] = np.where(warm[bz], np.where(lum[bz] > 128, I['beakL'], I['beakD']),
                       np.where(lum[bz] < 52, DARK, np.where(lum[bz] < 82, I['maskD'], I['maskL'])))
    idx[~a] = 0
    return idx
def rim(idx):                      # the moon is behind and above: top edges of the hat and shoulders catch a pale line
    solid = idx > 0
    up = np.zeros_like(solid); up[1:] = solid[:-1]
    top = solid & ~up
    run = nd.uniform_filter1d(top.astype(float), 3, axis=1) > 0.99
    upper = np.zeros_like(top); upper[:int(h_ * 0.42)] = True
    lum = PAL[np.maximum(idx, 1) - 1].sum(-1)
    out = idx.copy(); out[top & run & upper & (lum < 330)] = I['rim']
    if BACKLIT:   # v7: backlit, every edge that faces up or out (toward the sky) catches the moon down to his waist
        lf = np.zeros_like(solid); lf[:, 1:] = solid[:, :-1]
        rt = np.zeros_like(solid); rt[:, :-1] = solid[:, 1:]
        side = solid & (~lf | ~rt) & up
        hi = np.zeros_like(top); hi[:int(WAIST_SRC * SC * 0.5)] = True       # hat, hair and shoulders only
        face = FACEZ | BEAKZ
        out[(top | side) & hi & ~face & (lum < 330)] = I['rim']
    return out
def own_edges(idx):
    """v8b (Arvind: "the outline on Gravriel was not good; look at how Lugia and Ho-Oh do it"). Their sprites have no
    outline: the silhouette's edge pixels are just the colour inside them, a shade darker. The concept art's black ink
    around his silhouette is swapped for that: each edge pixel much darker than what lies inside it takes the inner
    colour times 0.85 (nearest general palette entry)."""
    solid = idx > 0
    pad = np.pad(solid, 1)
    edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    inner = solid & ~edge
    rgbi = PAL[np.maximum(idx, 1) - 1].astype(float)
    lum = rgbi @ np.array([0.3, 0.55, 0.15])
    out = idx.copy()
    gen = np.array(general)
    ys, xs = np.nonzero(edge)
    for y, x in zip(ys, xs):
        y0, y1, x0, x1 = max(0, y - 2), y + 3, max(0, x - 2), x + 3
        m = inner[y0:y1, x0:x1]
        if not m.any(): continue
        c = np.median(rgbi[y0:y1, x0:x1][m], 0)
        lc = c @ np.array([0.3, 0.55, 0.15])
        if lum[y, x] >= 0.72 * lc: continue                     # already its own tone
        if idx[y, x] in (I['eyeW'], I['iris'], I['pupil']): continue
        want = c * 0.85
        d = ((PAL[gen - 1] - want) ** 2).sum(1)
        out[y, x] = gen[d.argmin()]
    return out
# pixel eyes: an ellipse cut by a lid line that droops toward the outer corner
# v5: the eyes are always open. He looks down and ahead while he rises, right and left when only his eyes are out of
# the water (like at a crossing), and at the viewer only at the very end.
STATES = dict(away=dict(lid=0.36, px=0.0, py=0.42, inw=0.6), right=dict(lid=0.34, px=0.36, py=0.12, inw=0.0),
              left=dict(lid=0.34, px=-0.36, py=0.12, inw=0.0), stare=dict(lid=0.31, px=0.0, py=0.0),
              glow=dict(lid=0.29, px=0.0, py=0.0, hi=True))
EW, EH = int(os.environ.get('G2_EW', round(14 * SC / 0.25))), int(os.environ.get('G2_EH', round(11 * SC / 0.25)))
def draw_eye(state, outer_left):
    st = STATES[state]
    g = np.zeros((EH, EW), np.int32)                  # 0 = keep the picture
    cx, cy, rx, ry = (EW - 1) / 2, (EH - 1) / 2 + 0.3, EW / 2 - 0.15, EH / 2 - 0.15
    def lid_y(x):                                     # lid edge row (0..EH), lower at the outer corner
        u = (x - cx) / rx * (-1 if outer_left else 1)  # u=-1 outer, +1 inner
        return (cy - ry) + 2 * ry * (st['lid'] + 0.10 * (-u) * (1 - st['lid'] * 0.6))
    inward = 0.18 * st.get('inw', 1.0) * (1 if outer_left else -1)           # irises sit toward the beak, white shows on the outer side
    icx = cx + (st.get('px', 0) + inward) * rx; icy = cy + 0.1 * ry + st.get('py', 0) * ry
    ir = ry * 0.72
    for y in range(EH):
        for x in range(EW):
            inside = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 1
            if not inside: continue
            edge = any(not (((x + dx - cx) / rx) ** 2 + ((y + dy - cy) / ry) ** 2 < 1) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            ly = lid_y(x)
            if st['lid'] >= 1.0:                       # closed: just the lash line where the lid meets the lower rim
                ly2 = (cy - ry) + 2 * ry * (0.62 + 0.10 * ((x - cx) / rx * (1 if outer_left else -1)))
                if abs(y - ly2) < 0.6 and abs(x - cx) < rx * 0.92: g[y, x] = DARK
                continue
            if y < ly - 1.0: g[y, x] = I['maskL'] if not edge else I['maskD']
            elif y < ly + 0.8 or edge: g[y, x] = DARK                 # the heavy lid line and the outline
            else:
                d = np.hypot(x - icx, (y - icy) * 1.05)
                g[y, x] = I['pupil'] if d < ir * 0.5 else I['iris'] if d < ir else I['eyeW']
    if st.get('hi'):                                   # a glint up and to the inner side of the pupil
        hx = int(round(icx + (1.6 if outer_left else -1.6))); hy = int(round(max(lid_y(hx) + 1.2, icy - 1)))
        if 0 <= hy < EH and g[hy, hx] in (I['iris'], I['pupil']): g[hy, hx] = I['eyeW']
    return g
def paste_eyes(idx, state):
    out = idx.copy()
    for n, e in enumerate(EYES):
        g = draw_eye(state, outer_left=(n == 0))
        x0 = int(round(e['cx'] * SC - (EW - 1) / 2)); y0 = int(round(e['cy'] * SC - (EH - 1) / 2))
        sub = out[y0:y0 + EH, x0:x0 + EW]
        sub[g > 0] = g[g > 0]
    return out
WAIST_SRC = 568                    # the coat's waist in the front view: his waterline when he has risen
EYE_BOTTOM = int(round(max(e['cy'] + e['ry'] for e in EYES) * SC))
def harmonize(pal):
    """v16 (Arvind: "Gravriel looks a bit out of place with his colours"). The scene is blue-green (hue 195-220) and
    dark; Lugia is drawn in its scene's own colours. Each colour keeps its family but is pulled into the scene: greens
    turn toward sea green, warm colours (shell, beak) lose saturation and brightness instead of changing hue, darks
    turn blue, nothing but the eyes is brighter than the scene's pale mid tones, and the eyes come down a little.
    Applied to the palette after quantization, so every pixel keeps its index."""
    import colorsys
    out = []
    for i, c in enumerate(pal):
        r, g, b = (np.array(c) / 255.0).tolist()
        h, s_, v = colorsys.rgb_to_hsv(r, g, b); hd = h * 360
        if i + 1 in (I['eyeW'], I['iris']):
            v *= 0.86; s_ = min(s_, 0.5)
        elif v < 0.22:                                   # darks: the scene's blue-black
            hd, s_ = 212, max(s_, 0.42)
        elif 55 <= hd <= 175:                            # greens (kelp, coat, hands): toward sea green
            hd = hd + (172 - hd) * 0.6; s_ = min(s_ * 0.85, 0.42); v *= 0.92
        elif hd < 55 or hd > 300:                        # warm (shell, beak): keep the hue, lose strength
            s_ *= 0.6; v *= 0.82
        else:                                            # greys and blue-greys: a touch toward the scene's blue
            hd = hd + (200 - hd) * 0.5 if s_ > 0.02 else 200; s_ = max(s_, 0.12)
        rr, gg, bb = colorsys.hsv_to_rgb((hd % 360) / 360, s_, v)
        out.append([int(round(x * 255 / 8)) * 8 for x in (rr, gg, bb)])
    return np.clip(np.array(out), 0, 248)
if BACKLIT and os.environ.get('G2_HARMONIZE', '1') == '1':
    PAL = harmonize(PAL)
meta = dict(palette=[[0, 0, 0]] + PAL.astype(int).tolist(), scale=SC, poses=POSES, states=list(STATES),
            waist=int(round(WAIST_SRC * SC)), eye_bottom=EYE_BOTTOM,
            src_size=[Ws, Hs], index=I)
P = np.array(meta['palette'], np.uint8); BG = np.array([22, 40, 44], np.uint8)
def show(im): r = P[im]; r[im == 0] = BG; return r
sheet = []
for k, (rgb, a) in enumerate(frames):
    base = quant(rgb, a)
    if os.environ.get('G2_RIM', '0') == '1': base = rim(base)    # v8b: off. Ho-Oh and Lugia have no light rim
    if BACKLIT: base = own_edges(base)
    row = []
    for s in STATES:
        im = paste_eyes(base, s)
        Image.fromarray(im.astype(np.uint8)).save(os.path.join(OUT, f'p{k}_{s}.png'))
        row.append(im)
    sheet.append(row)
json.dump(meta, open(os.path.join(OUT, 'pal.json'), 'w'))
top = np.concatenate([show(x) for x in sheet[0]], 1)
Image.fromarray(top).resize((top.shape[1] * 3, top.shape[0] * 3), Image.NEAREST).save(os.path.join(OUT, 'preview.png'))
# head close-ups of every eye state, x8
hy0, hy1 = int(150 * SC), int(270 * SC); hx0, hx1 = int(420 * SC), int(700 * SC)
heads = np.concatenate([np.pad(show(x)[hy0:hy1, hx0:hx1], ((2, 2), (2, 2), (0, 0))) for x in sheet[0]], 1)
Image.fromarray(heads).resize((heads.shape[1] * 8, heads.shape[0] * 8), Image.NEAREST).save(os.path.join(OUT, 'head.png'))
print('ok', sheet[0][0].shape, 'palette', meta['palette'])
