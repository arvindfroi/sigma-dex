"""Gravriel's scene v10 (Arvind: "the moon must go up, the foreground down; the clouds and the water stand still").
- BG3 (never scrolls): sky, all clouds, far wrecks, sea, horizon fog
- BG2 (rises 16 px, patch 0x22f2): only the moon and its glow, painted 16 map rows lower
- BG1 (sinks 32 px, the game's own scroll again, like Ho-Oh's near trees): the near wreckage, painted 32 map rows
  higher and running off the bottom of the screen the whole time
- the water in front of his waist is no longer on BG1: build_grav4.py draws it as a strip in his own sprite
  (palette 2; the sprites load 3 palettes, patch 0x270a), in front of his body
Writes night/art_grav10/.  --- v9:
Gravriel's scene v9 (Arvind: "the others have landscape in the foreground, it helps the parallax; a shipwreck
or something fitting"): near wreckage at both edges on BG2 (a broken mast with a crow's nest, torn sail and ropes on
the left; a hull's ribs and a broken bowsprit on the right). It rises with the moon; the near water on BG1 hides its
foot. BG2 is 256 map rows here so the wreckage reaches the bottom when the layer has risen. Writes night/art_grav9/.
--- v8:
Gravriel's scene v8 (Arvind 2026-11-14: "there is no movement at all in Gravriel's background; the others have
it"): the moon, its glow and the high clouds are on BG2, which a code patch (grav/patch_prio.py, 0x22f2) now lifts
16 px during the scroll, the way the sun rises in Ho-Oh's scene. They are painted 16 rows lower in the map so they end
where they were. The sky gradient, stars, low clouds, wrecks, fog and sea stay on BG3; the water in front on BG1.
Writes night/art_grav8/.   --- v7:
Gravriel's scene v7, after Arvind's notes on v6 (2026-11-14):
- the wrecks floated above the horizon (they were on BG2, which scrolls): they are painted into the sky picture (BG3,
  which never moves), standing on the horizon
- clouds like Ho-Oh's (night/skykit.py wisps): thin banks with puffy tops and pointed tails, lit on the side facing
  the moon; a thin veil crosses the moon's lower part
- a cleaner moon: a disc with faint maria and two halo rings, a round glow (was a wide oval)
- the horizon bends like Ho-Oh's and Lugia's (a wide-angle lens): lower in the middle, 6 px higher at the edges
- BG1 still holds an exact copy of the sea from his waterline WROW down (v6), and no longer scrolls (code patch)
Writes night/art_grav7/ (top, bottom, far, near, moon, preview)."""
import numpy as np, os, math
from PIL import Image, ImageDraw
import sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from skykit import hz_curve, warp_sea, wisps, wisps2, moon_sprite, moon2, moon3, moon4, glow_levels, feather_pick, U as UCOL
OUT = os.path.join(HERE, os.environ.get('GRAV_ART', 'art_grav10')); os.makedirs(OUT, exist_ok=True)
W, H = 256, 192
MX, MY = 128, 52
WROW = int(os.environ.get('GRAV_WROW', 178))
HZ = 164
HZX = hz_curve(HZ, 6.0)


def c5(*v): return np.array(v, np.int32)


SKY = [c5(0, 1, 2), c5(1, 1, 3), c5(1, 2, 4), c5(2, 3, 5), c5(2, 4, 6), c5(3, 5, 7), c5(4, 6, 8),
       c5(5, 8, 9), c5(6, 10, 10), c5(8, 12, 11), c5(10, 14, 12), c5(12, 16, 14)]
STAR_DIM, STAR, STAR_HI = c5(3, 5, 7), c5(6, 9, 11), c5(10, 13, 14)
SEA = [c5(0, 1, 3), c5(1, 2, 4), c5(1, 3, 5), c5(2, 5, 6), c5(4, 7, 8)]
GLIT = [c5(6, 10, 10), c5(10, 15, 13), c5(15, 21, 17)]
CLOUD = [c5(1, 3, 4), c5(3, 5, 6), c5(5, 8, 8), c5(8, 11, 10), c5(11, 15, 13), c5(15, 19, 16)]
WISP = [c5(1, 2, 4), c5(4, 6, 7), c5(11, 15, 13), c5(18, 23, 19)]       # shade, body, lit, bright edge
WISP_FAR = [c5(3, 5, 6), c5(5, 8, 8), c5(8, 12, 11), c5(12, 17, 15)]  # low banks: paler, in the haze
MOONC = [c5(18, 23, 19), c5(22, 27, 22), c5(16, 21, 17), c5(15, 20, 16)]   # base, bright, mare, limb
WRECK = [c5(2, 4, 5), c5(3, 6, 7), c5(6, 10, 10), c5(9, 13, 12)]          # far in the fog: pale, low contrast
yy, xx = np.mgrid[0:H, 0:W]
u = (xx + 0.5 - 128) / 128


def stars(img, mask, n, region, seed, bright_frac=0.25, cross=4):
    r = np.random.default_rng(seed); placed = []
    x0, y0, x1, y1 = region
    tries = 0
    while len(placed) < n and tries < n * 60:
        tries += 1
        x, y = int(r.integers(x0, x1)), int(r.integers(y0, y1))
        if not mask[y, x] or any(abs(x - a) + abs(y - b) < 9 for a, b in placed): continue
        placed.append((x, y))
        if len(placed) <= cross and 2 <= x < W - 2 and 2 <= y < img.shape[0] - 2:
            img[y, x] = STAR_HI
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): img[y + dy, x + dx] = STAR
        else:
            img[y, x] = STAR if r.random() < bright_frac else STAR_DIM


# ------------------------------------------------------------------ top screen: deep sky + stars (as v6)
top = np.zeros((H, W, 3), np.int32)
yt = yy + 16 * (1 - u ** 2)
lvt = feather_pick(np.clip(yt / 200 * 3.0, 0, 3.0), 4)
for k in range(4): top[lvt == k] = SKY[k]
band = np.abs((yy - 150) - (xx - 40) * (-0.45)) < 22
stars(top, np.ones((H, W), bool), 70, (2, 2, W - 2, H - 2), 7, 0.3, 6)
r2 = np.random.default_rng(11)
for _ in range(220):
    x, y = int(r2.integers(0, W)), int(r2.integers(0, H))
    if band[y, x] and (top[y, x] == SKY[lvt[y, x]]).all(): top[y, x] = STAR_DIM

# ------------------------------------------------------------------ bottom screen BG3
bot = np.zeros((H, W, 3), np.int32)
ye = yy + 20 * (1 - u ** 2)                      # the bands arc like Ho-Oh's sky
lv = 3 + 4.4 * np.clip(ye / 175, 0, 1) ** 1.25
lv0 = lv.copy()
lvq0 = np.clip(feather_pick(lv0, 5), 0, 11)
lv = np.maximum(lv, glow_levels(MX, MY, [0, 18, 22, 28, 36, 46], [9.0, 9.0, 7.8, 6.4, 5.0, 3.4]))
lvq = np.clip(feather_pick(lv, 5), 0, 11)
base = np.zeros_like(bot)
for k in range(12): base[lvq0 == k] = SKY[k]
for k in range(12): bot[lvq == k] = SKY[k]
far_from_moon = np.hypot(xx - MX, yy - MY) > 60
stars(bot, (yy < 120) & far_from_moon & (lvq <= 6), 30, (2, 2, W - 2, 120), 3, 0.3, 3)
stars(base, (yy < 120) & far_from_moon & (lvq <= 6), 30, (2, 2, W - 2, 120), 3, 0.3, 3)

# the moon, part of the sky picture (BG3): the sun sprite is Gravriel
# v10 (Arvind: "the moon's content did not look good, just round blobs; it should be better"): a real surface,
# maria where the Moon's are, a bright rayed crater low down, light from the upper left. Size and rings as v7.
# v11 (Arvind: "still odd, as if squares and circles were thrown in"): skykit.moon4 paints it as a continuous picture
# v12 (Arvind: "make the markings less visible or lighter, the contrast is high"): shallower maria, lighter dark tones
M, Ma, _ = moon4(15.0, [c5(17, 22, 18), c5(18, 24, 20), c5(19, 25, 21), c5(20, 26, 22), c5(22, 28, 23), c5(24, 30, 25)],
                 [(2.0, c5(13, 17, 15)), (2.5, c5(10, 14, 13))], depth=0.26)
bot[MY - 32:MY + 32, MX - 32:MX + 32][Ma] = M[Ma]

# clouds: high banks either side of the moon (lit underneath and on the inner tips), low banks near the horizon
# (lit on top), and a veil over the moon's lower part
HIGH = [(36, 34, 110, 15, 5, 1), (10, 43, 64, 5.0, 1, 2), (66, 45, 54, 5.0, 2, 3), (52, 49, 70, 6.0, 2, 9),
        (220, 30, 106, 14, 5, 4), (248, 39, 58, 4.6, 1, 5), (186, 41, 58, 4.6, 2, 6), (204, 45, 66, 5.5, 2, 10),
        (128, 16, 60, 4.0, 2, 7)]
LOW = [(40, 128, 96, 3.0, 1, 11), (206, 122, 104, 3.4, 1, 12), (128, 140, 70, 2.2, 0, 13)]
# v7b (Arvind: "flat, not enough transitions"): soft edges and an 8-step ramp, as in Ho-Oh's clouds
RAMP = [c5(0, 1, 2), c5(1, 3, 4), c5(3, 5, 6), c5(5, 8, 8), c5(8, 12, 10), c5(11, 15, 12), c5(14, 19, 15), c5(18, 23, 18)]
RAMP_LOW = [c5(2, 3, 5), c5(3, 5, 6), c5(4, 6, 7), c5(5, 8, 8), c5(6, 9, 9), c5(8, 11, 10), c5(10, 14, 12), c5(12, 16, 14)]
# v8: everything that differs from the plain sky above row 100 (moon, glow, high clouds) goes to BG2, 16 rows lower in
# the map (BG2 ends the scroll lifted 16 px); BG3 keeps the plain sky there
RISE = 16
sky_part = (yy < 100) & (bot != base).any(-1)
far_img = np.zeros((H, W, 3), np.int32); far_a = np.zeros((H, W), bool)
far_img[RISE:][sky_part[:-RISE]] = bot[:-RISE][sky_part[:-RISE]]; far_a[RISE:] = sky_part[:-RISE]
bot = np.where((yy < 100)[..., None], base, bot)
# v10: all clouds stay on BG3 (still); BG2 holds only the moon and its glow
wisps2(bot, HIGH, (MX, MY + 80), RAMP, reach=200, lit_depth=10, seed=4)
wisps2(bot, LOW, (MX, MY), RAMP_LOW, reach=220, lit_depth=4, seed=3)
# (v8b: no veil in front of the moon, Arvind asked for it gone)

# wrecks on the horizon (BG3 does not scroll), drawn at 4x and shrunk
S = 4


def wreck_draw(d, base, top_, yards, rags, seed, w0, w1):
    r = np.random.default_rng(seed)
    (bx, by), (tx, ty) = base, top_
    dx, dy = tx - bx, ty - by; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; px, py = -uy, ux
    poly = [((bx + px * w0 / 2) * S, (by + py * w0 / 2) * S), ((tx + px * w1 / 2) * S, (ty + py * w1 / 2) * S),
            ((tx - px * w1 / 2 + ux * 2) * S, (ty - py * w1 / 2 + uy * 2) * S), ((bx - px * w0 / 2) * S, (by - py * w0 / 2) * S)]
    d['solid'].polygon(poly, fill=255)
    for (t, half, tilt) in yards:
        cx, cy = bx + dx * t, by + dy * t
        a = math.radians(tilt); ex, ey = math.cos(a) * half, math.sin(a) * half
        d['solid'].line(((cx - ex) * S, (cy - ey) * S, (cx + ex) * S, (cy + ey) * S), fill=255, width=int(1.8 * S))
        if rags:
            pts = [((cx - ex * 0.9) * S, (cy - ey * 0.9) * S), ((cx + ex * 0.9) * S, (cy + ey * 0.9) * S)]
            n = 9
            for k in range(n, -1, -1):
                s_ = k / n; x = cx + ex * 0.9 * (2 * s_ - 1); y = cy + ey * 0.9 * (2 * s_ - 1)
                drop = half * (0.55 + 0.45 * r.random()) * (0.4 if k % 3 == 0 else 1.0)
                pts.append((x * S, (y + drop) * S))
            d['cloth'].polygon(pts, fill=255)


def hull(d, pts): d['solid'].polygon([(x * S, y * S) for x, y in pts], fill=255)


ims = {k: Image.new('L', (W * S, H * S), 0) for k in ('solid', 'cloth')}
dr = {k: ImageDraw.Draw(v) for k, v in ims.items()}


def hz(x): return HZX[int(np.clip(round(x), 0, W - 1))]


# (x, mast lean, height, yards, rags, seed, widths) + hulls; every piece stands on the curved horizon at its x
for (x, lean, h, yards, rags, seed, w0, w1) in ((36, 6, 36, [(0.6, 9, -8), (0.85, 6, -10)], True, 1, 2.2, 1.2),
                                                 (44, -2, 24, [(0.7, 6, 6)], True, 5, 1.8, 1.0),
                                                 (212, -6, 30, [(0.65, 8, 12)], True, 2, 2.0, 1.1),
                                                 (179, 3, 15, [(0.7, 4, -6)], False, 6, 1.4, 0.8)):
    wreck_draw(dr, (x - lean / 6, hz(x) + 1), (x + lean * 0.8, hz(x) - h), yards, rags, seed, w0, w1)
for xs_ in ((16, 22, 40, 56, 60), (204, 210, 228, 236)):
    ys_ = (3, -3, -5, -2, 3) if len(xs_) == 5 else (3, -2, -3, 3)
    hull(dr, [(x, hz(x) + dy - 1) for x, dy in zip(xs_, ys_)])
mk = {k: np.asarray(v.resize((W, H), Image.BOX)) > 110 for k, v in ims.items()}
solid = (mk['solid'] | mk['cloth']) & (yy < HZX[None, :])
holes = mk['cloth'] & ~mk['solid'] & (np.random.default_rng(9).random((H, W)) < 0.12)
solid &= ~holes
bot[solid] = WRECK[0]
bot[solid & mk['cloth'] & ~mk['solid']] = WRECK[1]
lit_edge = solid & ~np.roll(solid, 1, 0)
bot[lit_edge] = np.where((np.hypot(xx - MX, yy - MY) < 130)[lit_edge][:, None], WRECK[3], WRECK[2])

# sea: painted flat (as v6), then bent onto the curved horizon
flat = np.zeros_like(bot)
for y in range(HZ, H):
    t = (y - HZ) / (H - HZ)
    lvl = 1.9 - 1.8 * t
    for x in range(W):
        k = int(np.clip(round(lvl + (0.5 if ((x + y) & 1) and abs(lvl - round(lvl)) > 0.38 else 0)), 0, 2))
        flat[y, x] = SEA[k]
rs = np.random.default_rng(5)
y = HZ + 1.0
while y < H:
    t = (y - HZ) / (H - HZ); yi = int(y)
    x = -int(rs.integers(0, 20))
    while x < W:
        L = int(rs.integers(3 + int(14 * t), 6 + int(30 * t))); gap = int(rs.integers(4 + int(10 * t), 10 + int(34 * t)))
        bend = 1 if t > 0.35 else 0
        for k in range(L):
            xx_ = x + k
            if not 0 <= xx_ < W: continue
            arc = yi - (bend if L * 0.25 < k < L * 0.75 else 0)
            cmoon = abs(xx_ - MX) / (5 + 46 * t)
            col = GLIT[2] if cmoon < 0.35 else GLIT[1] if cmoon < 0.75 else GLIT[0] if cmoon < 1.1 else SEA[3] if t > 0.25 else SEA[2]
            if arc < H: flat[arc, xx_] = col
            if t > 0.3 and arc + 1 < H: flat[arc + 1, xx_] = SEA[0]
        x += L + gap
    y += 1.2 + 5.5 * t * t + 1.2 * t
for y in range(HZ, HZ + 3):                                   # haze on the far water
    m = ((xx[y] + y) % 2 == 0) if y == HZ + 2 else np.ones(W, bool)
    flat[y][m] = CLOUD[2] if y < HZ + 2 else CLOUD[1]
warp_sea(flat, bot, HZX, HZ)

# a low fog bank lying on the horizon, see-through, following the curve (v5's, kept)
S4 = 4
hy, hx = np.mgrid[0:H * S4, 0:W * S4] / S4
hgt = np.full((H * S4, W * S4), -1.0)
for x in range(-10, 270, 18):
    cx, cy = x, 157 + 3 * math.sin(x / 23.0) - 6.0 * ((x - 128) / 128) ** 2
    rx, ry = 22 + 6 * math.sin(x / 17.0), 6 + 2 * math.cos(x / 13.0)
    d2 = ((hx - cx) / rx) ** 2 + ((hy - cy) / ry) ** 2
    base = 165 - 6.0 * ((hx - 128) / 128) ** 2
    hgt = np.where((d2 < 1) & (hy < base), np.maximum(hgt, np.sqrt(np.clip(1 - d2, 0, None)) * ry), hgt)
fm = (hgt >= 0).reshape(H, S4, W, S4).mean((1, 3)) > 0.5
top_edge = fm & ~np.roll(fm, 1, 0)
FS = np.array(CLOUD + MOONC + WRECK)
mix = bot.astype(float) * 0.4 + np.array(CLOUD[2], float) * 0.6
mix[top_edge] = bot[top_edge] * 0.3 + np.array(CLOUD[4], float) * 0.7
d = ((mix[..., None, :] - FS[None, None]) ** 2).sum(-1)
snapped = FS[d.argmin(-1)]
bot[fm] = snapped[fm]

# BG2: empty now (the wrecks moved to BG3). BG1: the water in front of him, an exact copy of the sea (v6)
near_img = np.zeros((H, W, 3), np.int32); near_a = np.zeros((H, W), bool)
near_img[WROW:] = bot[WROW:]; near_a[WROW:] = True


# ------------------------------------------------------------------ v9: near wreckage (BG2, rises with the moon)
FG = [c5(0, 1, 2), c5(1, 2, 4), c5(4, 7, 7), c5(8, 12, 11)]          # wood, torn cloth, moonlit edge, bright edge
S4 = 4
SINK = 32
fims = {k: Image.new('L', (W * S4, (H + SINK) * S4), 0) for k in ('wood', 'cloth')}
fd = {k: ImageDraw.Draw(v) for k, v in fims.items()}
def P(pts): return [(x * S4, y * S4) for x, y in pts]
def pole(a, b, w0, w1, layer='wood'):
    (ax, ay), (bx, by) = a, b; dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy); px, py = -dy / L, dx / L
    fd[layer].polygon(P([(ax + px * w0 / 2, ay + py * w0 / 2), (bx + px * w1 / 2, by + py * w1 / 2),
                         (bx - px * w1 / 2, by - py * w1 / 2), (ax - px * w0 / 2, ay - py * w0 / 2)]), fill=255)
def rope(a, b, sag, w=1.0):
    pts = []
    for i in range(25):
        t = i / 24; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t + sag * 4 * t * (1 - t)
        pts.append((x, y))
    fd['wood'].line(P(pts), fill=255, width=max(1, int(w * S4)))
rr_ = np.random.default_rng(31)
def rag(x0, y0, x1, y1, drop):                       # torn cloth hanging from a yard between (x0,y0) and (x1,y1)
    pts = [(x0, y0), (x1, y1)]
    n = 10
    for k in range(n, -1, -1):
        t = k / n; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
        pts.append((x, y + drop * (0.45 + 0.55 * rr_.random()) * (0.35 if k % 4 == 1 else 1.0)))
    fd['cloth'].polygon(P(pts), fill=255)
# left: a broken mast leaning in from the lower left, a crow's nest, a slanting yard with a torn sail, ropes
pole((6, 226), (31, 86), 8.0, 4.5)
fd['wood'].polygon(P([(21, 97), (41, 95), (40, 103), (23, 105)]), fill=255)          # crow's nest
fd['wood'].polygon(P([(31, 86), (35, 80), (33, 87)]), fill=255)                       # splintered top
pole((-6, 126), (44, 112), 2.6, 2.0)                                                  # yard
rag(2, 124, 40, 114, 30)
rope((31, 90), (-2, 150), 6); rope((29, 100), (-2, 178), 8); rope((40, 112), (46, 226), 3, 0.8)
# right: a hull's ribs curving up out of the water, a broken bowsprit with a rope
for (bx, top_y, lean, w) in ((262, 120, -26, 5.0), (250, 132, -20, 4.2), (238, 146, -14, 3.6), (227, 160, -9, 3.0)):
    pts = [(bx + lean * (1 - (1 - t) ** 2) , 226 - (226 - top_y) * t) for t in np.linspace(0, 1, 30)]
    for (a, b) in zip(pts[:-1], pts[1:]): pole(a, b, w, w * 0.92)
pole((262, 150), (218, 116), 4.5, 2.4)
rope((219, 118), (262, 176), 9, 0.9)
fm = {k: np.asarray(v.resize((W, H + SINK), Image.BOX)) > 110 for k, v in fims.items()}
solid = fm['wood'] | fm['cloth']
holes = fm['cloth'] & ~fm['wood'] & (np.random.default_rng(9).random(solid.shape) < 0.10)
solid &= ~holes
fy, fx = np.mgrid[0:H + SINK, 0:W]
fg = np.zeros((H + SINK, W, 3), np.int32)
fg[solid] = FG[0]; fg[solid & fm['cloth'] & ~fm['wood']] = FG[1]
ys_, xs_ = np.nonzero(solid)
dx_, dy_ = MX - xs_, MY - ys_; n_ = np.hypot(dx_, dy_) + 1e-6
qx = np.clip(np.round(xs_ + dx_ / n_).astype(int), 0, W - 1); qy = np.clip(np.round(ys_ + dy_ / n_).astype(int), 0, H + SINK - 1)
edge = ~solid[qy, qx]
fg[ys_[edge], xs_[edge]] = np.where((ys_[edge] < 130)[:, None], FG[3], FG[2])
far256 = np.zeros((256, W, 3), np.int32); far256a = np.zeros((256, W), bool)
far256[:H] = far_img; far256a[:H] = far_a
far_img, far_a = far256, far256a
# BG1 = the near wreckage only (no water copy any more); map row = final screen row - SINK
near_img = np.zeros((H, W, 3), np.int32); near_a = np.zeros((H, W), bool)
near_img[:] = fg[SINK:SINK + H]; near_a[:] = solid[SINK:SINK + H]

def save(name, img, a=None):
    rgb = (img * 8).astype(np.uint8)
    if a is None: Image.fromarray(rgb).save(os.path.join(OUT, name))
    else: Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)])).save(os.path.join(OUT, name))


save('top.png', top); save('bottom.png', bot); save('far.png', far_img, far_a); save('near.png', near_img, near_a)
save('moon.png', M, Ma)
pv = np.concatenate([top, bot], 0)
Image.fromarray((pv * 8).astype(np.uint8)).resize((W * 3, 384 * 3), Image.NEAREST).save(os.path.join(OUT, 'preview.png'))
print('ok')
