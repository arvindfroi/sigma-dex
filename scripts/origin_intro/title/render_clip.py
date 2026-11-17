"""Title screen bottom (a/2/6/4): one clip of 50 frames from a still picture + its depth map, the way the originals work
(analysed 2026-11-15, see tittel_analyse.png):
- the picture never moves; a light plane sweeps LEFT -> RIGHT through 3D: pixel lights at t_on = T0 + B*(x - K*near)
  (near = 0..1 from the depth map, so nearer parts light earlier and the light's edge bends over the forms), stepped per frame
- each pixel stays lit for D frames; on its first and last lit frame it shows one tone darker (the soft edge of the light)
- one hue in a few flat tones (the clip's own palette 13 entries, reused as they are) + black lines on black
python title/render_clip.py COMP.png DEPTH.png OUTDIR [CLIP=0]
-> OUTDIR/idx.npy (50x192x256 palette-13 indices), OUTDIR/fNN.png, OUTDIR/sheet.png, OUTDIR/still.png"""
import sys, os, numpy as np
from PIL import Image
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__))
COMP, DEPTH, OUT = sys.argv[1:4]; CLIP = int(sys.argv[4]) if len(sys.argv) > 4 else 0
os.makedirs(OUT, exist_ok=True)
pal = np.load(os.path.join(HERE, 'pal13.npy'))
RAMPS = {0: [1, 7, 9, 3, 13, 16, 20],           # clip 0 (Blastoise's, now Warrallier's): its blues, dark -> light
         1: [12, 14, 23, 24, 26, 25, 20]}        # clip 1 (Charizard's, now Monarkhan's): its oranges
RAMP = RAMPS[CLIP]
T0, B, K, D = float(os.environ.get('T_T0', 4)), float(os.environ.get('T_B', 0.075)), float(os.environ.get('T_K', 70)), int(os.environ.get('T_D', 14))
W, H = 256, 192
src = np.asarray(Image.open(COMP).convert('RGB').resize((1024, 768), Image.LANCZOS)).astype(float)
dep = np.asarray(Image.open(DEPTH).convert('L').resize((1024, 768), Image.LANCZOS)).astype(float)
lum = src @ np.array([0.3, 0.59, 0.11])
mask = nd.binary_fill_holes(nd.binary_opening((dep > 30) | (lum > 35), iterations=2))
# black lines: pixels much darker than their surroundings (outlines, inner lines), at full size
loc = nd.gaussian_filter(lum, 5)
line = (lum < 0.55 * loc) & (lum < 70) & mask
# shrink 4x: a cell is line if enough of it is line; figure if mostly figure
blk = lambda a: a.reshape(H, 4, W, 4).mean((1, 3))
m4 = blk(mask.astype(float)) > 0.5
l4 = (blk(line.astype(float)) > 0.32) & m4
lum4 = blk(np.where(mask, lum, 0)) / np.maximum(blk(mask.astype(float)), 1e-6)
d4 = blk(np.where(mask, dep, 0)) / np.maximum(blk(mask.astype(float)), 1e-6)
d4 = nd.gaussian_filter(d4, 1.2)
# tones: the picture's value spread over the ramp by rank inside the figure (the dark body would vanish on black otherwise),
# with a little of the depth mixed in so near parts read lighter, as in the originals
inside = m4 & ~l4
v = np.zeros((H, W))
r = np.argsort(np.argsort(lum4[inside])); v[inside] = r / max(1, len(r) - 1)
dn = np.zeros((H, W)); dd = d4[m4]; dn[m4] = (dd - np.percentile(dd, 3)) / max(1, np.percentile(dd, 97) - np.percentile(dd, 3)); dn = np.clip(dn, 0, 1)
v = np.clip(0.8 * v + 0.2 * dn, 0, 1)
EDGES = [0.12, 0.3, 0.5, 0.7, 0.88, 0.97]          # share of the figure in each tone, dark -> light
lvl = np.searchsorted(EDGES, v)
# flatter shapes like the originals' cel areas: a 3x3 majority pass over the tones (lines left alone)
from scipy.stats import mode as _mode
pad = np.pad(lvl, 1, mode='edge'); win = np.stack([pad[dy:dy + H, dx:dx + W] for dy in range(3) for dx in range(3)], -1)
lvl = _mode(win, axis=-1, keepdims=False).mode
lvl[l4] = -1; lvl[~m4] = -1
# eye: the brightest yellow -> the top tone
sat = src.max(-1) - src.min(-1)
# the held orb (v2, Arvind: "it holds a ball like the one at the tip of Blastoise's cannon"): the biggest bright round blob
ORB = os.environ.get('T_ORB', '1') == '1'
orb4 = np.zeros((H, W), bool)
# v4 (Arvind: "remove the ball from the hand but keep the effect; mind the fingers in front of the ball"): the orb's place
# can come from another picture (T_ORB_REF, the one that still had the ball); T_ORB_DRAW=0 leaves the ball itself out, so
# only its flashes are drawn, coming out of the empty hand with the fingers in front
ORB_DRAW = os.environ.get('T_ORB_DRAW', '1') == '1'
if ORB:
    ref = src if not os.environ.get('T_ORB_REF') else np.asarray(Image.open(os.environ['T_ORB_REF']).convert('RGB').resize((1024, 768), Image.LANCZOS)).astype(float)
    rl = ref @ np.array([0.3, 0.59, 0.11]); rs = ref.max(-1) - ref.min(-1)
    br = (rl > 150) & (rs > 25) | (rl > 225); br = nd.binary_opening(br, iterations=3); lab, n = nd.label(br)
    if n:
        k = 1 + int(np.argmax(nd.sum(br, lab, range(1, n + 1)))); ys, xs = np.nonzero(lab == k)
        cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2; rad = max(ys.max() - ys.min(), xs.max() - xs.min()) / 2 + 6
        yy, xx = np.mgrid[:768, :1024]; disc = ((yy - cy) ** 2 + (xx - cx) ** 2 <= rad ** 2) & mask & (lum > 95) & ((sat > 45) | (lum > 170))   # not the dark grey claws in front
        if ORB_DRAW: orb4 = blk(disc.astype(float)) > 0.5
        ORB_C, ORB_R = (cy / 4, cx / 4), rad / 4
        print('orb centre', [round(v, 1) for v in ORB_C], 'radius', round(ORB_R, 1))
eye = (((src[..., 0] > 150) & (src[..., 1] > 120) & (src[..., 2] < 90)) | ((lum > 200) & (sat < 40))) & mask
eye4 = (blk(eye.astype(float)) > 0.3) & ~orb4
lvl[eye4] = len(RAMP) - 1                                          # white eyes: the top tone
if ORB:
    ov = lum4[orb4]; r_ = np.argsort(np.argsort(ov)) / max(1, len(ov) - 1)
    lvl[orb4 & ~l4] = np.searchsorted([0.15, 0.4, 0.75], r_[~l4[orb4]]) + 3     # the orb in the light half of the ramp
Image.fromarray(np.where(lvl[..., None] >= 0, pal[np.array(RAMP)[np.clip(lvl, 0, None)]], 0).astype(np.uint8)).save(os.path.join(OUT, 'still.png'))
# gold fur (Arvind 2026-11-15: "the fur should look a bit like gold"): T_FUR = a mask picture of the fur. Inside it the tones
# are ranked on their own with a metallic spread - deep shadow straight into bright gold, a few white glints - and drawn with
# the clip's gold entries (GOLD7, one per tone level) instead of the body ramp.
FUR4 = np.zeros((H, W), bool); GLINTS = []
if os.environ.get('T_FUR'):
    fu = np.asarray(Image.open(os.environ['T_FUR']).convert('RGB').resize((1024, 768), Image.LANCZOS)).astype(int)
    furm = (fu.min(-1) > 215) & (src[..., 0] > 150) & (src[..., 2] < 140) & mask       # white in the mask, yellow in the picture
    FUR4 = (blk(furm.astype(float)) > 0.5) & m4 & ~l4
    fv = lum4[FUR4]; rk = np.argsort(np.argsort(fv)) / max(1, len(fv) - 1)
    lvl[FUR4] = np.searchsorted([0.22, 0.4, 0.62, 0.84, 0.95, 0.985], rk)
    print('fur px', int(FUR4.sum()))
    fy_, fx_ = np.nonzero(FUR4); order = np.argsort(-lum4[FUR4])
    GLINTS = []
    for i_ in order:
        p_ = (fy_[i_], fx_[i_])
        if all((p_[0] - g[0]) ** 2 + (p_[1] - g[1]) ** 2 > 22 ** 2 for g in GLINTS): GLINTS.append((p_[0], p_[1], len(GLINTS) * 3))
        if len(GLINTS) >= int(os.environ.get('T_GLINTS', 4)): break
GOLD7 = [12, 14, 22, 25, 27, 27, 20]
# colours per material (Monarkhan v4, Arvind: "the wing colours and the spot colours look odd"): one global tone level per pixel
# as before, but each material draws that level with its own entries - yellow wings stay gold-yellow instead of turning white,
# spots stay dark brown, the body red, the nose light, fangs and claws white.
MAT4 = None
if os.environ.get('T_MAT') == '1':
    sys.path.insert(0, HERE); from matclass import classes
    cl = classes(src.astype(int))
    onehot = np.stack([blk((cl == k).astype(float)) for k in range(6)], -1); onehot[..., 0] *= 0.6
    MAT4 = onehot.argmax(-1)
MATT = {0: RAMP, 1: [12, 14, 23, 23, 24, 26, 26], 2: [14, 24, 26, 26, 25, 25, 27], 3: [12, 12, 12, 14, 14, 14, 24],
        4: [14, 23, 24, 26, 26, 25, 25], 5: [15, 15, 20, 20, 20, 20, 20]}
# the hand in front of the flash: figure pixels round the orb's place that are near the viewer (left of the bill)
HAND = np.zeros((H, W), bool)
if ORB and not ORB_DRAW:
    yy, xx = np.mgrid[:H, :W]; dd = np.sqrt((yy - ORB_C[0]) ** 2 + (xx - ORB_C[1]) ** 2)
    HAND = m4 & (dd <= ORB_R * float(os.environ.get("T_HAND_R", 1.5))) & (dn > float(os.environ.get('T_HAND_DN', 0.55))) & (xx < ORB_C[1] + ORB_R * float(os.environ.get("T_HAND_X", 0.95)) - np.maximum(0, yy - ORB_C[0]) * float(os.environ.get("T_HAND_SLANT", 0)))   # optional slanted wrist line
    HAND &= ~((yy < ORB_C[0] + ORB_R * 0.6) & (xx > ORB_C[1] + ORB_R * 0.9))       # above the palm, the right side is the head's edge
    lab_, n_ = nd.label(HAND & ~nd.binary_dilation(l4))             # the black lines split the parts: keep only the
    keep = [k for k in range(1, n_ + 1) if ((lab_ == k) & (dd <= ORB_R)).any() and (lab_ == k).sum() > 6]   # pieces at the orb's place
    HAND = nd.binary_dilation(np.isin(lab_, keep), iterations=2) & HAND
    Image.fromarray((HAND * 255).astype(np.uint8)).save(os.path.join(OUT, 'hand_mask.png'))
# timing
X = np.arange(W)[None, :].repeat(H, 0)
ton = np.floor(T0 + B * (X - K * dn)).astype(int)
def star(n):
    pts = [(0, 0, 6)]
    for k in range(1, n + 1):
        c = 5 if k < n else 4
        pts += [(k, 0, c), (-k, 0, c), (0, k, c), (0, -k, c)]
    if n >= 3: pts += [(1, 1, 6), (-1, 1, 6), (1, -1, 6), (-1, -1, 6), (2, 1, 5), (-2, 1, 5), (2, -1, 5), (-2, -1, 5),
                       (1, 2, 5), (-1, 2, 5), (1, -2, 5), (-1, -2, 5)]
    return pts
STAR_SHAPES = {0: [(0, 0, 5)], 1: star(2), 2: star(3), 3: star(6)}
STARS = [(-1.25, -0.95, 0), (1.15, -1.25, 3), (1.0, 0.75, 5), (-0.55, 1.3, 2), (2.2, -0.2, 6)]
DROP_BIG = ["....o....", "...oOo...", "...oOo...", "..oOwOo..", ".oOwwOOo.", ".oOwOOOo.", "oOOOOOOOo", "oOOOOOOOo", ".oOOOOOo.", "..ooooo.."]
DROP_SMALL = [".........", "....o....", "...oOo...", "...oOo...", "..oOwOo..", "..oOOOo..", ".oOOOOOo.", ".oOOOOOo.", "..ooooo..", "........."]
FLASH_LIGHT = os.environ.get('T_FLASH_LIGHT', '1') == '1'
FL_START = int(os.environ.get('T_FL_START', 3))
ZS = float(os.environ.get('T_ZS', 90))                     # depth range of the figure in pixels (near = +ZS)
dsm = nd.gaussian_filter(dn, 2.0); P3z = dsm * ZS
gy_, gx_ = np.gradient(P3z); nrm3 = np.stack([-gx_, -gy_, np.ones_like(gx_)], -1); nrm3 /= np.linalg.norm(nrm3, axis=-1, keepdims=True)
if ORB:
    yy0, xx0 = np.mgrid[:H, :W]
    hz = np.percentile(P3z[HAND], 80) if HAND.any() else ZS
    FL_Z = hz + ORB_R * 0.4                                  # the light sits in the cupped hand, a little in front of it
    Lv = np.stack([ORB_C[1] - xx0, ORB_C[0] - yy0, FL_Z - P3z], -1).astype(float); Lv /= np.linalg.norm(Lv, axis=-1, keepdims=True) + 1e-6
    FL_LAMB = np.clip((nrm3 * Lv).sum(-1), 0, 1)
FL_REACH, FL_GAIN = float(os.environ.get('T_REACH', 1.6)), float(os.environ.get('T_GAIN', 1.0))
DROP_AT = (int(os.environ.get('T_DROPX', 8)), int(os.environ.get('T_DROPY', 8)))
# ---- fire (Monarkhan, Arvind 2026-11-15; Charizard's clip starts with fire in the dark that spreads into a glowing rim
# along the head, flickers and lasts long, then the sweep comes): T_FLAMES = a mask picture of the creature's own flames.
# The flames are their own layer from the first frame, flickering, and every flame is a point light in the sweep's 3D space.
FLAMES = os.environ.get('T_FLAMES')
FL4 = np.zeros((H, W), bool); FLS = []
if FLAMES:
    fm = np.asarray(Image.open(FLAMES).convert('L').resize((1024, 768), Image.LANCZOS)) > 128
    FL4 = (blk(fm.astype(float)) > 0.4) & m4
    lab_, n_ = nd.label(FL4)
    for k in range(1, n_ + 1):
        ys_, xs_ = np.nonzero(lab_ == k)
        if len(ys_) < 12: continue
        zf = np.percentile(dn[lab_ == k], 70) * float(os.environ.get('T_ZS', 90)) + 12
        FLS.append((ys_.mean(), xs_.mean(), zf, np.sqrt(len(ys_) / np.pi)))
    print('flames', [(round(a), round(b), round(r_)) for a, b, z_, r_ in FLS])
    FIRE_END = int(os.environ.get('T_FIRE_END', 36))
    FIRE_RIM = float(os.environ.get('T_FIRE_RIM', 2.5))
    HEAT = [nd.gaussian_filter(np.random.default_rng(40 + k).standard_normal((96, 64)), (3.0, 1.6)) / 0.12 for k in range(4)]
    HEAT = [h / h.std() for h in HEAT]
    FLAME_SWAY, FLAME_LICK = float(os.environ.get('T_SWAY', 3.0)), float(os.environ.get('T_LICK', 0.35))
    FIRE_GAIN, FIRE_REACH = float(os.environ.get('T_FIRE_GAIN', 1.6)), float(os.environ.get('T_FIRE_REACH', 2.6))
    rng_f = np.random.default_rng(5)
    yyf, xxf = np.mgrid[:H, :W]
    dsm_f = nd.gaussian_filter(dn, 2.0) * float(os.environ.get('T_ZS', 90))
    gyf, gxf = np.gradient(dsm_f); nrmf = np.stack([-gxf, -gyf, np.ones_like(gxf)], -1); nrmf /= np.linalg.norm(nrmf, axis=-1, keepdims=True)
    def fire_light(flick):
        I = np.zeros((H, W))
        for (cy_, cx_, cz_, r_), fk in zip(FLS, flick):
            v = np.stack([cx_ - xxf, cy_ - yyf, cz_ - dsm_f], -1).astype(float); dist = np.linalg.norm(v, axis=-1) + 1e-6
            lam = np.clip((nrmf * (v / dist[..., None])).sum(-1), 0, 1)
            # back/rim light like Charizard's fire rim: edges whose normal turns toward the flame in the picture plane glow
            # even when the flame is behind them (1 - n_z = how much the surface turns away from the viewer)
            dxy = np.stack([cx_ - xxf, cy_ - yyf], -1).astype(float); dxy /= np.linalg.norm(dxy, axis=-1, keepdims=True) + 1e-6
            rim = np.clip((nrmf[..., :2] * dxy).sum(-1), 0, 1) * (1 - nrmf[..., 2]) * FIRE_RIM
            lam = np.maximum(lam, rim)
            I += fk * lam / (1 + (dist / (r_ * FIRE_REACH)) ** 2) ** 1.5   # steep: fire lights what is near
        return I * FIRE_GAIN
frames = np.zeros((50, H, W), np.uint8)
for t in range(50):
    on = m4 & (t >= ton) & (t < ton + D) & (lvl >= 0)
    edge = on & ((t == ton) | (t == ton + D - 1))
    L = np.where(edge, np.maximum(lvl - 1, 0), lvl)
    f = np.zeros((H, W), np.uint8); f[on] = np.array(RAMP)[L[on]]
    if ORB and not ORB_DRAW and 3 <= t <= 45 and os.environ.get('T_HAND_LIT', '0') == '1':
        # optional: the empty hand stays lit as long as Blastoise's cannon (v4; Arvind did not like it, so off by default)
        hl = HAND & (lvl >= 0); f[hl] = np.array(RAMP)[np.maximum(lvl[hl] - (1 if t in (3, 45) else 0), 0)]
        f[HAND & l4] = 0
    HANDF = f.copy()                                                   # the hand as the sweep shows it (dark = silhouette)
    if ORB:
        # the orb is its own effect layer, like Blastoise's cannon: lit from early on and long after the sweep, with one flash
        # where a big pale disc swells over it and shrinks again (frames 10-18 in the original)
        if 3 <= t <= 45:
            o_on = orb4 & (lvl >= 0); f[o_on] = np.array(RAMP)[lvl[o_on]]
            ol = orb4 & l4; f[ol] = 0
            if t in (3, 45): f[o_on] = np.array(RAMP)[np.maximum(lvl[o_on] - 1, 0)]
        # v3 (Arvind: "same effects as Blastoise: the ball goes on and off and gives off light when on"): measured on the
        # original cannon: the mouth flashes on every other frame; the pale disc starts small, swells past the mouth's edge
        # (frames ~11-17), shrinks again, and ends as a small core blinking until the layer goes out
        # v8 (Arvind: "start with the ball blinking, then the sweep comes, like Blastoise"): the flashes start at FL_START
        # (default 3) and the sweep later (T_T0); the swell pattern runs from the first flash
        te = t + (5 - FL_START)
        if FL_START <= t <= 45 and (t - FL_START) % 2 == 0:
            env = {5: .35, 7: .6, 9: .85, 11: 1.05, 13: 1.2, 15: 1.3, 17: 1.22, 19: 1.05, 21: .9, 23: .75, 25: .6, 27: .5, 29: .45}
            rr = ORB_R * env.get(te, .38)
            yy, xx = np.mgrid[:H, :W]; dd = np.sqrt((yy - ORB_C[0]) ** 2 + (xx - ORB_C[1]) ** 2)
            # the flash lights its surroundings (v6, Arvind: "the ball should light up the surroundings like Blastoise's"):
            # measured on the original's flash frames: ~2-3k pixels go brighter, never darker: one tone up on what is lit
            # near the flash, and a 1-3 px rim of light on the edges that face it (cap, face, cannon, hand)
            if FLASH_LIGHT:
                # v7 (Arvind: "it blinks but has no effect on the surroundings; use the same 3D map as the left-right light"):
                # the flash is a point light in the hand, in the same 3D space as the sweep (x, y, depth). Every figure pixel
                # gets light from it: Lambert on the depth map's normals, falling off with 3D distance, scaled by the flash
                # size. Lit pixels go up to 3 tones brighter; dark (unlit) pixels near it are revealed in low tones.
                I = FL_LAMB * (0.45 + 0.55 * env.get(te, .38) / 1.3) / (1 + (np.sqrt((xx - ORB_C[1]) ** 2 + (yy - ORB_C[0]) ** 2 + (FL_Z - P3z) ** 2) / (ORB_R * FL_REACH)) ** 2)
                I = I * FL_GAIN
                cur = np.full((H, W), -1)
                for k_, c_ in enumerate(RAMP): cur[f == c_] = k_
                lit_ = (cur >= 0) & m4 & ~l4
                boost = np.floor(I * 3.6).astype(int)
                f[lit_] = np.array(RAMP)[np.minimum(cur[lit_] + boost[lit_], len(RAMP) - 1)]
                REV = float(os.environ.get('T_REV', 0.32))
                dark_ = (f == 0) & m4 & ~l4 & (I > REV)
                # v8 (Arvind: "the light looks weak; Blastoise's cannon light is as strong as the left-right light"): where the
                # flash reaches fully, a dark part shows its own tones as the sweep would; farther away one tone less per step
                FULL, STEP = float(os.environ.get('T_FULL', 0.7)), float(os.environ.get('T_STEP', 0.12))
                down = np.clip(np.floor((FULL - I[dark_]) / STEP) + 1, 0, 9).astype(int); down[I[dark_] >= FULL] = 0
                f[dark_] = np.array(RAMP)[np.maximum(lvl[dark_] - down, 0)]
                f[(f == 0) & m4 & l4 & nd.binary_dilation(dark_)] = 0          # the black lines stay black
            f[dd <= rr] = RAMP[-1]; f[(dd > rr - 1.2) & (dd <= rr)] = RAMP[-3]
            hd = HAND & (dd <= rr + 1); f[hd] = HANDF[hd]              # fingers in front of the light
        # twinkling four-point stars round the orb and one by the head; each runs dot -> small -> big -> small -> dot
        for (fx, fy, ph) in STARS:
            if not (6 <= t <= 46): continue
            stage = [0, 1, 2, 3, 2, 1, 0, -1][(t + ph) % 8]
            x0, y0 = int(ORB_C[1] + fx * ORB_R), int(ORB_C[0] + fy * ORB_R)
            for (dx, dy, c) in STAR_SHAPES.get(stage, []):
                if 0 <= y0 + dy < H and 0 <= x0 + dx < W: f[y0 + dy, x0 + dx] = RAMP[c]
        # a water drop in place of Blastoise's ice crystal, pulsing between two sizes
        if 4 <= t <= 46:
            shp = DROP_BIG if (t // 2) % 2 == 0 else DROP_SMALL
            for dy, row in enumerate(shp):
                for dx, ch in enumerate(row):
                    for sy in range(2):
                        for sx in range(2):                      # drawn at 2x, like the original's crystal size
                            yy_, xx_ = DROP_AT[1] + 2 * dy + sy, DROP_AT[0] + 2 * dx + sx
                            if ch != '.' and 0 <= yy_ < H and 0 <= xx_ < W: f[yy_, xx_] = RAMP[{'o': 2, 'O': 4, 'w': 6}[ch]]
    if FLAMES and t <= FIRE_END:
        flick = rng_f.uniform(0.75, 1.1, len(FLS)) * (min(1.0, 0.45 + 0.2 * t) if t < 3 else 1.0) * (0.6 if t >= FIRE_END - 1 else 1.0)
        I = fire_light(flick)
        cur = np.full((H, W), -1)
        for k_, c_ in enumerate(RAMP): cur[f == c_] = k_
        lit_ = (cur >= 0) & m4 & ~l4 & ~FL4
        f[lit_] = np.array(RAMP)[np.minimum(cur[lit_] + np.floor(I[lit_] * 3.2).astype(int), len(RAMP) - 1)]
        FULL_, STEP_, REV_ = 0.75, 0.13, float(os.environ.get('T_FIRE_REV', 0.3))
        dark_ = (f == 0) & m4 & ~l4 & ~FL4 & (I > REV_)
        down = np.clip(np.floor((FULL_ - I[dark_]) / STEP_) + 1, 0, 9).astype(int); down[I[dark_] >= FULL_] = 0
        glow = np.minimum(np.floor(I[dark_] * 3.5).astype(int) + 1, 5)              # fire-lit edges glow like Charizard's rim
        f[dark_] = np.array(RAMP)[np.maximum(np.maximum(lvl[dark_] - down, 0), glow)]
        # the flames themselves (v2, Arvind: "not enough movement in the flames"): every frame each flame is re-drawn through
        # a moving warp - it sways side to side more toward its tip, its tongues lick upward and stretch, and its tones roll
        # upward like rising heat; the base stays put. Old place cleared first (the flames float free of the body).
        f[FL4] = np.where(m4[FL4] & (lvl[FL4] >= 0) & (f[FL4] > 0) & False, f[FL4], 0)
        tone_src = np.clip(np.where(lvl >= 0, lvl, 4) + 1, 2, len(RAMP) - 1); tone_src[l4] = -1
        lab_f, _ = nd.label(FL4)
        for kf, (cy_, cx_, cz_, r_) in enumerate(FLS):
            m_ = lab_f == lab_f[int(round(cy_)), int(round(cx_))] if lab_f[int(round(cy_)), int(round(cx_))] else (FL4 & ((yyf - cy_) ** 2 + (xxf - cx_) ** 2 < (2.2 * r_) ** 2))
            ys_, xs_ = np.nonzero(m_)
            if not len(ys_): continue
            base_y, top_y = ys_.max(), ys_.min(); hgt = max(1, base_y - top_y)
            ph = t * 0.9 + kf * 2.1
            # inverse warp: for every output pixel near the flame, where in the source flame does it come from
            oy, ox = np.mgrid[max(0, top_y - 10):min(H, base_y + 2), max(0, xs_.min() - 8):min(W, xs_.max() + 9)]
            up = np.clip((base_y - oy) / hgt, 0, 1.4)                         # 0 at the base, 1 at the top
            sway = (FLAME_SWAY * up ** 1.5) * np.sin(ph + up * 2.4)
            stretch = 1 + FLAME_LICK * 0.5 * (1 + np.sin(ph * 1.3 + kf)) * up        # tongues reach up and fall back
            sy = np.round(base_y - (base_y - oy) / stretch).astype(int); sx = np.round(ox - sway).astype(int)
            ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
            src_in = np.zeros_like(ok); src_in[ok] = m_[sy[ok], sx[ok]]
            tn = np.full(oy.shape, -1); tn[src_in] = tone_src[sy[src_in], sx[src_in]]
            field = HEAT[kf % len(HEAT)]                                          # a fixed noise field that rises 3 px a frame
            fy = (oy - oy.min() + 3 * t) % field.shape[0]; fx = (ox - ox.min()) % field.shape[1]
            nzz = field[fy, fx]
            roll = np.where(nzz > 0.35, 1, np.where(nzz < -0.5, -1, 0))
            tn = np.where(tn >= 0, np.clip(tn + roll, 2, len(RAMP) - 1), -1)
            edge = src_in & ~nd.binary_erosion(src_in) & (rng_f.random(oy.shape) < 0.3) & (up > 0.45)
            tn[edge] = -1
            sub = f[oy[:, 0][:, None], ox[0][None, :]]
            sub = np.where(tn >= 0, np.array(RAMP)[np.maximum(tn, 0)], np.where(src_in, 0, sub))
            f[oy[:, 0][:, None], ox[0][None, :]] = sub
    if FUR4.any() or MAT4 is not None:
        cur = np.full((H, W), -1)
        for k_, c_ in enumerate(RAMP): cur[f == c_] = k_
        base = (cur >= 0) & ~FL4
        if MAT4 is not None:
            for mk, tab in MATT.items():
                if mk == 0: continue
                mm = base & (MAT4 == mk) & ~FUR4; f[mm] = np.array(tab)[cur[mm]]
        if FUR4.any():
            # gold: the fur flashes two tones brighter in the two frames after the light reaches it (metal catching light),
            # then settles to its metallic tones; a few glints twinkle on its brightest points while it is lit
            gm = base & FUR4
            shine = gm & ((t - ton) >= 0) & ((t - ton) <= 2)
            lv = cur.copy(); lv[shine] = np.minimum(lv[shine] + 2, 6)
            f[gm] = np.array(GOLD7)[lv[gm]]
            for (gy_, gx_, gp_) in GLINTS:
                if not FUR4[gy_, gx_] or f[gy_, gx_] == 0: continue
                stage = [0, 1, 2, 3, 2, 1, -1, -1, -1, -1][(t + gp_) % 10]
                for (dx, dy, c) in STAR_SHAPES.get(stage, []):
                    if 0 <= gy_ + dy < H and 0 <= gx_ + dx < W: f[gy_ + dy, gx_ + dx] = GOLD7[c] if c < 6 else 20
    frames[t] = f
np.save(os.path.join(OUT, 'idx.npy'), frames)
for t in range(50):
    im = Image.fromarray(frames[t], 'P'); im.putpalette(pal.ravel().tolist()); im.save(os.path.join(OUT, f'f{t:02d}.png'))
S = Image.new('RGB', (10 * 130, 5 * 98), (30, 30, 30))
for t in range(50): S.paste(Image.open(os.path.join(OUT, f'f{t:02d}.png')).convert('RGB').resize((128, 96)), ((t % 10) * 130, (t // 10) * 98))
S.save(os.path.join(OUT, 'sheet.png'))
print('figure px', int(m4.sum()), 'line px', int(l4.sum()), 'first lit', int(ton[m4].min()), 'last off', int((ton[m4] + D).max()))
