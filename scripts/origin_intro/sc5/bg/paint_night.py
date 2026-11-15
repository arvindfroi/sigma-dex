"""Scene 5 night background in the originals' pixel style (Arvind 2026-11-15: "work more on the background and the northern
lights; you can see it is a pixelated picture and not the right style"). Drawn by rules, not painted and shrunk:
flat colour bands with stepped, ragged edges (as the original sky and sea), few colours, crisp shapes.
Virtual canvas 256x608, measured in the emulator: while the scene plays the bottom screen shows screen 64 rows o..o+191
(o = 64 -> 29, in night64 rows = map rows 96+) and the top screen screen 61 rows o+96..o+287, so the two screens meet when
canvas row = screen 61 row = night64 row + 288. Visible: canvas rows ~125-543. Horizon at row 496.
python sc5/bg/paint_night.py [SEED] -> sc5/bg/night_canvas.png, night61.png (256x320), night64.png (256x320)"""
import sys, os, numpy as np
from PIL import Image
H8 = os.path.dirname(os.path.abspath(__file__))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
rng = np.random.default_rng(SEED)
W, H, HOR = 256, 608, 496
OFF = 96                                                           # everything below was laid out for a horizon at 400
X = np.arange(W)
def steps(n, lo, hi, run=(3, 9), amp=2):
    """a ragged edge: piecewise-constant offsets in runs of 3-9 px, like the stepped band edges of the original"""
    out = np.zeros(n); x = 0; v = 0
    while x < n:
        r = rng.integers(*run); v = np.clip(v + rng.integers(-1, 2), -amp, amp); out[x:x + r] = v; x += r
    return out
def smooth_noise(n, k, amp):
    p = rng.normal(0, 1, n // k + 3); xs = np.arange(n) / k
    i = xs.astype(int); f = xs - i; f = f * f * (3 - 2 * f)
    return (p[i] * (1 - f) + p[i + 1] * f) * amp
img = np.zeros((H, W, 3), int)
# ---------------- 1. sky: night ramp, bands curving down at the sides (the original's dome), ragged stepped edges
SKY = [(8, 8, 33), (8, 16, 49), (16, 24, 65), (16, 32, 82), (24, 41, 98), (24, 57, 115), (32, 74, 123), (41, 90, 131), (57, 106, 139)]
edges = np.array([70, 150, 215, 265, 305, 338, 362, 382]) + OFF        # band k ends at edges[k] (centre column)
dome = ((X - 127.5) / 128.0) ** 2 * 26                              # bands sit lower at the sides
lvl = np.zeros((H, W), int)
for k, e in enumerate(edges):
    edge = e + dome + steps(W, 0, 0, amp=3) * 1.5
    edge = np.round(edge).astype(int)
    lvl += (np.arange(H)[:, None] >= edge[None, :])
img[:HOR] = np.array(SKY)[np.minimum(lvl, len(SKY) - 1)][:HOR]
# ---------------- 2. stars: sparse, only in the dark upper sky
STAR = [(98, 115, 164), (189, 205, 238), (246, 246, 255)]
SPOT = [(3, 3), (5, 6), (2, 5)]                     # stars sit on a few spots inside an 8x8 tile, so their tiles repeat
for _ in range(90):
    sx, sy = SPOT[rng.integers(3)]; x = int(rng.integers(0, 32)) * 8 + sx; y = int(rng.triangular(120, 120, 396)) // 8 * 8 + sy
    if lvl[y, x] > 4: continue
    b = rng.choice(3, p=[0.55, 0.33, 0.12]); img[y, x] = STAR[b]
    if b == 2: 
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): img[y + dy, x + dx] = STAR[0]
# ---------------- 3. northern lights: curtains of vertical rays. Bright mint lower edge, greens fading up into the sky,
# a violet fringe at the top; column brightness varies in runs (the folds), all levels flat with stepped ends.
AUR = [(16, 82, 90), (24, 123, 106), (41, 172, 115), (82, 222, 139), (164, 255, 197), (230, 255, 238)]
VIO = [(57, 41, 106), (90, 57, 139)]
def curtain(base, height, gain, violet=True, hem=True):
    """rays: each column's brightness comes in runs of 1-3 px (the folds), bright rays reach higher; the lowest level
    already lets the sky through, so the upper rays thin out into streaks instead of a solid wall"""
    ray = np.ones(W); x = 0
    while x < W:
        r = rng.integers(1, 4); ray[x:x + r] = rng.choice([0.3, 0.55, 0.8, 1.0], p=[0.25, 0.3, 0.25, 0.2]); x += r
    for x in range(W):
        g = gain[x] * ray[x]; b = base[x]; h = height[x] * (0.45 + 0.55 * ray[x])
        if g <= 0.05 or h < 4: continue
        for y in range(max(0, int(b - h)), int(b) + 1):
            t = min(1.0, max(0.0, (b - y) / h))
            v = g * (1.0 - t) ** 1.7
            if hem and t < 0.05 and g > 0.5: k = 5 if g > 0.78 else 4
            else: k = int(v * 5.2) - 1
            if k >= 0: img[y, x] = AUR[min(k, 4)]
            elif violet and 0.66 < t < 0.86 and g > 0.62 and ray[x] >= 0.8: img[y, x] = VIO[1] if t < 0.78 else VIO[0]
# main curtain on the top screen: an S-shaped hem sweeping from upper left down to the right, over the fjord
base = OFF + 150 + 55 * np.sin((X / W) * np.pi * 1.25 - 0.5) + smooth_noise(W, 40, 10) + steps(W, 0, 0, run=(2, 6), amp=2)
height = 85 + smooth_noise(W, 10, 22) + 45 * np.exp(-((X - 170) / 60.0) ** 2)
gain = np.clip(0.75 + smooth_noise(W, 14, 0.3), 0, 1)
gain *= np.clip(1.2 - np.abs(X - 160) / 170, 0.2, 1)                  # brightest above the fjord's mouth
curtain(base, height, gain)
# a second, fainter and lower curtain far away, above the mountains
base2 = OFF + 330 + 12 * np.sin(X / W * np.pi * 2 + 1) + steps(W, 0, 0, run=(2, 7), amp=2)
height2 = 45 + smooth_noise(W, 7, 14) + steps(W, 0, 0, run=(1, 4), amp=3) * 4
gain2 = np.clip(0.42 + smooth_noise(W, 18, 0.22), 0, 0.75) * np.clip(1.1 - np.abs(X - 140) / 150, 0, 1)
curtain(base2, height2, gain2, violet=False, hem=False)
# ---------------- 4. the fjord, Norwegian style (Arvind 2026-11-15: "could look more like fjords with Norwegian mountains"):
# not alpine spikes but steep, glacier-cut walls that drop straight into the water, rounded shoulders and flat high plateaus
# (fjellvidde) with snow lying in streaks, granite ledges on the cliff faces, headlands alternating left and right that
# recede into the fjord, each farther one lower and hazier, and a thin waterfall. Drawn back to front.
MTN = np.zeros((H, W), bool)
LAYERS = {  # base, cliff face lit by the aurora above the fjord, ledge/gully shade, snow, snow shade
    'far':  [(41, 65, 98), (57, 90, 115), (32, 57, 90), (139, 164, 197), (98, 123, 156)],
    'mid':  [(24, 41, 74), (41, 74, 98), (16, 32, 57), (156, 180, 213), (106, 131, 164)],
    'near': [(16, 24, 49), (32, 65, 90), (8, 16, 33), (189, 213, 238), (123, 148, 189)],
}
def headland(side, layer, x_out, y_out, x_edge, y_edge, x_foot, round_r=6, snow=0.5, ledges=True, fall=None, knoll=4, snowline=None):
    """side 'L': land from x_out (left) to the cliff edge at x_edge; 'R': mirrored. The plateau runs from (x_out, y_out) to
    (x_edge, y_edge) with gentle knolls, the shoulder rounds over round_r px, then the cliff falls to the water at x_foot."""
    base, lit, shade, sn, sns = LAYERS[layer]
    sgn = 1 if side == 'L' else -1
    xs = np.arange(W)
    t = np.clip((xs - x_out) / (x_edge - x_out), 0, 1)
    top = y_out + (y_edge - y_out) * t ** 0.8 - np.abs(smooth_noise(W, 20, knoll)) - smooth_noise(W, 7, knoll * 0.25)   # rounded domes
    # rounded shoulder: the last round_r px before the edge curve down
    dx = (x_edge - xs) * sgn
    sh = (dx >= 0) & (dx < round_r)
    top = np.where(sh, top + (round_r - np.sqrt(np.maximum(0, round_r ** 2 - (round_r - dx) ** 2))) * 1.6, top)
    # the cliff face: x of the wall at each row (near vertical, a slight bulge and granite steps)
    rows = np.arange(int(y_edge), HOR + 1)
    f = (rows - y_edge) / max(1, HOR - y_edge)
    face = x_edge + (x_foot - x_edge) * f ** 0.7 + smooth_noise(len(rows) + 8, 6, 1.4)[:len(rows)]
    face = np.round(face + np.floor((rows - y_edge) / 7) % 2 * sgn).astype(int)       # small steps every 7 px
    face_at = dict(zip(rows.tolist(), face.tolist()))
    for x in range(W):
        inland = (x <= x_edge) if side == 'L' else (x >= x_edge)
        beyond = (x - x_out) * sgn < 0
        if beyond: continue
        y0 = int(round(top[x])) if inland else None
        for y in range(int(min(top.min(), y_edge)), HOR):
            if inland: 
                if y < y0: continue
            else:
                fx = face_at.get(y)
                if fx is None or (x - fx) * sgn > 0: continue
            img[y, x] = base; MTN[y, x] = True
    # cliff face light: the wall turned toward the fjord's middle catches the aurora; granite ledges and gullies
    for y in rows[:-1]:
        fx = face_at[int(y)]
        w = 2 if layer != 'far' else 1
        for k in range(w):
            xx = fx - k * sgn
            if 0 <= xx < W and MTN[y, xx]: img[y, xx] = lit
        if ledges and (y - int(y_edge)) % 9 == 4:
            ln = int(rng.integers(3, 9))
            for k in range(ln):
                xx = fx - (w + k) * sgn
                if 0 <= xx < W and MTN[y, xx]: img[y, xx] = lit if k < ln - 2 else shade
    # gullies: dark vertical streaks down the wall
    for _ in range(3 if layer != 'far' else 1):
        gy = int(rng.integers(int(y_edge) + 4, max(int(y_edge) + 5, HOR - 20))); ln = int(rng.integers(8, 22))
        for y in range(gy, min(HOR, gy + ln)):
            xx = face_at[y] - (w + int(rng.integers(1, 4))) * sgn
            if 0 <= xx < W and MTN[y, xx]: img[y, xx] = shade
    # the plateau's own top edge: a lit rim, and snow lying in broken horizontal streaks
    for x in range(W):
        inland = (x <= x_edge) if side == 'L' else (x >= x_edge)
        if not inland or (x - x_out) * sgn < 0: continue
        y0 = int(round(top[x]))
        img[y0, x] = lit
        if rng.random() < snow:
            img[y0, x] = sn
            if rng.random() < 0.6: img[y0 + 1, x] = sns
    run = 0
    for x in range(W):
        inland = (x <= x_edge - round_r * sgn) if side == 'L' else (x >= x_edge - round_r * sgn)
        if not inland or (x - x_out) * sgn < 0: continue
        if run <= 0 and rng.random() < snow * 0.08: run = int(rng.integers(3, 12)); dy = int(rng.integers(3, 9))
        if run > 0:
            y = int(round(top[x])) + dy
            if y < HOR and MTN[y, x]: img[y, x] = sn if run > 1 else sns
            run -= 1
    if snowline is not None:                                               # snow fields on the high slopes, lying in streaks
        for x in range(W):
            inland = (x <= x_edge) if side == 'L' else (x >= x_edge)
            if not inland or (x - x_out) * sgn < 0: continue
            y0 = int(round(top[x]))
            if y0 >= snowline: continue
            dep = int((snowline - y0) / 2.2)
            for y in range(y0, min(HOR, y0 + dep)):
                if not MTN[y, x]: continue
                band = (y - y0) // 3 + (x // int(rng.integers(5, 9)))
                if band % 3 != 2 or y - y0 < 2: img[y, x] = sn if (y - y0) < dep * 0.55 else sns
    if fall is not None:                                                   # a thin waterfall down the wall
        fx0, fy0 = fall
        for y in range(fy0, HOR):
            xx = face_at.get(y, fx0) - (3 + (y // 5) % 2) * sgn
            if 0 <= xx < W and MTN[y, xx] and (y % 11) not in (0, 1): img[y, xx] = (189, 213, 238) if y % 3 else (139, 172, 213)
def end_mountain():
    xs = np.arange(W); cx = 150
    top = 452 + np.minimum(np.abs(xs - 136), np.abs(xs - 166) + 3) * 0.75 - np.abs(smooth_noise(W, 6, 2))   # two peaks
    for x in range(W):
        y0 = int(round(top[x]))
        if y0 >= HOR - 2: continue
        img[y0:HOR, x] = (41, 65, 98); MTN[y0:HOR, x] = True
        dep = max(0, int((466 - y0) / 1.8))
        for y in range(y0, min(HOR, y0 + dep)):
            if (y - y0) < 2 or (x + (y - y0) * 2) % 7 < 5: img[y, x] = (139, 164, 197) if (y - y0) < dep * 0.5 else (98, 123, 156)
end_mountain()
VP = 150                                                                      # the fjord bends away here, under the aurora
headland('L', 'far', 96, 462, 140, 468, 144, round_r=4, snow=0.6, ledges=False, knoll=3, snowline=466)
headland('R', 'far', 214, 458, 158, 470, 154, round_r=4, snow=0.6, ledges=False, knoll=3, snowline=464)
headland('L', 'mid', 0, 420, 108, 444, 120, round_r=6, snow=0.45, knoll=7, snowline=446)
headland('R', 'mid', 255, 412, 180, 446, 168, round_r=6, snow=0.45, fall=(176, 452), knoll=7, snowline=442)
headland('L', 'near', 0, 352, 62, 398, 82, round_r=10, snow=0.35, knoll=10, snowline=396)
headland('R', 'near', 255, 344, 212, 392, 194, round_r=10, snow=0.35, knoll=10, snowline=390)
# ---------------- 5. water: night sea bands (ragged, curving up at the sides like the original), mountain and aurora mirrored
SEA = [(41, 74, 98), (32, 57, 90), (24, 49, 82), (16, 41, 74), (16, 32, 65), (8, 24, 49), (8, 16, 41)]
sedges = np.array([404, 410, 420, 436, 458, 482]) + OFF
dome2 = -((X - 127.5) / 128.0) ** 2 * 14
sl = np.zeros((H, W), int)
for e in sedges:
    edge = np.round(e + dome2 + steps(W, 0, 0, amp=2) * 1.5).astype(int); sl += (np.arange(H)[:, None] >= edge[None, :])
img[HOR:] = np.array(SEA)[np.minimum(sl, len(SEA) - 1)][HOR:]
img[HOR] = (57, 98, 115)                                              # the bright water line
# reflections: rows below the horizon take the colour of the mirrored row above, darkened, broken into horizontal dashes
for y in range(HOR + 1, H):
    d = y - HOR; src = HOR - d * 1.6
    if src < 360 + OFF: break
    row = img[int(src)].copy(); keep = rng.random(W) < max(0.15, 0.85 - d / 90)
    runs = np.repeat(rng.random(W // 4 + 1) < max(0.2, 0.9 - d / 80), 4)[:W]
    m = keep & runs
    dark = (row * 0.55).astype(int)
    mt = MTN[int(src)]
    lit = (row[:, 1] > row[:, 2] + 10) & ~mt                           # aurora green reflects; the walls reflect dark
    img[y, mt & runs] = (8, 16, 33)
    img[y, lit & m] = np.where((d < 30), 1, 0)[..., None] * np.array(AUR[2]) + np.where(d >= 30, 1, 0)[..., None] * np.array(AUR[1])
# the aurora's glitter path on the water under the bright part of the curtain
for y in range(HOR + 2, H, 2):
    d = y - HOR; n = rng.integers(2, 6)
    for _ in range(n):
        cx = int(rng.normal(165, 18 + d * 0.25)); ln = rng.integers(2, 9)
        c = AUR[3] if d < 25 and rng.random() < 0.4 else (AUR[2] if d < 60 else AUR[1])
        if rng.random() < 0.9 - d / 160: img[y, max(0, cx):min(W, cx + ln)] = c
Image.fromarray(img.astype(np.uint8)).save(os.path.join(H8, 'night_canvas.png'))
# screens: 61 = canvas rows 0..359 (map rows 0-44), 64 = canvas rows 288..607 (map rows 96-415)
Image.fromarray(img[:360].astype(np.uint8)).save(os.path.join(H8, 'night61.png'))
Image.fromarray(img[288:608].astype(np.uint8)).save(os.path.join(H8, 'night64.png'))
print('colours', len(np.unique(img.reshape(-1, 3), axis=0)))
