"""Scene 3: the deer trio replaces Suicune, Entei and Raikou (Arvind 2026-11-12). a/2/6/2 members: 39 palette,
40 shared BG tiles (1024, 4bpp), screens 48 (top strip, Entei), 47 (middle, Suicune), 49 (bottom, Raikou).
Each strip is a 256x64 band of 8 tile rows; we give each deer two palettes of its own (6-9 were empty) and pack its
tiles into the slots only the three beast strips used plus the slots no screen used.
python deer/build_strips.py IN.narc OUT.narc   (pictures and crops in STRIPS below)"""
import sys, os, struct, json, numpy as np
from scipy import ndimage as nd
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from g2d import lz10_dec, read_ncgr, sections
from lz import lz10_enc
from narc import unpack, pack
SRC, DST = sys.argv[1], sys.argv[2]
# Targets measured from the originals (deer/measure.py, 2026-11-14): one palette of 9-11 flat colours, 30-37 % of the
# band covered, body luma mean ~65 (p90 ~96), 30-40 gold eye pixels (246,211,101) about 3x brighter than the body.
# name, picture, screen member, band first tile row, palette, eye height
# + how far down the band the eyes sit (the originals differ: Entei high, Suicune 60 %, Raikou low); low eyes keep
#   the antlers, orbs and crown in the picture
SWAP = os.environ.get('SWAP', '0') == '1'     # v3: Qwen style swap of the original strip (deer/gen_swap.py), read on its 6x grid
SWAPS = {'rockedeer': 'swap/rockedeer_7c1.png', 'felk': 'swap/felk_6.png', 'moosus': 'swap/moosus_2.png'}
# v10 (2026-11-15) defaults: copy/rockedeer_1 + copy/felk_5 (deer/gen_copystyle.py: our design first, the original strip as style only), swap/moosus_2, v5 converter (STYLE3=0)
#   v9 = rock4_e2, swap/moosus_2, faces/felk7_e3 with STYLE3=1
# v8 (2026-11-15) defaults: rock4_e2 (v5), moosus_2 (v3, Arvind liked it), felk7_e1 (from Arvind's Felk picture), STYLE3 cel pass, MAT 6
#   (v6 = style/rockedeer_r2k65_21, moosus_r2k65_21, felk_r2k65_23 with STYLE3=0; v5 = rock4_e2, moos4_e4, felk5_e8 with STYLE3=0)
# v6 (2026-11-15): Sugimori-LoRA style pass of the v5 faces (deer/style_test.py r2, denoise 0.65, seeds 21/21/23); v5 = faces/rock4_e2, moos4_e4, felk5_e8
# v4 (Arvind 2026-11-14): Moosus in the middle (Suicune, head-on); the others look the way Entei (left) and Raikou (right) do
STRIPS = [('rockedeer', os.environ.get('ROCK', 'copy/rockedeer_1.png'), 48, 0, 1, 0.35),
          ('moosus', os.environ.get('MOOS', 'swap/moosus_2.png'), 47, 8, 5, 0.60),
          ('felk', os.environ.get('FELK', 'copy/felk_5.png'), 49, 16, 6, float(os.environ.get('FELK_EYE', 0.42)))]
LINES = os.environ.get('DEER_LINES', '0') == '1'   # v2's own line art + mode filter + black eye ring: Arvind found it worse
COVER, LUMA, EYE_PX, NCOL = 0.33, 66.0, 32, 9
# v7 (Arvind 2026-11-15: v5 and D best, none good enough; D's clean source went grey in the shrink): STYLE2=1 grades with a curve
# that keeps the darks dark and the contrast (instead of scaling + pressing highlights), uses 11 colours (originals 9-11) and keeps
# the source's own black lines (a band pixel goes black when >= LINE_KEEP of its source block is dark line) - not drawn lines like v2
STYLE2 = os.environ.get('STYLE2', '0') == '1'
LINE_KEEP = float(os.environ.get('LINE_KEEP', 0.34))
if STYLE2: NCOL = 11
# v8 (Arvind 2026-11-15: "ours is not cel-shaded like the original: few colours, base colours with one layer of shadow over them,
# and many outlines"): STYLE3=1. Measured: each material in the originals is a base + one shadow ~0.4-0.5x as bright and a bit
# cooler (82,98,123)/(32,49,65), (139,8,8)/(57,0,0), (24,106,139)/(0,41,82), (98,57,115)/(57,24,57), plus black lines and the eye gold.
# Here: MAT materials by k-means on colour (not brightness) at 4x, each split lit/shadow (Otsu within it), mode-shrunk to the band,
# base set to the originals' brightness, shadow = base x SHADOW cooled, black outlines between materials and the source's dark lines.
STYLE3 = os.environ.get('STYLE3', '0') == '1'
MAT = int(os.environ.get('MAT', 6)); SHADOW = float(os.environ.get('SHADOW', 0.45)); BASE_MAX = float(os.environ.get('BASE_MAX', 140))
if STYLE3: NCOL = 2 * MAT
LINE_L = float(os.environ.get('LINE_L', 14)); LIT_FRAC = float(os.environ.get('LIT_FRAC', 0.62)); BASE_MIN_L = float(os.environ.get('BASE_MIN_L', 82)); HALO = os.environ.get('HALO', 'felk').split(','); OUT_DE = float(os.environ.get('OUT_DE', 30))   # 30: inner lines 0.05-0.12 (originals 0.04-0.09)
MERGE = 3                                               # tiles differing in this many pixels or fewer share a slot          # body colours; + eye gold + eye shade + black = 12
EYE, EYE2 = np.array([255, 222, 115.]), np.array([197, 156, 24.])   # the originals' own eye tones
SWAP_LUMA = 72.0         # swap strips: a touch above the originals' ~66, our colours are lighter by design
LINE_FRAC = 0.075        # thin black line art per lit pixel: Suicune 0.089, Raikou 0.079, Entei 0.040
BUDGET = {}
def to_lab(c):                       # simple sRGB -> Lab
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def kmeans(X, k, it=12, seed=0):
    rng = np.random.default_rng(seed); C = X[rng.choice(len(X), min(k, len(X)), replace=False)]
    for _ in range(it):
        a = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([X[a == j].mean(0) if (a == j).any() else C[j] for j in range(len(C))])
    return C
def gba5(c): return np.round(np.clip(c, 0, 255) / 255 * 31) * 255 / 31
def luma(a): return 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]
def eye_mask(a):
    v = a.max(-1); sat = (v - a.min(-1)) / np.maximum(v, 1)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (v > 150) & (sat > 0.4) & (r > b + 60) & (g > b + 30) & (g <= r + 10)   # v8: gold, not lime leaves
def strip_pixels(path, eyey=0.62):
    """crop a 4:1 window round the eyes, zoomed so the creature covers COVER of the band"""
    src = np.asarray(Image.open(os.path.join(HERE, path)).convert('RGB')).astype(np.float32)
    H, W = src.shape[:2]; em = eye_mask(src); ys, xs = np.where(em)
    cx, cy = (xs.mean(), ys.mean()) if len(xs) else (W / 2, H / 2)
    best = None
    zs = [1.0] if '/swap/' in '/' + path or path.startswith('swap/') else np.linspace(1.0, 1.45, 10)   # v8: swap pictures sit on the original's grid
    for z in zs:                                      # wider than this cuts antlers, orbs and crown away
        w, h = W / z, H / z; x0 = np.clip(cx - w / 2, 0, W - w); y0 = np.clip(cy - h * eyey, 0, H - h)   # eyes ~60 % down, as Suicune's
        a = np.asarray(Image.fromarray(src.astype(np.uint8)).crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((256, 64), Image.LANCZOS)).astype(np.float32)
        cov = (a.max(-1) > 24).mean()
        if best is None or abs(cov - COVER) < abs(best[0] - COVER): best = (cov, z, a, (int(x0), int(y0), int(x0 + w), int(y0 + h)), src)
    return best
def one_palette(a, src_eye):
    """body graded to the original's luma, NCOL flat colours by k-means, eyes forced to the original gold"""
    live = a.max(-1) > 24
    body = live & ~src_eye
    a = a.copy()
    if STYLE2:                                              # curve: top (p97) -> 112, gamma so the body mean lands on LUMA
        f = luma(a); top = max(np.percentile(f[body], 97), 1); x = np.clip(f / top, 0, 1.2)
        g = 1.0
        for _ in range(30):
            m = (112 * x[body] ** g).mean(); g *= (m / LUMA) ** 0.5
        t = 112 * x ** g; a[body] *= (t / np.maximum(f, 1))[body][:, None]
    else:
      for _ in range(3):                                      # mean to LUMA, highlights pressed down toward p90 ~96
        a[body] *= LUMA / max(luma(a[body]).mean(), 1)
        f = luma(a); t = np.where(f > 80, 80 + (f - 80) * 0.45, f); a[body] *= (t / np.maximum(f, 1))[body][:, None]
    a = np.clip(a, 0, 255)
    C = kmeans(to_lab(a[body][:: max(1, body.sum() // 6000)]), NCOL, seed=1)
    px = a[body]; Lp = to_lab(px)
    cols = np.array([px[((Lp - c) ** 2).sum(-1).argmin()] for c in C])
    pal = gba5(np.vstack([[0, 0, 0], cols, EYE, EYE2]))       # 1 black, 2..NCOL+1 body, eye, eye shade
    L = to_lab(a); P = to_lab(pal[:NCOL + 1])
    idx = ((L[..., None, :] - P[None, None]) ** 2).sum(-1).argmin(-1)
    idx[~live] = 0
    # glow round the eyes is not eye: gold body colours outside the eye mask take the nearest non-gold colour
    v = pal.max(-1); sat = (v - pal.min(-1)) / np.maximum(v, 1)
    import colorsys
    hue = np.array([colorsys.rgb_to_hsv(*(c / 255))[0] * 360 for c in pal])
    goldc = (v > 140) & (sat > 0.4) & (hue > 30) & (hue < 75); goldc[0] = False; goldc[NCOL + 1:] = False
    if goldc.any() and (~goldc[1:NCOL + 1]).any():
        bad = np.isin(idx, np.where(goldc)[0]) & ~src_eye
        ok = np.where(~goldc[:NCOL + 1] & (np.arange(NCOL + 1) > 0))[0]
        d2 = ((L[bad][:, None] - P[ok][None]) ** 2).sum(-1)
        idx[bad] = ok[d2.argmin(1)]
    # eyes: the core gets the gold, a one-pixel ring the shade (as the originals: a glowing slit)
    core = src_eye
    ring = nd.binary_dilation(core) & ~core & live
    idx[core] = NCOL + 1                                   # v4: no gold ring (it doubled the eye size)
    return idx, pal
def otsu(v):
    h, e = np.histogram(v, 64); c = (e[:-1] + e[1:]) / 2; w = np.cumsum(h); m = np.cumsum(h * c); best, t = -1, np.median(v)
    for i in range(1, 63):
        if w[i] == 0 or w[-1] - w[i] == 0: continue
        b = w[i] * (w[-1] - w[i]) * (m[i] / w[i] - (m[-1] - m[i]) / (w[-1] - w[i])) ** 2
        if b > best: best, t = b, c[i]
    return t
def mode_shrink(lab, k, n):
    H, W = lab.shape; h, w = H // k, W // k
    blocks = lab[:h * k, :w * k].reshape(h, k, w, k).transpose(0, 2, 1, 3).reshape(h, w, k * k)
    cnt = np.stack([(blocks == i).sum(-1) for i in range(n)], -1); return cnt.argmax(-1), cnt
def cel(src, box, em, name=''):
    """v8: flat cel shading like the originals (see STYLE3 above). Returns band indices (0 black, 1..2*MAT body, eyes after) and palette"""
    K = 4
    hi = np.asarray(Image.fromarray(src.astype(np.uint8)).crop(box).resize((256 * K, 64 * K), Image.LANCZOS)).astype(np.float32)
    live = hi.max(-1) > 24
    top = np.percentile(hi[live].max(-1), 97); hi = np.clip(hi * (235 / max(top, 1)), 0, 255)   # night-dark sources: stretch first
    L = luma(hi)
    line = live & (L < LINE_L)                                   # the picture's own dark lines and darkest gaps
    body = live & ~line
    lab = to_lab(nd.gaussian_filter(hi, (2.5, 2.5, 0)))          # colour first, brightness a little; chroma relative to brightness
    ch = lab[..., 1:] * (60 / (lab[..., :1] + 40))            # so a dark brown mane is not grouped with dark grey
    feat = np.concatenate([lab[..., :1] * 0.35, ch], -1)
    C = kmeans(feat[body][:: max(1, body.sum() // 20000)], MAT, seed=1)
    m = ((feat[..., None, :] - C[None, None]) ** 2).sum(-1).argmin(-1)
    cls = np.zeros(L.shape, int)                                 # 0 black, 1 + 2*i lit, 2 + 2*i shadow
    bases = []
    for i in range(MAT):
        sel = body & (m == i)
        if sel.sum() < 50: bases.append(np.array([60, 60, 70.])); continue
        t = np.quantile(L[sel], 1 - LIT_FRAC) if LIT_FRAC > 0 else otsu(L[sel]); lit = sel & (L >= t)
        cls[lit] = 1 + 2 * i; cls[sel & ~lit] = 2 + 2 * i
        px = hi[lit] if lit.sum() > 20 else hi[sel]
        bases.append(np.median(px, 0))
    small, cnt = mode_shrink(cls, K, 2 * MAT + 1)
    # a band pixel is black only when the line really covers it (not every mixed block)
    blk = cnt[..., 0] / (K * K); small[(small == 0) & (blk < 0.55)] = cnt[..., 1:].argmax(-1)[(small == 0) & (blk < 0.55)] + 1
    small[np.asarray(Image.fromarray(live.astype(np.uint8) * 255).resize((256, 64), Image.BOX)) < 110] = 0
    # outlines between different materials (not between lit and shadow of one material), drawn on the darker side
    matof = np.where(small > 0, (small - 1) // 2, -1)
    pal = [[0, 0, 0]]
    share = np.array([(m[body] == i).mean() for i in range(MAT)])
    for i, b in enumerate(bases):                                # v9: partial lift toward the originals' brightness, hue and
        b = b * np.clip((BASE_MAX / max(b.max(), 1)) ** 0.6, 0.5, 3.0)   # saturation kept (v8 lifted every material to 140: brown -> grey)
        y = luma(b); b = np.clip(y + (b - y) * 1.15, 0, 255)
        if share[i] >= 0.12 and luma(b) < BASE_MIN_L:            # big lit areas at least as light as the originals' (~95)
            b = b * BASE_MIN_L / max(luma(b), 1); y = luma(b)    # lifted colours greyed toward the originals' moonlit blue-grey
            sat = (b.max() - b.min()) / max(b.max(), 1); b = np.clip(y + (b - y) * min(1.0, 0.42 / max(sat, 0.01)), 0, 255)
        if luma(b) > 112: b = b * 112 / luma(b)                  # cream faces: not much brighter than the originals' lightest parts
        sh = b * SHADOW + np.array([-4, 0, 10]); pal += [list(b), list(sh)]
    pal = np.array(pal); lum = luma(pal)
    out = small.copy()
    for dy, dx in ((0, 1), (1, 0)):
        a1 = matof[:64 - dy, :256 - dx]; a2 = matof[dy:, dx:]
        far = np.sqrt(((to_lab(pal[1::2])[:, None] - to_lab(pal[1::2])[None]) ** 2).sum(-1)) > OUT_DE   # only clearly different materials
        diff = (a1 >= 0) & (a2 >= 0) & (a1 != a2) & far[np.maximum(a1, 0), np.maximum(a2, 0)]
        l1 = lum[small[:64 - dy, :256 - dx]]; l2 = lum[small[dy:, dx:]]
        o1 = diff & (l1 <= l2); o2 = diff & (l1 > l2)
        out[:64 - dy, :256 - dx][o1] = 0; out[dy:, dx:][o2] = 0
    out[em] = 0
    if name in HALO:                                             # thin bright gold (halos) kept as the darker eye gold
        v_ = hi.max(-1); sat_ = (v_ - hi.min(-1)) / np.maximum(v_, 1)
        gold = (v_ > 170) & (sat_ > 0.4) & (hi[..., 0] > hi[..., 2] + 60) & (hi[..., 1] > hi[..., 2] + 30) & (hi[..., 1] <= hi[..., 0] + 10)
        gf = np.asarray(Image.fromarray(gold.astype(np.uint8) * 255).resize((256, 64), Image.BOX)).astype(np.float32) / 255
        out[(gf >= 0.22) & ~nd.binary_dilation(em, iterations=2)] = 2 * MAT + 2
    if os.environ.get('CEL_DEBUG'): print('bases', [tuple(int(v) for v in b) for b in bases], 'pal', [tuple(int(v) for v in c) for c in pal[1::2]], file=sys.stderr)
    pal = gba5(np.vstack([pal, EYE, EYE2]))
    return out, pal
# v11 (Arvind 2026-11-15: "the only thing missing is the eyes"): the originals' eyes are one flat almond of bright gold
# (255,222,115) with a crisp 1-px black ring, ~30-40 px per beast (Entei one side eye 6x9, Suicune two 5x5, Raikou one 6x10).
# Ours had pupils, mixed golds and no ring. We draw them: eye centres measured in the source picture (compact yellow blobs),
# mapped into the band; shapes drawn here (not copied): a side eye looking left or right, or a frontal angry pair.
SIDE_L = [".......###", "....######", ".#########", "##########", "...####..."]
FRONT_L = ["###..", "#####", ".####", "...##"]
EYE_AT = {   # name: (source file it was measured on, kind, [(y, x) in source px])
    'rockedeer': ('rockedeer_1.png', 'left', [(175, 592)]),
    'moosus': ('moosus_2.png', 'front', [(172, 681), (170, 851)]),
    'felk': ('felk_5.png', 'right', [(202, 1009)]),
}
def stamp_eyes(img, em, box, spec):
    _, kind, pts = spec
    img = img.copy(); eyes = (NCOL + 1, NCOL + 2)
    old = nd.binary_dilation(np.isin(img, eyes) | em, iterations=1) & np.isin(img, eyes) | em
    ring = nd.binary_dilation(old, iterations=2) & ~old & ~np.isin(img, eyes)
    if ring.any():                                         # old eye pixels take the colour around them
        v, c = np.unique(img[ring], return_counts=True); fill = v[c.argmax()]
        img[old] = fill
    sx = 256 / (box[2] - box[0]); sy = 64 / (box[3] - box[1])
    pts = sorted(pts, key=lambda p: p[1])
    for k, (y, x) in enumerate(pts):
        cy = int(round((y - box[1]) * sy)); cx = int(round((x - box[0]) * sx))
        rows = SIDE_L if kind in ('left', 'right') else FRONT_L
        m = np.array([[ch == '#' for ch in r] for r in rows])
        if kind == 'right' or (kind == 'front' and k == 1): m = m[:, ::-1]
        h, w = m.shape; y0, x0 = cy - h // 2, cx - w // 2
        mask = np.zeros(img.shape, bool)
        ys, xs = np.nonzero(m); ys = ys + y0; xs = xs + x0
        ok = (ys >= 0) & (ys < 64) & (xs >= 0) & (xs < 256); mask[ys[ok], xs[ok]] = True
        img[nd.binary_dilation(mask, structure=np.ones((3, 3))) & ~mask] = 0      # crisp black ring
        img[mask] = NCOL + 1
        low = mask & ~np.roll(mask, -1, axis=0)                                   # bottom edge in the darker gold
        img[low & (np.arange(256)[None, :] % 3 == 0)] = NCOL + 2
    return img
def line_art(img, pal, lit, avoid):
    """black 1-px lines on the darker side of borders between clearly different colour areas (the originals' contour
    lines: round eyes, between plates and parts; not between a colour and its own shade). The colour distance cut is
    searched so the lines cover LINE_FRAC of the lit pixels; lone line pixels are dropped."""
    Lp = to_lab(pal); lum = luma(pal)
    def lines(T):
        m = np.zeros(img.shape, bool)
        for dy, dx in ((0, 1), (1, 0)):
            A = img[:img.shape[0] - dy, :img.shape[1] - dx]; B = img[dy:, dx:]
            both = (A > 0) & (B > 0)
            far = both & (np.sqrt(((Lp[A] - Lp[B]) ** 2).sum(-1)) > T)
            darkA = lum[A] <= lum[B]
            m[:img.shape[0] - dy, :img.shape[1] - dx] |= far & darkA
            m[dy:, dx:] |= far & ~darkA
        m &= ~avoid
        n = nd.convolve(m.astype(int), np.ones((3, 3), int), mode='constant') - m
        return m & (n >= 1)
    best = None
    for T in np.linspace(10, 60, 26):
        m = lines(T); f = m.sum() / max(lit.sum(), 1)
        if best is None or abs(f - LINE_FRAC) < abs(best[1] - LINE_FRAC): best = (m, f)
    return best[0]
def majority(img, keep):
    """3x3 mode filter: flat, clean shapes like the originals (keep = pixels left alone)"""
    out = img.copy(); H, W = img.shape; p = np.pad(img, 1, mode='edge')
    win = np.stack([p[y:y + H, x:x + W] for y in range(3) for x in range(3)])
    for v in np.unique(img):
        cnt = (win == v).sum(0)
        if v == 0: continue
        better = (cnt >= 5) & ~keep
        out[better] = v
    return out
def swap_pixels(path, k=12):
    """the swap picture is the whole strip at 6x: k flat colours (Lab k-means, near-black = black), then each 6x6 cell
    takes the colour most of it has"""
    src = np.asarray(Image.open(os.path.join(HERE, path)).convert('RGB').resize((1536, 384))).astype(np.float32)
    px = src.reshape(-1, 3); lit = px.max(-1) >= 28
    C = kmeans(to_lab(px[lit][:: max(1, lit.sum() // 20000)]), k, seed=3)
    rp = px[lit][:: max(1, lit.sum() // 20000)]; Lr = to_lab(rp)
    cols = gba5(np.array([rp[((Lr - c) ** 2).sum(-1).argmin()] for c in C]))
    pal = np.vstack([[0, 0, 0], cols])
    lab = to_lab(src); idx = ((lab[..., None, :] - to_lab(pal)[None, None]) ** 2).sum(-1).argmin(-1)
    idx[src.max(-1) < 28] = 0
    cells = idx.reshape(64, 6, 256, 6).transpose(0, 2, 1, 3).reshape(64, 256, 36)
    out = np.zeros((64, 256), int)
    for v in range(len(pal)):
        cnt = (cells == v).sum(-1)
        out = np.where(cnt > np.take_along_axis((cells == out[..., None]).sum(-1)[..., None], np.zeros((64, 256, 1), int), -1)[..., 0], v, out)
    small = src.reshape(64, 6, 256, 6, 3).mean((1, 3))
    return out, pal, small
def despeckle(img):
    out = img.copy(); H, W = img.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            n = [img[y - 1, x], img[y + 1, x], img[y, x - 1], img[y, x + 1]]
            if img[y, x] not in n:
                v, c = np.unique(n, return_counts=True)
                if c.max() >= 3: out[y, x] = v[c.argmax()]
    return out
F = unpack(open(SRC, 'rb').read())
def dec(i): return lz10_dec(F[i]) if F[i][:1] == b'\x10' else F[i]
def screen(i):
    d = dec(i); mg, v, s = sections(d); o, sc = s[b'NRCS']; sz = struct.unpack_from('<I', sc, 16)[0]
    return bytearray(d), o + 20, np.array(struct.unpack_from(f'<{sz // 2}H', sc, 20))
used = {i: set((screen(i)[2] & 1023).tolist()) for i in range(42, 53)}
beast = used[47] | used[48] | used[49]; other = set().union(*[used[i] for i in used if i not in (47, 48, 49)])
# only the beast region (688+): lower never-used slots (267-287, 527-543) are shared with other loads at run time
pool = sorted(t for t in (beast - other - {704}) | (set(range(1, 1024)) - set().union(*used.values())) if t >= 688)
g40 = bytearray(dec(40)); mg, v, s = sections(bytes(g40)); o, sc = s[b'RAHC']; tbase = o + 8 + struct.unpack_from('<I', sc, 28)[0]
p39 = bytearray(dec(39)); mg, v, s = sections(bytes(p39)); o, sc = s[b'TTLP']; pbase = o + 8 + struct.unpack_from('<I', sc, 20)[0]
def bgr(c): r, g, b = (int(round(v / 255 * 31)) for v in c); return r | g << 5 | b << 10
report = {}; previews = []
free = list(pool)
for name, pic, scr_i, row0, pal_no, eyey in STRIPS:
    if SWAP:
        img, pal, a = swap_pixels(SWAPS[name])
        # grade the palette (not pixels) toward the originals' luma; Qwen's small gold eye colours are left alone
        cnt = np.bincount(img.reshape(-1), minlength=len(pal)); pl = luma(pal)
        v = pal.max(-1); sat = (v - pal.min(-1)) / np.maximum(v, 1)
        eyec = (v > 170) & (sat > 0.4) & (pal[:, 0] > pal[:, 2] + 60) & (cnt < 90)
        body = (np.arange(len(pal)) > 0) & ~eyec
        for _ in range(4):
            m = (pl[body] * cnt[body]).sum() / max(cnt[body].sum(), 1)
            f = SWAP_LUMA / max(m, 1)
            t = pl * f; t = np.where(t > 90, 90 + (t - 90) * 0.5, t)
            pal[body] = np.clip(pal[body] * (t / np.maximum(pl, 1))[body][:, None], 0, 255); pl = luma(pal)
        pal = gba5(pal)
        # eyes: small compact bright-yellow blobs in the swap (not the halo ring, not orange flames)
        import colorsys
        hue = np.array([[colorsys.rgb_to_hsv(*(q / 255))[0] * 360 for q in row] for row in np.clip(a, 0, 255)])
        v_ = a.max(-1); s_ = (v_ - a.min(-1)) / np.maximum(v_, 1)
        cand = (v_ > 110) & (s_ > 0.3) & (hue > 38) & (hue < 75)
        lb, nb = nd.label(cand); em = np.zeros_like(cand)
        for j in range(1, nb + 1):                       # eyes are the brightest points (v 250-255; flames stop ~216)
            whole = lb == j
            if v_[whole].max() < 235: continue
            core = whole & (v_ > 0.8 * v_[whole].max())
            if core.sum() > 18: core &= v_ >= np.sort(v_[core])[-18]
            em |= core
        lb2, n2 = nd.label(em, structure=np.ones((3, 3)))     # keep an eye pair (same height, 6-40 px apart; the lowest: eyes sit under crowns and halos) or one eye
        if n2 > 1:
            cs = nd.center_of_mass(em, lb2, range(1, n2 + 1)); sz = nd.sum(em, lb2, range(1, n2 + 1))
            pairs = [(cs[i][0] + cs[j][0], i, j) for i in range(n2) for j in range(i + 1, n2)
                     if abs(cs[i][0] - cs[j][0]) <= 4 and 6 <= abs(cs[i][1] - cs[j][1]) <= 40]
            keep = [max(pairs)[1:]] if pairs else [(int(np.argmax(sz)),)]
            em = np.isin(lb2, [k + 1 for k in keep[0]])
        if 0 < em.sum() < 20:                                # tiny eyes read as specks at DS size: one pixel wider
            em = nd.binary_dilation(em, structure=[[0, 0, 0], [1, 1, 1], [0, 0, 0]]) & (img > 0)
        if em.any():
            pal = np.vstack([pal, EYE, EYE2])[:16]; l_ = luma(a)
            img[em] = len(pal) - 1; img[em & (l_ >= np.median(l_[em]))] = len(pal) - 2
        z, box = 1.0, (0, 0, 1536, 384)
    else:
        cov, z, a, box, src = strip_pixels(pic, eyey)
        # eye pixels in the band: the brightest gold blobs, grown or shrunk to about EYE_PX
        em = eye_mask(a); em[:14] = False                       # v8: halos and crowns sit in the top rows, eyes never do
        score = np.where(em, luma(a), 0)
        if em.sum() > EYE_PX: em = score >= np.sort(score[em])[-EYE_PX]
        lab_, n_ = nd.label(em)                                  # one eye is at most ~18 px, like Suicune's (15 + 15)
        for j in range(1, n_ + 1):
            b_ = lab_ == j
            if b_.sum() > 16: em &= ~(b_ & (score < np.sort(score[b_])[-16]))
        while 0 < em.sum() < EYE_PX * 0.7: em = nd.binary_dilation(em, structure=[[0, 0, 0], [1, 1, 1], [0, 0, 0]]) & (a.max(-1) > 40)
        em = nd.binary_fill_holes(nd.binary_closing(em) | em) & (a.max(-1) > 40)   # whole eyes, no specks
        if STYLE3: img, pal = cel(src, box, em, name); lit = img > 0
        else:
            img, pal = one_palette(a, em)
            lit = img > 0
            img = despeckle(img)
        if STYLE2 and not STYLE3:                           # the source's own black lines, kept through the shrink
            sc = src[box[1]:box[3], box[0]:box[2]]; ls = luma(sc)
            fig = nd.binary_fill_holes(nd.binary_closing(ls > 24, iterations=3))
            dark = (ls < 34) & fig
            frac = np.asarray(Image.fromarray((dark * 255).astype(np.uint8)).resize((256, 64), Image.BOX)).astype(np.float32) / 255
            img[(frac >= LINE_KEEP) & lit & ~nd.binary_dilation(em)] = 0
        if LINES:
            img = majority(majority(img, em), em)
            img[line_art(img, pal, lit, nd.binary_dilation(em, iterations=1))] = 0
        # eyes like the originals: bright core, darker gold lower half, black ring
        core_l = luma(a)
        img[em] = NCOL + 2
        if em.any(): img[em & (core_l >= np.median(core_l[em]))] = NCOL + 1
        if LINES: img[nd.binary_dilation(em) & ~em & lit] = 0
        if name in EYE_AT and os.path.basename(pic) == EYE_AT[name][0]:
            img = stamp_eyes(img, em, box, EYE_AT[name])
        grp = np.zeros(256, int); pals = [pal]; pals_no = (pal_no,)
    grp = np.zeros(256, int); pals = [pal]; pals_no = (pal_no,)
    for merge in (MERGE, 5, 7, 9, 12, 16):                 # merge harder only when the strip does not fit
        # tiles, dedupe with flips
        tiles = {}; entries = np.zeros((8, 32), int); new = []
        for ty in range(8):
            for tx in range(32):
                t = img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] + 1          # colour index 1..15 (1 = black)
                p = pals_no[grp[ty * 32 + tx]]
                key = None
                for hf in (0, 1):
                    for vf in (0, 1):
                        tt = t[:, ::-1] if hf else t; tt = tt[::-1] if vf else tt
                        k = tt.tobytes()
                        if k in tiles: key = (tiles[k], hf, vf); break
                    if key: break
                if not key and new:                               # near-duplicate (<= MERGE pixels differ): reuse it
                    N = np.array(new)
                    for hf in (0, 1):
                        for vf in (0, 1):
                            tt = t[:, ::-1] if hf else t; tt = tt[::-1] if vf else tt
                            dif = (N != tt).sum((1, 2)); j = int(dif.argmin())
                            if dif[j] <= merge and not key: key = (j, hf, vf)
                if not key:
                    tiles[t.tobytes()] = len(new); new.append(t); key = (len(new) - 1, 0, 0)
                entries[ty, tx] = key[0] | key[1] << 10 | key[2] << 11 | p << 12
        if len(new) <= len(free): break
    if len(new) > len(free): raise SystemExit(f'{name}: {len(new)} tiles, only {len(free)} free')
    slots = free[:len(new)]; free = free[len(new):]
    for k, t in enumerate(new):
        b = bytes((t.reshape(-1)[0::2] | (t.reshape(-1)[1::2] << 4)).astype(np.uint8))
        g40[tbase + slots[k] * 32: tbase + slots[k] * 32 + 32] = b
    ent = (entries & ~1023) | np.vectorize(lambda e: slots[e & 1023])(entries)
    d, off, e = screen(scr_i); e = e.reshape(32, 32)
    e[row0:row0 + 8] = ent
    struct.pack_into(f'<{e.size}H', d, off, *e.reshape(-1).tolist())
    F[scr_i] = lz10_enc(bytes(d)) if F[scr_i][:1] == b'\x10' else bytes(d)
    for c in range(16):
        col = pal[c - 1] if 1 <= c <= len(pal) else (0, 0, 0)
        struct.pack_into('<H', p39, pbase + 2 * (16 * pal_no + c), bgr(col) if c else 0)
    # preview from what was written
    rgb = np.zeros((64, 256, 3), np.uint8)
    for ty in range(8):
        for tx in range(32):
            t = img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]; rgb[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = pal[t]
    previews.append(rgb); report[name] = dict(tiles=len(new), merge=merge, palette=pal_no, zoom=round(float(z), 2), crop=box, eye_px=int(em.sum()))
F[40] = lz10_enc(bytes(g40)) if F[40][:1] == b'\x10' else bytes(g40)
F[39] = lz10_enc(bytes(p39)) if F[39][:1] == b'\x10' else bytes(p39)
open(DST, 'wb').write(pack(F))
Image.fromarray(np.vstack(previews)).save(os.environ.get('PREVIEW', os.path.join(HERE, 'strips_preview.png')))
print(json.dumps(report), 'pool', len(pool), 'left', len(free))
