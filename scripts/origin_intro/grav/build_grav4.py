"""Gravriel v4 sprite data for opening scene 1 (gs_opening a/2/6/2 members 23 palette, 24 tiles, 25 animation, 26 cells).
python grav/build_grav4.py PXDIR OUT.narc
Two sprites share these files (pret src/intro_movie_scene_1.c):
- the "sun" (sequence 0) starts with the background scroll, ~370 frames before Ho-Oh would appear. It is Gravriel:
  hidden under the water, then rising slowly, eyes shut, then the look. A code patch (grav/patch_prio.py) puts it at BG
  priority 2, behind BG1, whose painted water (night/paint_grav4.py) covers his waterline WROW and everything below.
  So he rises out of the water pixel by pixel; the parts still under water are left out of each cell (they would wrap
  around the screen otherwise).
- the "bird" (sequence 1, Ho-Oh's) starts 368 frames after the scroll, stays in front of everything (priority 0) and
  draws the foam at his waist and rings spreading on the water.
Timing: both animations run 2 ticks per frame; the fade to white starts ~90 frames after the bird appears."""
import sys, os, json, math, struct
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
from g2d import *
from lz import lz10_enc
from narc import unpack, pack
PX, OUTN = sys.argv[1], sys.argv[2]
SRC = os.path.join(ROOT, '..', 'rc8', 'x_rc8', 'files', 'a', '2', '6', '2')
meta = json.load(open(os.path.join(PX, 'pal.json')))
PAL = meta['palette']; POSES = meta['poses']; RIMI = meta['index']['rim']; EYEW = meta['index']['eyeW']
WROW = int(os.environ.get('GRAV_WROW', 178))
WAIST = int(os.environ.get('G4_WAIST', meta['waist']))   # picture row on the waterline when he has risen
CELL = int(os.environ.get('G4_CELL', 32))
VALID = set(SHAPE.values()); INV = {v: k for k, v in SHAPE.items()}
gs = unpack(open(SRC, 'rb').read())
tiledata = bytearray(); store = {}
def put(block):
    key = (block.shape, block.tobytes())
    if key in store: return store[key]
    start = len(tiledata) // 32
    for ty in range(0, block.shape[0], 8):
        for tx in range(0, block.shape[1], 8):
            for row in block[ty:ty + 8, tx:tx + 8]:
                for k in range(0, 8, 2): tiledata.append(int(row[k]) | int(row[k + 1]) << 4)
    store[key] = start; return start
def fit(n, cap): return min(s for s in (8, 16, 32, 64) if s >= n and s <= cap)
def grid_oams(img, AX, AY, box, cell=CELL):
    """picture -> sprites on a shared grid with 1 px overlap, each shrunk to its content: (x, y, w, h, tile) from the anchor"""
    x0, y0, x1, y1 = box
    P = np.pad(img, ((0, cell + 64), (0, cell + 64)))
    out = []
    for y in range(y0, y1 + 1, cell - 1):
        for x in range(x0, x1 + 1, cell - 1):
            b = P[y:y + cell, x:x + cell]
            if not b.any(): continue
            yy, xx = np.where(b > 0)
            w = fit(xx.max() - xx.min() + 1, cell); h = fit(yy.max() - yy.min() + 1, cell)
            if (w, h) not in VALID:
                if w > h: h = w // 2
                else: w = h // 2
            ox = min(xx.min(), cell - w); oy = min(yy.min(), cell - h)
            out.append((x + ox - AX, y + oy - AY, w, h, put(P[y + oy:y + oy + h, x + ox:x + ox + w])))
    return out
# ---------------------------------------------------------------- Gravriel frames (only the part above his waist line)
STATES = meta['states']
frames = {}
for k in range(POSES):
    for s in STATES:
        if s not in ('stare', 'glow') or (s == 'glow' and k != 0): continue   # v6: he always looks at you
        im = np.array(Image.open(os.path.join(PX, f'p{k}_{s}.png'))).astype(np.uint8)
        im[WAIST + 2:] = 0                         # under water for good: never drawn
        frames[(k, s)] = im
U = np.any([f > 0 for f in frames.values()], 0); ys, xs = np.where(U)
AX = 128; AY = WAIST
box = (max(0, xs.min() - 1), max(0, ys.min() - 1), xs.max(), ys.max())
oams = {key: grid_oams(f, AX, AY, box) for key, f in frames.items()}
TOP = int(ys.min()) - AY                           # hat top relative to the anchor (negative)
# the ghost's dissolve: the last frame with every other pixel gone (checkerboard), then three in four gone
yy_, xx_ = np.mgrid[0:frames[(0, 'glow')].shape[0], 0:frames[(0, 'glow')].shape[1]]
DIS = [((xx_ + yy_) % 2 == 0), ((xx_ % 2 == 0) & (yy_ % 2 == 0))]
_t0 = len(tiledata) // 32
# v15: one dissolve picture (the checker); the last step shows every other piece of it (no new tiles), which frees
# room for the water strip
dis_oams = [grid_oams(np.where(DIS[0], frames[(0, 'glow')], 0).astype(np.uint8), AX, AY, box)]
dis_oams.append(dis_oams[0])                      # same picture, drawn with the fading ghost palette 3
print('dissolve tiles', len(tiledata) // 32 - _t0)
# v15: the water in front of his waist. BG1 scrolls again (it holds the near wreckage), so the sea from his waterline
# down is drawn in his own sprite, in front of his body (first in every cell), from the scene's still BG3 picture,
# with its own palette (2)
SEA_PNG = os.environ.get('G4_SEA')
cover_oams, SEA_PAL = [], []
if SEA_PNG:
    sea = np.asarray(Image.open(SEA_PNG).convert('RGB')).astype(int)
    x0c, x1c = max(0, box[0] - 1), min(255, box[2] + 1)
    strip = sea[WROW:192, x0c:x1c + 1]
    cols_ = sorted(set(map(tuple, strip.reshape(-1, 3))))
    assert len(cols_) <= 15, f'water strip has {len(cols_)} colours'
    SEA_PAL = cols_
    lut = {c: i + 1 for i, c in enumerate(cols_)}
    simg = np.zeros((192 - WROW, 256), np.uint8)
    simg[:, x0c:x1c + 1] = np.array([[lut[tuple(v)] for v in row] for row in strip], np.uint8)
    cover_oams = grid_oams(simg, AX, 0, (x0c, 0, x1c, 191 - WROW))
    print('water strip', len(cover_oams), 'pieces,', len(SEA_PAL), 'colours, tiles now', len(tiledata) // 32)
def cover(d): return [(x, y - d, w, h, t, 2, 0) for (x, y, w, h, t) in cover_oams]
print('Gravriel tiles', len(tiledata) // 32, 'sprites per frame', max(len(o) for o in oams.values()), 'height above waist', -TOP)
# ---------------------------------------------------------------- foam and rings (the bird sprite), drawn here
solid_row = U[WAIST - 1]; bx = np.where(solid_row)[0]
HALF = (bx.max() - bx.min()) / 2 + 2; BCX = (bx.max() + bx.min()) / 2 - AX
def ring_frame(ph):
    """foam along his waist + 2 rings spreading on the water (front halves only: the backs are behind him)"""
    Wd, Hd = 256, 32; im = np.zeros((Hd, Wd), np.uint8); cy = 6
    r = np.random.default_rng(int(ph * 100))
    if os.environ.get('G4_FOAM', 'hug') == 'line':
        for x in range(int(AX + BCX - HALF - 3), int(AX + BCX + HALF + 4)):          # v6: broken pale line
            if r.random() < 0.78: im[cy, x] = RIMI
            if r.random() < 0.22: im[cy - 1, x] = RIMI
            if r.random() < 0.10: im[cy + 1, x] = EYEW
    else:   # v16: foam piles up where the water meets his sides, thin and broken across his front
        for side in (-1, 1):
            ex = AX + BCX + side * HALF
            for k in range(40):
                x = int(round(ex + side * r.normal(0, 2.2) - side * abs(r.normal(0, 3.5))))
                y = cy + int(round(r.normal(0, 0.8)))
                if 0 <= x < Wd: im[y, x] = EYEW if r.random() < 0.3 else RIMI
        for x in range(int(AX + BCX - HALF + 4), int(AX + BCX + HALF - 3)):
            if r.random() < 0.28: im[cy, x] = RIMI
            if r.random() < 0.05: im[cy - 1, x] = RIMI
    for j in range(2):
        t = (ph + j * 0.5) % 1.0
        a = HALF + 6 + 46 * t; b = 2.0 + 7 * t
        for k in range(720):
            th = math.pi * k / 720
            x = int(round(AX + BCX + a * math.cos(th))); y = int(round(cy + b * math.sin(th)))
            if 48 <= x < 208 and 0 <= y < Hd and ((k // (14 + int(20 * t))) % 3 != 2): im[y, x] = RIMI if t < 0.6 else 6
    return im
# v16: his reflection under him and the water bulging against him (palette 2, the sea's own colours). One picture,
# cut into 8-row bands; the bands sway sideways from frame to frame, so the reflection wobbles without new tiles.
REFL_bands = []
if SEA_PAL:
    sp = np.array(SEA_PAL); lum_ = sp @ np.array([0.3, 0.55, 0.15])
    DK = int(np.argmin(lum_)) + 1
    MIDW = int(np.argsort(lum_)[len(lum_) // 2]) + 1
    # his own dark sea green, mirrored and dimmed by the water: two extra colours in palette 2
    kd = np.array(PAL[meta['index']['kelpD']] if 'kelpD' in meta['index'] else PAL[4])
    for f_, w_ in ((0.75, (8, 24, 40)), (0.5, (8, 16, 32))):   # half his colour, half the water's
        SEA_PAL.append(tuple(int(round((v * f_ * 0.5 + q * 0.5) / 8)) * 8 for v, q in zip(kd, w_)))
    REF_A, REF_B = len(SEA_PAL) - 1, len(SEA_PAL)
    rr = np.random.default_rng(23)
    Hr = 16; refl = np.zeros((Hr, 256), np.uint8); top0 = 2                      # row top0 = the waterline
    for x in range(U.shape[1]):                                                   # bulge: the row just above
        if U[WAIST - 1, x] and rr.random() < 0.75: refl[top0 - 1, x] = MIDW
    for k in range(1, Hr - top0):                                                 # the mirrored silhouette below
        src = WAIST - 1 - k
        if src < 0: break
        row = U[src]
        xs_r = np.where(row)[0]
        if not len(xs_r): continue
        x = int(xs_r.min()) + int(rr.integers(0, 3))
        while x <= xs_r.max():                         # streaks: runs of reflection broken by thin gaps of water
            L = int(rr.integers(4, 12 - min(k, 6))); G = int(rr.integers(1, 2 + k // 3))
            for xx in range(x, min(x + L, int(xs_r.max()) + 1)):
                if row[xx]: refl[top0 + k, xx] = REF_A if k < 5 else REF_B
            x += L + G
    for b0 in range(0, Hr, 8):
        band = np.zeros_like(refl); band[b0:b0 + 8] = refl[b0:b0 + 8]
        REFL_bands.append(grid_oams(band, AX, top0, (0, b0, 255, b0 + 7), cell=32))
    print('reflection pieces', sum(len(b) for b in REFL_bands), 'tiles now', len(tiledata) // 32)
    if os.environ.get('G4_DEBUG'): print('refl rows', (refl > 0).sum(1).tolist(), REFL_bands)
def refl_oams(ph):
    out = []
    for bi, band in enumerate(REFL_bands):
        dx = int(round(1.6 * math.sin(2 * math.pi * ph + bi * 1.9))) if bi else 0
        out += [(x + dx, y, w, h, t, 2, 0) for (x, y, w, h, t) in band]
    return out
NR_ = int(os.environ.get('G4_RINGS', 4))
RINGS = [ring_frame(i / NR_) for i in range(NR_)]
ring_oams = [grid_oams(f, AX, 6, (0, 0, 255, 31), cell=16) for f in RINGS]
print('with rings', len(tiledata) // 32, 'tiles')
ntiles = len(tiledata) // 32
assert ntiles <= 1024, f'{ntiles} tiles: over the 32 KB OBJ VRAM of the intro'
# ---------------------------------------------------------------- timeline (frames since the scroll starts)
# v6: the scroll ends ~245. His hat and eyes come up and stop with the water just under the eyes, staring at you
# like a hunter on the lurk; then he rises, the beard swaying, still staring; his eyes flare, he turns ghost green,
# goes see-through and is gone just before the scene fades to white (~474).
# v7: the bird starts at 245 (code patch, was 368; the fade still starts at the same time). The water stirs first,
# then the hat breaks the surface with a splash.
BIRD0 = int(os.environ.get('G4_BIRD0', 245))
T_UP0, T_UP1 = 262, 302            # hat and eyes surface
T_RISE0, T_RISE1 = 322, 428        # he rises
T_GLOW = 430
T_GREEN, T_D1, T_D2, T_GONE = 442, 452, 460, 468   # green, half dissolved, mostly dissolved, gone
T_END = 640
D0 = AY - (TOP + AY) + 4                         # anchor depth below the waterline when only the water is there
D_EYE = WAIST - meta['eye_bottom'] - 2           # water just under the eyes
def ease(u):
    u = min(1, max(0, u)); return u * u * u * (u * (u * 6 - 15) + 10)
def depth(T):
    if T < T_RISE0: d = D0 + (D_EYE - D0) * ease((T - T_UP0) / (T_UP1 - T_UP0))
    elif os.environ.get('G4_RISE', 'heave') == 'smooth': d = D_EYE * (1 - ease((T - T_RISE0) / (T_RISE1 - T_RISE0)))
    else:   # v16: a heavy body: three heaves, each sinking back a little before the next, not one even glide
        u = (T - T_RISE0) / (T_RISE1 - T_RISE0)
        KU = [0.0, 0.24, 0.34, 0.58, 0.68, 0.90, 1.0]
        KV = [0.0, 0.40, 0.35, 0.74, 0.69, 1.03, 1.0]
        u = min(1.0, max(0.0, u)); j = max(i for i in range(len(KU) - 1) if KU[i] <= u) if u < 1 else len(KU) - 2
        f = ease((u - KU[j]) / (KU[j + 1] - KU[j]))
        d = D_EYE * (1 - (KV[j] + (KV[j + 1] - KV[j]) * f))
    return d + 0.7 * math.sin(2 * math.pi * T / 64)                       # he hangs in the water, rocking a little
def pose(T):
    if T < T_RISE0 or T >= T_GLOW: return 0
    return [0, 1, 2, 1][((T - T_RISE0) // 20) % 4] if POSES == 3 else ((T - T_RISE0) // 20) % POSES
def eyes(T): return 'glow' if T >= T_GLOW else 'stare'
# splash (v7): when the hat breaks the surface, drops fly up around it and fall back. They are drawn in his own
# sprite, above the waterline only (behind BG1 nothing would show anyway), from one 8x8 drop tile.
DROP_T = put(np.pad(np.array([[0, EYEW, 0], [RIMI, EYEW, RIMI], [0, RIMI, 0]], np.uint8), ((0, 5), (0, 5))))
DROP_S = put(np.pad(np.array([[RIMI]], np.uint8), ((0, 7), (0, 7))))
hat_cols = np.where(U[:int(meta['eye_bottom'])].any(0))[0]
HL, HR = hat_cols.min() - AX, hat_cols.max() - AX
_r = np.random.default_rng(17)
SPLASH = []
for i in range(16):
    x0 = _r.uniform(HL, HR); side = -1 if x0 < (HL + HR) / 2 else 1
    SPLASH.append(dict(x0=x0, vx=side * _r.uniform(0.15, 0.6), vy=-_r.uniform(0.9, 2.4), t0=_r.integers(0, 10),
                       big=_r.random() < 0.5))
# v16: water runs off him while he rises: drips fall from the beard and coat back into the sea (1 px drop tile)
DRIP = []
_rd = np.random.default_rng(41)
_cols = np.where(U[WAIST - 30:WAIST].any(0))[0] - AX
for i in range(70):
    DRIP.append(dict(t0=int(_rd.uniform(T_RISE0 - 4, T_GLOW + 30)), x=int(_rd.choice(_cols)), h=_rd.uniform(6, 34)))
def drips(T, d):
    out = []
    for dp in DRIP:
        t = T - dp['t0']
        if t < 0: continue
        y = -dp['h'] + 0.12 * t * t                    # relative to the waterline, falling
        if y >= -1: continue
        if dp['h'] > (-TOP - d) - 6: continue           # he is not that far out of the water yet
        out.append((dp['x'], int(round(y)) - d, 8, 8, DROP_S))
    return out
def drops(T, d):
    out = []
    for sp in SPLASH:
        t = T - T_UP0 - sp['t0']
        if t < 0: continue
        y = sp['vy'] * t + 0.09 * t * t
        if y >= 0: continue                          # back in the water
        x = sp['x0'] + sp['vx'] * t
        out.append((int(round(x)) - 1, int(round(y)) - d - 1, 8, 8, DROP_T if sp['big'] else DROP_S))
    return out
cells = []; cell_ix = {}
def cell_for(oam_list):
    key = tuple(oam_list)
    if key not in cell_ix: cell_ix[key] = len(cells); cells.append(list(oam_list))
    return cell_ix[key]
EMPTY = cell_for([])
seq0 = []
for T in range(0, T_END):
    d = int(round(depth(T)))
    ol = [o for o in oams[(pose(T), eyes(T))] if o[1] < -d]               # only what is above the water
    if T >= T_GONE: ol = []
    elif T >= T_GREEN:                                   # the ghost: palette 0 (green), then dissolving
        src = dis_oams[1] if T >= T_D2 else dis_oams[0] if T >= T_D1 else ol
        ol = [o[:5] + (3 if T >= T_D2 else 0, 0) for o in src if o[1] < -d]
        # (OBJ semi-transparent mode was tried in v6: this scene's blend registers make such sprites invisible)
    if ol and T >= T_UP0: ol = cover(d) + ol          # v15: the water in front of him, drawn over his body
    ol = ol + drops(T, d) + (drips(T, d) if ol and T < T_GREEN else [])
    c = cell_for(ol) if ol else EMPTY
    e = dict(cell=c, tx=0, ty=WROW - 96 + d, dur=2)
    if seq0 and seq0[-1]['cell'] == c and seq0[-1]['ty'] == e['ty']: seq0[-1]['dur'] += 2
    else: seq0.append(e)
seq0[-1]['dur'] = 1000
RC0 = len(cells)
for i_, o in enumerate(ring_oams): cells.append(list(o) + refl_oams(i_ / NR_))
RCS = len(cells)                                   # rings alone: the water stirs before anything is above it
for o in ring_oams: cells.append(list(o))
seq1 = []
hw_rows = [(np.where(U[r])[0].max() - np.where(U[r])[0].min()) / 2 if U[r].any() else 0 for r in range(U.shape[0])]
def ring_scale(T):
    if T < T_UP0: return 0.22 + 0.10 * (T - BIRD0) / max(1, T_UP0 - BIRD0)           # the water stirs, nothing yet
    d = depth(T); r = int(np.clip(round(WAIST - d), 0, U.shape[0] - 1))
    return float(np.clip((hw_rows[r] + 2) / HALF, 0.32, 1.0))
for T in range(BIRD0, T_END, 6):                 # the bird: entries every 6 frames
    sc = ring_scale(T)
    if T >= T_GONE:                              # v10: he is gone, the water goes still
        seq1.append(dict(cell=EMPTY, rot=0, sx=1.0, sy=1.0, tx=0, ty=WROW - 96, dur=12)); continue
    seq1.append(dict(cell=(RC0 if T >= T_UP0 + 6 else RCS) + ((T - BIRD0) // 6) % NR_, rot=0, sx=sc, sy=0.55 + 0.45 * sc, tx=0, ty=WROW - 96, dur=12))
seq1[-1]['dur'] = 1000
print('cells', len(cells), 'seq0 entries', len(seq0), 'seq1 entries', len(seq1))
# ---------------------------------------------------------------- NCGR
ntiles = len(tiledata) // 32                     # v7: with the splash drops
assert ntiles <= 1024, f'{ntiles} tiles: over the 32 KB OBJ VRAM of the intro'
hdr = bytearray(lz10_dec(gs[24])[:16 + 32])
rahc = 32 + len(tiledata)
struct.pack_into('<I', hdr, 8, 16 + rahc); struct.pack_into('<I', hdr, 16 + 4, rahc); struct.pack_into('<I', hdr, 16 + 24, len(tiledata))
ncgr = bytes(hdr) + bytes(tiledata)
# ---------------------------------------------------------------- NCER
def oam(x, y, w, h, tile, palno=1, mode=0):
    shp, sz = INV[(w, h)]
    return struct.pack('<HHH', (shp << 14) | (mode << 10) | (y & 255), (sz << 14) | (x & 511), (palno << 12) | tile)
kb_cells = []
for ol in cells:
    if not ol:
        kb_cells.append((0x900, (0, 0, 0, 0), [])); continue
    xs_ = []; ys_ = []; ob = []
    for o in ol:
        x, y, w, h, t = o[:5]
        ob.append(oam(*o)); xs_ += [x, x + w - 1]; ys_ += [y, y + h - 1]
    bb = (max(xs_), max(ys_), min(xs_), min(ys_))
    r = int(np.ceil(max(np.hypot(a, b) for a in (bb[0], bb[2]) for b in (bb[1], bb[3])) / 4))
    kb_cells.append((0x900 | min(r, 0x3f), bb, ob))
kb = bytearray(b'KBEC' + b'\0' * 4 + struct.pack('<HHIIII', len(kb_cells), 1, 0x18, 0, 0, 0) + b'\0' * 4)
table = bytearray(); oamb = bytearray()
for attr, bb, ob in kb_cells:
    table += struct.pack('<HHI4h', len(ob), attr, len(oamb), *bb); oamb += b''.join(ob)
kb += table + oamb
while len(kb) % 4: kb += b'\0'
struct.pack_into('<I', kb, 4, len(kb))
_, _, osecs = sections(lz10_dec(gs[26]))
rest = osecs[b'LBAL'][1] + osecs[b'TXEU'][1]
ncer = b'RECN' + struct.pack('<HHIHH', 0xFEFF, 0x0100, 16 + len(kb) + len(rest), 16, 3) + bytes(kb) + rest
# ---------------------------------------------------------------- NANR: 0 = Gravriel (position only), 1 = rings (affine), 2 = old
an = lz10_dec(gs[25]) if gs[25][0] == 0x10 else gs[25]
oldan = read_nanr(an)
seqs = [dict(loop=0, el=2, at=1, pm=1, frames=seq0), dict(loop=0, el=1, at=1, pm=1, frames=seq1),
        dict(loop=0, el=0, at=1, pm=2, frames=[dict(cell=0, dur=8)])]
data = bytearray(); ftab = bytearray(); stab = bytearray(); nfr = 0
for sq in seqs:
    stab += struct.pack('<HHHHII', len(sq['frames']), sq['loop'], sq['el'], sq['at'], sq['pm'], len(ftab))
    for fr in sq['frames']:
        ftab += struct.pack('<IHH', len(data), fr['dur'], 0xBEEF)
        if sq['el'] == 0: data += struct.pack('<H', fr['cell'])
        elif sq['el'] == 1: data += struct.pack('<HHiihh', fr['cell'], fr['rot'], int(round(fr['sx'] * 4096)), int(round(fr['sy'] * 4096)), fr['tx'], fr['ty'])
        else: data += struct.pack('<HHhh', fr['cell'], 0xBEEF, fr['tx'], fr['ty'])
        nfr += 1
    while len(data) % 4: data += b'\0'
so = 24; fo = so + len(stab); ao = fo + len(ftab)
body = struct.pack('<HHIIIII', len(seqs), nfr, so, fo, ao, 0, 0) + stab + ftab + data
knba = b'KNBA' + struct.pack('<I', 8 + len(body)) + body
_, _, asecs = sections(an)
nanr = b'RNAN' + struct.pack('<HHIHH', 0xFEFF, 0x0100, 16 + len(knba) + len(asecs[b'LBAL'][1] + asecs[b'TXEU'][1]), 16, 3) + knba + asecs[b'LBAL'][1] + asecs[b'TXEU'][1]
chk = read_nanr(nanr)
assert chk['seqs'][0]['frames'][3]['ty'] == seq0[3]['ty'] and chk['seqs'][1]['frames'][2]['cell'] == seq1[2]['cell']
# ---------------------------------------------------------------- NCLR: palette 1 = his colours
cl = bytearray(lz10_dec(gs[23]) if gs[23][0] == 0x10 else gs[23])
_, _, ps = sections(bytes(cl)); po = ps[b'TTLP'][0]; base = po + 8 + struct.unpack_from('<I', cl, po + 20)[0]
GH = []                                          # palette 0: the ghost - every colour turned into pale sea green
for i, c in enumerate(PAL[1:16], 1):
    l = (0.3 * c[0] + 0.55 * c[1] + 0.15 * c[2])
    g = (min(248, 0.35 * l + 10), min(248, 1.05 * l + 60), min(248, 0.8 * l + 44))
    if i in (meta['index']['eyeW'], meta['index']['iris']): g = (200, 255, 230)
    struct.pack_into('<H', cl, base + 2 * i, (int(g[0]) >> 3) | (int(g[1]) >> 3) << 5 | (int(g[2]) >> 3) << 10)
for i, c in enumerate(PAL[1:16], 1):
    struct.pack_into('<H', cl, base + 2 * (16 + i), (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10)
BEHIND = np.array([24, 40, 48])                   # palette 3: the ghost half faded into the night behind him
for i, c in enumerate(PAL[1:16], 1):
    l = (0.3 * c[0] + 0.55 * c[1] + 0.15 * c[2])
    g = np.array((min(248, 0.35 * l + 10), min(248, 1.05 * l + 60), min(248, 0.8 * l + 44)))
    if i in (meta['index']['eyeW'], meta['index']['iris']): g = np.array((200, 255, 230))
    g = (g * 0.45 + BEHIND * 0.55).astype(int)
    struct.pack_into('<H', cl, base + 2 * (48 + i), (int(g[0]) >> 3) | (int(g[1]) >> 3) << 5 | (int(g[2]) >> 3) << 10)
for i, c in enumerate(SEA_PAL, 1):                # palette 2: the water strip
    struct.pack_into('<H', cl, base + 2 * (32 + i), (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10)
gs[23] = bytes(cl); gs[24] = lz10_enc(ncgr); gs[25] = lz10_enc(nanr); gs[26] = lz10_enc(ncer)
assert lz10_dec(gs[24]) == ncgr and lz10_dec(gs[26]) == ncer and lz10_dec(gs[25]) == nanr
open(OUTN, 'wb').write(pack(gs))
# per-line OBJ cost (normal sprites: w cycles + overhead; worst case counted as affine 10 + 2w) at full height + rings
cost = np.zeros(192)
for (x, y, w, h, t) in oams[(0, 'glow')] + ring_oams[0]:
    a_ = WROW + y; cost[max(0, a_):max(0, min(192, a_ + h))] += 10 + 2 * w
print(f'tiles {ntiles}/1024, worst line ~{cost.max():.0f}/2130, sprites at the end {len(oams[(0, "glow")]) + len(ring_oams[0])}/128')
print('ok', OUTN)
