"""Tropical night for opening scene 1 (own art, drawn by code).
Writes night/art/: top.png (sub screen sky), bottom.png (main BG3: sky, moon glow, clouds, islands, sea),
far.png / near.png (main BG2 / BG1: palms, transparent elsewhere), moon.png (64x64 sprite), preview.png.
All colours are DS 5-bit values times 8, so nothing changes when they are written to the palette."""
import numpy as np, os, math
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'art'); os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1990)
W, H = 256, 192
MX, MY = 128, 97            # where the moon ends up (sprite at 128,96 + last anim offset)
HZ = 164                    # horizon row on the bottom screen

def c5(*v): return np.array(v, np.int32)
# sky ramp, dark -> light (5-bit)
SKY = [c5(1, 1, 3), c5(1, 2, 5), c5(2, 3, 7), c5(3, 4, 9), c5(4, 5, 11), c5(5, 7, 13), c5(6, 8, 15),
       c5(7, 10, 17), c5(9, 12, 19), c5(11, 14, 21), c5(13, 17, 24), c5(16, 20, 26)]
STAR_DIM, STAR, STAR_HI = c5(10, 12, 19), c5(22, 24, 30), c5(31, 31, 27)
CLOUD = [c5(3, 4, 9), c5(5, 6, 12), c5(13, 15, 23), c5(20, 22, 29)]        # shade, body, lit, lit hi
SEA = [c5(2, 3, 8), c5(3, 4, 10), c5(4, 6, 12), c5(6, 8, 15), c5(8, 11, 18)]  # dark .. wave crest
GLIT = [c5(13, 17, 25), c5(21, 25, 31), c5(31, 31, 28)]
ISL = [c5(2, 2, 6), c5(5, 6, 11)]                                          # island body, moonlit rim
LAMP = [c5(31, 24, 10), c5(31, 30, 20), c5(20, 12, 6)]                   # lamp, lamp core, lamp reflection
NEAR = [c5(1, 1, 3), c5(2, 2, 5), c5(5, 7, 12), c5(9, 12, 18)]             # palms near: dark, ring, rim, rim hi
FAR = [c5(2, 3, 7), c5(3, 4, 9), c5(6, 8, 14), c5(10, 13, 19)]             # palms far: lighter (air between)

def bayer_pick(level, x, y):
    """round a continuous level, with a checkerboard only in a thin seam around the band edge"""
    lo = np.floor(level); f = level - lo
    chk = ((x + y) & 1) == 0
    up = np.where(np.abs(f - 0.5) < 0.12, chk, f >= 0.5)
    return (lo + up).astype(int)

yy, xx = np.mgrid[0:H, 0:W]
u = (xx + 0.5 - 128) / 128

def glow_level(x, y):
    r = np.sqrt(((x + 0.5 - MX) / 1.4) ** 2 + (y + 0.5 - MY) ** 2)
    return np.interp(r, [0, 24, 32, 42, 55, 70, 84, 97], [10.4, 10.4, 9.5, 8.5, 7.5, 6.5, 5.0, 2.9], right=0)

def stars(img, mask, n, region, seed, bright_frac=0.25, cross=4):
    r = np.random.default_rng(seed); placed = []
    x0, y0, x1, y1 = region
    tries = 0
    while len(placed) < n and tries < n * 60:
        tries += 1
        x, y = int(r.integers(x0, x1)), int(r.integers(y0, y1))
        if not mask[y, x] or any(abs(x - a) + abs(y - b) < 9 for a, b in placed): continue
        placed.append((x, y))
        k = len(placed)
        if k <= cross and 2 <= x < W - 2 and 2 <= y < img.shape[0] - 2:
            img[y, x] = STAR_HI
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): img[y + dy, x + dx] = STAR
        else:
            img[y, x] = STAR if r.random() < bright_frac else STAR_DIM
    return placed

# ------------------------------------------------------------------ top screen: deep sky + stars + a faint star band
top = np.zeros((H, W, 3), np.int32)
yt = yy + 16 * (1 - u ** 2)
lvt = bayer_pick(np.clip(yt / 200 * 3.0, 0, 3.0), xx, yy)
for k in range(4): top[lvt == k] = SKY[k]
band = np.abs((yy - 150) - (xx - 40) * (-0.45)) < 22          # a faint band of small stars across the sky
stars(top, np.ones((H, W), bool), 70, (2, 2, W - 2, H - 2), 7, 0.3, 6)
r2 = np.random.default_rng(11)
for _ in range(220):
    x, y = int(r2.integers(0, W)), int(r2.integers(0, H))
    if band[y, x] and (top[y, x] == SKY[lvt[y, x]]).all(): top[y, x] = STAR_DIM

# ------------------------------------------------------------------ bottom screen BG3: sky, glow, clouds, islands, sea
bot = np.zeros((H, W, 3), np.int32)
ye = yy + 18 * (1 - u ** 2)
lv = 3 + 4.4 * np.clip(ye / 175, 0, 1) ** 1.25
lv = np.maximum(lv, glow_level(xx, yy))
lvq = np.clip(bayer_pick(lv, xx, yy), 0, 11)
for k in range(12): bot[lvq == k] = SKY[k]
skymask = (yy < HZ)
far_from_moon = np.sqrt(((xx - MX) / 1.3) ** 2 + (yy - MY) ** 2) > 62
stars(bot, skymask & far_from_moon & (lvq <= 6) & (yy < 120), 34, (2, 2, W - 2, 120), 3, 0.3, 3)

# clouds (v14, after Ho-Oh's scene): layers of cumulus. A pale, see-through back layer sits higher and further out; the
# front banks are denser. Highlights are see-through too: each layer is blended over what is below it (sky or the back
# layer) and the result snapped to the scene's own colours, so the sky's glow shows through the clouds in bands.
CLOUD = [c5(3, 4, 9), c5(5, 6, 13), c5(8, 10, 17), c5(12, 14, 21), c5(18, 20, 26), c5(26, 26, 26)]
LAYERS = [
    dict(alpha=(0.35, 0.55), banks=[   # back: big soft shapes, higher, mostly see-through
        dict(base=60, puffs=[(26, 46, 22, 9), (50, 40, 18, 10), (8, 52, 14, 7), (70, 49, 20, 5), (96, 52, 16, 3)]),
        dict(base=54, puffs=[(230, 40, 22, 9), (206, 34, 18, 10), (248, 46, 14, 7), (186, 43, 20, 5), (160, 46, 16, 3)]),
        dict(base=20, puffs=[(140, 15, 16, 4), (124, 17, 12, 3), (158, 17, 10, 2.5)])]),
    dict(alpha=(0.85, 0.6), banks=[    # front: the banks, highlights at 60 %
        dict(base=73, puffs=[(18, 62, 15, 10), (36, 55, 14, 12), (52, 60, 12, 9), (8, 67, 10, 7), (28, 66, 14, 7),
                             (66, 67, 16, 4.5), (84, 70, 14, 3), (98, 72, 9, 2)]),
        dict(base=66, puffs=[(238, 55, 15, 10), (220, 48, 14, 12), (204, 53, 12, 9), (250, 60, 10, 7), (228, 59, 14, 7),
                             (190, 60, 16, 4.5), (172, 63, 14, 3), (158, 65, 9, 2)]),
        dict(base=29, puffs=[(106, 24, 7, 4.5), (116, 23, 6, 5), (126, 26, 9, 2.2), (96, 27, 7, 2)]),
        dict(base=30, puffs=[(166, 25, 6, 4), (175, 24, 5, 4.5), (184, 27, 8, 2), (158, 28, 6, 1.8)])]),
]
S4 = 4
hy, hx = np.mgrid[0:H * S4, 0:W * S4] / S4
dist_moon = np.hypot((xx - MX) / 1.3, yy - MY)
SNAP = np.array(SKY + CLOUD)
def down(a): return a.reshape(H, S4, W, S4).mean((1, 3))
cloud_any = np.zeros((H, W), bool)
for L_ in LAYERS:
    hgt = np.full((H * S4, W * S4), -1.0)
    for bk in L_['banks']:
        for (cx, cy, rx, ry) in bk['puffs']:
            d2 = ((hx - cx) / rx) ** 2 + ((hy - cy) / ry) ** 2
            dome = np.sqrt(np.clip(1 - d2, 0, None)) * ry
            hgt = np.where((d2 < 1) & (hy < bk['base']), np.maximum(hgt, dome), hgt)
    cm4 = hgt >= 0
    gy, gx = np.gradient(np.where(cm4, hgt, 0))
    nrm = np.stack([-gx, -gy, np.full_like(hgt, 1.6)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    lx, ly = MX - hx, (MY + 30) - hy; ln = np.hypot(lx, ly) + 1e-6
    lam = nrm[..., 0] * lx / ln * 0.85 + nrm[..., 1] * ly / ln * 0.85 + nrm[..., 2] * 0.35
    near = np.clip(1 - np.hypot((hx - MX) / 1.3, hy - MY) / 150, 0, 1)
    tone = lam * 0.75 + near * 0.45 - 0.22
    cm = down(cm4.astype(float)) > 0.5
    tq = down(np.where(cm4, tone, 0)) / np.maximum(down(cm4.astype(float)), 1e-6)
    k = 1 + np.digitize(tq, [-0.05, 0.25])
    db = np.full((H, W), 99)
    for y_ in range(H - 2, -1, -1):
        db[y_] = np.where(cm[y_], np.where(cm[y_ + 1], db[y_ + 1] + 1, 0), 99)
    dt = np.full((H, W), 99)
    for y_ in range(1, H):
        dt[y_] = np.where(cm[y_], np.where(cm[y_ - 1], dt[y_ - 1] + 1, 0), 99)
    k = np.where(cm & (db <= 3), np.maximum(k, 3), k)
    k = np.where(cm & (db <= 1), np.where(dist_moon < 115, 4, 3), k)
    k = np.where(cm & (db == 0) & (dist_moon < 85), 5, k)
    k = np.where(cm & (dt <= 2) & (db > 3), np.minimum(k, 2), k)
    k = np.where(cm & (dt <= 1) & (db > 2), 1, k)
    a_body, a_hi = L_['alpha']
    alpha = np.where(k >= 4, a_hi, np.where(k == 3, (a_body + a_hi) / 2, a_body))
    col = np.array(CLOUD)[k].astype(float)
    mix = bot.astype(float) * (1 - alpha[..., None]) + col * alpha[..., None]
    # snap to the scene's colours (5-bit values times 8): keeps the palette small
    d = ((mix[..., None, :] - SNAP[None, None]) ** 2).sum(-1)
    snapped = SNAP[d.argmin(-1)]
    bot[cm] = snapped[cm]
    cloud_any |= cm
cm = cloud_any

def rim(mask, lx, ly, steps=1):
    """pixels of mask whose neighbour toward the light point is outside the mask"""
    out = np.zeros_like(mask)
    ys, xs = np.nonzero(mask)
    dx = lx - xs; dy = ly - ys; n = np.hypot(dx, dy) + 1e-6
    for s in range(1, steps + 1):
        qx = np.clip(np.round(xs + dx / n * s).astype(int), 0, mask.shape[1] - 1)
        qy = np.clip(np.round(ys + dy / n * s).astype(int), 0, mask.shape[0] - 1)
        out[ys, xs] |= ~mask[qy, qx]
    return out

# islands on the horizon (silhouettes with a moonlit top edge), tiny palms, a harbour with lamps
xs_ = np.arange(W) + 0.5
hl = 7.5 * np.exp(-((xs_ - 34) / 24) ** 2) + 3.5 * np.exp(-((xs_ - 72) / 13) ** 2)
hr = 15 * np.exp(-((xs_ - 234) / 20) ** 2) + 6.5 * np.exp(-((xs_ - 198) / 16) ** 2) + 3 * np.exp(-((xs_ - 176) / 8) ** 2)
hgt = np.where(xs_ < 100, hl, np.where(xs_ > 160, hr, 0))
isl = (yy < HZ) & (yy >= HZ - np.round(hgt)[None, :]) & (hgt[None, :] >= 0.8)
def tiny_palm(m, x, y, h, lean):
    for k in range(h):
        m[y - k, x + int(round(lean * k * k / (h * h) * 2))] = True
    tx, ty = x + int(round(lean * 2)), y - h
    for (dx, dy) in ((-3, 1), (-2, 0), (-1, 0), (1, 0), (2, 0), (3, 1), (-2, -1), (2, -1), (0, -1), (-4, 2), (4, 2)):
        m[ty + dy, tx + dx] = True
for (x, base, h, lean) in ((20, HZ - 6, 7, -1), (29, HZ - 7, 9, 1), (37, HZ - 7, 6, 1), (64, HZ - 3, 7, -1), (222, HZ - 14, 8, 1), (244, HZ - 12, 7, -1)):
    tiny_palm(isl, x, base, h, lean)
# harbour: little houses and a lighthouse on the right island
for (x0, x1, h) in ((186, 191, 9), (192, 196, 11), (197, 203, 8), (205, 209, 10)):
    isl[HZ - h:HZ, x0:x1] = True
isl[HZ - 16:HZ, 174:176] = True; isl[HZ - 18:HZ - 16, 173:177] = True
bot[isl] = ISL[0]
ir = isl & ~np.roll(isl, 1, 0)                                     # top edge
bot[ir & (yy < HZ)] = ISL[1]
lamps = [(175, HZ - 17, 1), (188, HZ - 5, 0), (194, HZ - 7, 0), (199, HZ - 4, 0), (207, HZ - 6, 0), (194, HZ - 4, 0)]
for (x, y, big) in lamps:
    bot[y, x] = LAMP[1] if big else LAMP[0]
    if big:
        for dx, dy in ((1, 0), (-1, 0), (0, -1)): bot[y + dy, x + dx] = LAMP[0]

# sea: lighter near the horizon, wave streaks spaced out toward the viewer, the moon's glitter path
for y in range(HZ, H):
    t = (y - HZ) / (H - HZ)
    lvl = 2.6 - 2.4 * t
    for x in range(W):
        k = int(np.clip(round(lvl + (0.5 if ((x + y) & 1) and abs(lvl - round(lvl)) > 0.38 else 0)), 0, 2))
        bot[y, x] = SEA[k]
rs = np.random.default_rng(5)
wave_rows = [HZ + 1, HZ + 3, HZ + 5, HZ + 8, HZ + 11, HZ + 15, HZ + 19, HZ + 24]
for i, y in enumerate(wave_rows):
    if y >= H: continue
    x = int(rs.integers(0, 12))
    while x < W:
        L = int(rs.integers(4, 10 + 3 * i)); gap = int(rs.integers(6, 16 + 3 * i))
        bot[y, x:x + L] = SEA[3]
        if i >= 3 and L > 6: bot[y - 1, x + 2:x + L - 2] = SEA[4] if i >= 5 else SEA[3]
        x += L + gap
for y in range(HZ, H):
    t = (y - HZ) / (H - HZ)
    hw = 3 + 46 * t ** 1.15
    x = MX - hw
    while x < MX + hw:
        L = int(rs.integers(2, 4 + int(10 * t))); gap = int(rs.integers(1, 3 + int(6 * t)))
        if (y - HZ) % 2 == 0 or t > 0.3:
            c = abs(x + L / 2 - MX) / hw
            col = GLIT[2] if c < 0.25 else GLIT[1] if c < 0.6 else GLIT[0]
            xa, xb = int(x), int(min(x + L, MX + hw))
            bot[y, xa:xb] = col
        x += L + gap
# lamp reflections: short warm dashes under each lamp
for (x, y, big) in lamps:
    for k, yy_ in enumerate(range(HZ + 1, HZ + 9 + 6 * big)):
        if rs.random() < 0.7: bot[yy_, x - (k % 2):x + 1] = LAMP[2] if k > 3 else LAMP[0]

# ------------------------------------------------------------------ palms (BG2 far, BG1 near)
S = 4
def palm(d, base, top, bend, w0, w1, fronds, flen, seed, fw=4.5):
    """trunk: quadratic curve with taper; fronds: drooping ribs with leaflets. Draws at S x scale."""
    r = np.random.default_rng(seed)
    bx, by = base; tx, ty = top
    mx, my = (bx + tx) / 2, (by + ty) / 2
    nx, ny = -(ty - by), (tx - bx); nn = math.hypot(nx, ny); nx, ny = nx / nn, ny / nn
    cx, cy = mx + nx * bend, my + ny * bend
    P = lambda t: ((1 - t) ** 2 * bx + 2 * (1 - t) * t * cx + t * t * tx, (1 - t) ** 2 * by + 2 * (1 - t) * t * cy + t * t * ty)
    left, right, rings = [], [], []
    N = 40
    for i in range(N + 1):
        t = i / N; x, y = P(t); x2, y2 = P(min(1, t + 0.01)); x1, y1 = P(max(0, t - 0.01))
        dx, dy = x2 - x1, y2 - y1; n = math.hypot(dx, dy); px, py = -dy / n, dx / n
        w = (w0 + (w1 - w0) * t) / 2
        left.append(((x + px * w) * S, (y + py * w) * S)); right.append(((x - px * w) * S, (y - py * w) * S))
        if i % 3 == 1: rings.append(((x + px * w) * S, (y + py * w) * S, (x - px * w) * S, (y - py * w) * S))
    d['trunk'].polygon(left + right[::-1], fill=255)
    for (a, b, c_, e) in rings: d['ring'].line((a, b, c_, e), fill=255, width=S)
    # crown: coconuts + fronds
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        ccx, ccy = tx + math.cos(a) * 1.8, ty + 2 + math.sin(a) * 1.2
        d['frond'].ellipse(((ccx - 2.0) * S, (ccy - 2.0) * S, (ccx + 2.0) * S, (ccy + 2.0) * S), fill=255)
    for (ang, droop, lf) in fronds:
        L = flen * lf
        a = math.radians(ang)
        n = max(12, int(L))
        pts = [(tx + L * (i / n) * math.cos(a), ty + L * (i / n) * math.sin(a) + droop * L * (i / n) ** 2) for i in range(n + 1)]
        up, lo = [], []
        for i in range(n + 1):
            s_ = i / n
            (x0, y0), (x1, y1) = pts[max(0, i - 1)], pts[min(n, i + 1)]
            dx, dy = x1 - x0, y1 - y0; m = math.hypot(dx, dy) + 1e-6; dx, dy = dx / m, dy / m
            nx_, ny_ = -dy, dx
            if ny_ < 0: nx_, ny_ = -nx_, -ny_          # normal pointing down
            w = fw * (1 - s_) ** 0.8 * (0.55 + 0.45 * math.sin(math.pi * min(1, 0.25 + s_)))
            tooth = (1.9 if (i % 3 == 0 and 0.08 < s_ < 0.95) else 1.0) * (0.9 + 0.25 * r.random())
            x, y = pts[i]
            up.append(((x - nx_ * w * 0.3) * S, (y - ny_ * w * 0.3) * S))
            lo.append(((x + nx_ * w * tooth) * S, (y + ny_ * w * tooth) * S))
        d['frond'].polygon(up + lo[::-1], fill=255)
        d['rib'].line([(x * S, y * S) for x, y in pts[2:int(n * 0.8)]], fill=255, width=S)

def palm_layer(specs, pal, extra=None):
    ims = {k: Image.new('L', (W * S, H * S), 0) for k in ('trunk', 'ring', 'frond', 'rib')}
    d = {k: ImageDraw.Draw(v) for k, v in ims.items()}
    for sp in specs: palm(d, *sp)
    if extra: extra(d)
    m = {k: np.asarray(v.resize((W, H), Image.BOX)) > 110 for k, v in ims.items()}
    solid = m['trunk'] | m['frond']
    img = np.zeros((H, W, 3), np.int32); a = np.zeros((H, W), bool)
    img[solid] = pal[0]; a[solid] = True
    img[m['trunk'] & m['ring'] & ~m['frond']] = pal[1]
    img[m['rib'] & m['frond']] = pal[1]
    r1 = rim(solid, MX, MY - 30, 1)
    r2 = rim(solid, MX, MY - 30, 2) & ~r1 & m['trunk'] & ~m['frond']
    img[r2] = pal[2]
    near_side = np.hypot(xx - MX, yy - MY) < 120
    img[r1] = np.where(near_side[r1][:, None], pal[3], pal[2])
    a[192 - 0:, :] = False
    return img, a

def bushes(spec):
    def f(d):
        for (cx, cy, rx, ry, ang) in spec:
            # a broad leaf: ellipse rotated, drawn as a polygon
            pts = []
            for i in range(24):
                t = 2 * math.pi * i / 24
                x, y = rx * math.cos(t), ry * math.sin(t)
                ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                pts.append(((cx + x * ca - y * sa) * S, (cy + x * sa + y * ca) * S))
            d['frond'].polygon(pts, fill=255)
    return f

FRONDS_L = [(-172, 0.75, 0.95), (-145, 0.9, 0.9), (-112, 1.5, 0.7), (-80, 1.55, 0.75), (-50, 1.0, 0.95), (-22, 0.8, 1.05), (5, 0.7, 1.0), (32, 0.6, 0.75), (150, 0.6, 0.7)]
FRONDS_R = [(-180 - a, dr, lf) for (a, dr, lf) in FRONDS_L]
far_specs = [((30, 196), (52, 122), -6, 5.5, 3.5, FRONDS_L, 30, 1, 3.4),
             ((226, 196), (206, 128), 6, 5.0, 3.2, FRONDS_R, 27, 2, 3.2)]
far_img, far_a = palm_layer(far_specs, FAR, bushes([(8, 186, 18, 6, -8), (36, 190, 16, 5, 6), (250, 184, 16, 6, 10), (222, 190, 18, 5, -6)]))
near_specs = [((-8, 200), (38, 72), 14, 11, 6, FRONDS_L, 50, 3, 5.0),
              ((262, 200), (220, 80), -14, 10.5, 5.5, FRONDS_R, 47, 4, 4.8)]
near_img, near_a = palm_layer(near_specs, NEAR, bushes([(10, 178, 22, 7, -25), (24, 188, 22, 6, -5), (2, 166, 14, 6, -60),
                                                         (246, 176, 22, 7, 25), (232, 188, 22, 6, 5), (254, 164, 14, 6, 60)]))

# ------------------------------------------------------------------ moon sprite 64x64
M = np.zeros((64, 64, 3), np.int32); Ma = np.zeros((64, 64), bool)
my_, mx_ = np.mgrid[0:64, 0:64]
rr = np.hypot(mx_ + 0.5 - 32, my_ + 0.5 - 32)
MOON = [c5(29, 29, 26), c5(31, 31, 29), c5(25, 26, 25), c5(22, 23, 24), c5(27, 27, 25)]   # base, bright, mare, mare dark, limb
for (r0, r1_, col) in ((21.5, 25.0, SKY[10]), (18.5, 21.5, SKY[11])):
    ring = (rr >= r0) & (rr < r1_); M[ring] = col; Ma[ring] = True
disc = rr < 18.5
M[disc] = MOON[0]; Ma[disc] = True
M[disc & (rr > 16.8)] = MOON[4]
# maria: soft blobs (own shapes)
for (cx, cy, rx, ry, k) in ((36, 25, 7, 5, 2), (41, 32, 4, 4.5, 2), (26, 31, 4, 6.5, 2), (23, 39, 3.5, 2.2, 2), (34, 41, 2.2, 2, 2),
                             (37, 24, 3.5, 2.5, 3), (27, 34, 2, 3, 3)):
    e = (((mx_ + 0.5 - cx) / rx) ** 2 + ((my_ + 0.5 - cy) / ry) ** 2) < 1
    M[disc & e] = MOON[k]
for (cx, cy) in ((34, 42), (22, 34), (41, 21)):
    M[cy, cx] = MOON[1]; M[cy - 1, cx] = MOON[1]
hl = disc & (np.hypot(mx_ + 0.5 - 27, my_ + 0.5 - 22) < 5) & (M == MOON[0]).all(-1)
M[hl] = MOON[1]

def save(name, img, a=None):
    rgb = (img * 8).astype(np.uint8)
    if a is None: Image.fromarray(rgb).save(os.path.join(OUT, name))
    else:
        Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)])).save(os.path.join(OUT, name))
save('top.png', top); save('bottom.png', bot); save('far.png', far_img, far_a); save('near.png', near_img, near_a)
save('moon.png', M, Ma)

# preview: both screens, end of the scroll (BG1 down 32, BG2 down 16), moon at its last spot
def comp(base, lay, a, dy):
    out = base.copy()
    sh = np.roll(lay, dy, 0); sa = np.roll(a, dy, 0); sa[:dy] = False
    out[sa] = sh[sa]; return out
b2 = comp(bot, far_img, far_a, 16); b2 = comp(b2, near_img, near_a, 32)
mo = np.zeros_like(bot); ma = np.zeros((H, W), bool)
mo[MY - 32:MY + 32, MX - 32:MX + 32] = M; ma[MY - 32:MY + 32, MX - 32:MX + 32] = Ma
b2[ma] = mo[ma]
b0 = comp(bot, far_img, far_a, 0); b0 = comp(b0, near_img, near_a, 0)
mo0 = np.zeros_like(bot); ma0 = np.zeros((H, W), bool)
mo0[MY - 1:MY + 63, MX - 32:MX + 32] = M; ma0[MY - 1:MY + 63, MX - 32:MX + 32] = Ma
b0[ma0] = mo0[ma0]
pv = np.concatenate([np.concatenate([top, b0], 0), np.zeros((384, 8, 3), np.int32) + 31, np.concatenate([top, b2], 0)], 1)
Image.fromarray((pv * 8).astype(np.uint8)).resize((pv.shape[1] * 2, pv.shape[0] * 2), Image.NEAREST).save(os.path.join(OUT, 'preview.png'))
print('ok')
