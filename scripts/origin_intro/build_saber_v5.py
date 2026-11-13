"""Opening movie scene 1: the 3D-rendered Sabertann sails in over the water instead of Ho-Oh flying out of the sun.
Reads saber3d/px/f*.png (pixel frames) + pal.json, writes gs_opening (a/2/6/2) members 23 (palette), 24 (tiles),
25 (animation: path, zoom, roll) and 26 (cells) into out_a262_saber.narc.
Timing facts (pret src/intro_movie_scene_1.c + emulator): the sprite sits at (128,96), the animation runs 2 ticks per
frame, the fade to white starts 90 frames after it appears and takes ~65 frames."""
import numpy as np, struct, json, sys, math, os
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g2d import *
from lz import lz10_enc
from narc import unpack, pack
OUTN = sys.argv[1] if len(sys.argv) > 1 else 'out_a262_saber.narc'
SRC = '../rc8/x_rc8/files/a/2/6/2'
HERE = os.path.dirname(os.path.abspath(__file__))
# detail levels: far away the ship uses a small render with few sprites (the OBJ engine draws at most
# 2130 cycles per line; an affine double-size sprite of width w costs 10 + 4w on every line its box touches)
LODS = [dict(dir='saber3d/v5px', ppu=float(os.environ.get('SAB_PPU0', 22)), frames=[int(v) for v in os.environ.get('SAB_F0', '1,2,3,4,5,6,7').split(',')], smin=float(os.environ.get('SAB_S0', 0.5))),
        dict(dir='saber3d/v5px14', ppu=float(os.environ.get('SAB_PPU1', 13)), frames=[int(v) for v in os.environ.get('SAB_F1', '1,3').split(',')], smin=float(os.environ.get('SAB_S1', 0.2))),
        dict(dir='saber3d/v5px7', ppu=7, frames=[int(v) for v in os.environ.get('SAB_F2', '1').split(',')], smin=0.0)]
CELL = int(os.environ.get('SAB_CELL', 32))     # base layer: sprites of up to CELL px laid out with 1 px overlap (no seams)
PAL = json.load(open(os.path.join(HERE, LODS[0]['dir'], 'pal.json')))['palette']
VALID = set(SHAPE.values()); INV = {v: k for k, v in SHAPE.items()}
gs = unpack(open(SRC, 'rb').read())
cg = read_ncgr(lz10_dec(gs[24]))
MOON = os.environ.get('SAB_MOON')          # night scene: a 64x64 moon (own tiles, no mirroring) replaces the sun
if MOON:
    mi = np.asarray(Image.open(MOON).convert('RGBA'))
    mkey = np.where(mi[..., 3] > 127, (mi[..., 0] >> 3).astype(int) | (mi[..., 1] >> 3).astype(int) << 5 | (mi[..., 2] >> 3).astype(int) << 10, -1)
    MOON_PAL = sorted(int(v) for v in np.unique(mkey) if v >= 0)
    assert len(MOON_PAL) <= 15, len(MOON_PAL)
    midx = np.zeros(mkey.shape, np.uint8)
    for ci, v in enumerate(MOON_PAL, 1): midx[mkey == v] = ci
    tiledata = bytearray()
    for qy in (0, 32):
        for qx in (0, 32):                   # quadrants TL, TR, BL, BR = tiles 0, 16, 32, 48
            q = midx[qy:qy + 32, qx:qx + 32]
            for ty in range(0, 32, 8):
                for tx in range(0, 32, 8):
                    for row in q[ty:ty + 8, tx:tx + 8]:
                        for k in range(0, 8, 2): tiledata.append(int(row[k]) | int(row[k + 1]) << 4)
    SUN_TILES = 64
else:
    SUN_TILES = 16
    tiledata = bytearray(cg['data'][:SUN_TILES * 32])
store = {}
def put(block):
    key = (block.shape, block.tobytes())
    if key in store: return store[key]
    start = len(tiledata) // 32
    for ty in range(0, block.shape[0], 8):
        for tx in range(0, block.shape[1], 8):
            for row in block[ty:ty + 8, tx:tx + 8]:
                for k in range(0, 8, 2): tiledata.append(int(row[k]) | int(row[k + 1]) << 4)
    store[key] = start; return start
def fit(n, cap):
    return min(s for s in (8, 16, 32, 64) if s >= n and s <= cap)
def base_oams(img, AX, AY, box=None):
    """picture -> sprites on a grid with 1 px overlap, each shrunk to its content.
    box = (x0, y0, x1, y1): a grid shared by all frames, so unchanged areas give identical blocks (shared tiles)"""
    ys, xs = np.where(img > 0)
    x0, y0, x1, y1 = box if box else (xs.min() - 1, ys.min() - 1, xs.max(), ys.max())
    P = np.pad(img, ((0, CELL + 64), (0, CELL + 64)))
    out = []
    for y in range(y0, y1 + 1, CELL - 1):
        for x in range(x0, x1 + 1, CELL - 1):
            b = P[y:y + CELL, x:x + CELL]
            if not b.any(): continue
            yy, xx = np.where(b > 0)
            w = fit(xx.max() - xx.min() + 1, CELL); h = fit(yy.max() - yy.min() + 1, CELL)
            if (w, h) not in VALID:
                if w > h: h = w // 2
                else: w = h // 2
            ox = min(xx.min(), CELL - w); oy = min(yy.min(), CELL - h)
            blk = P[y + oy:y + oy + h, x + ox:x + ox + w]
            out.append((x + ox - AX, y + oy - AY, w, h, put(blk)))
    return out
cells_oams = []          # cell 1.. in order
for L in LODS:
    meta = json.load(open(os.path.join(HERE, L['dir'], 'pal.json')))
    AX, AY = int(round(meta['anchor'][0])), int(round(meta['anchor'][1]))
    frames = [np.array(Image.open(os.path.join(HERE, L['dir'], f'f{i}.png'))) for i in L['frames']]
    ys, xs = np.where(frames[0] > 0)
    L['H0'] = (AY - ys.min()) * 30 / L['ppu']           # height above the waterline in LOD0 px (swim frame)
    U = np.any([f > 0 for f in frames], 0); ys, xs = np.where(U)
    box = (max(0, xs.min() - 1), max(0, ys.min() - 1), xs.max(), ys.max())   # never start the grid at -1 (numpy would wrap)
    t0 = len(tiledata) // 32
    L['cell0'] = len(cells_oams) + 1
    for f in frames:
        cells_oams.append(base_oams(f, AX, AY, box))
    print(f"LOD ppu {L['ppu']}: frames {len(frames)}, tiles {len(tiledata) // 32 - t0}, sprites/frame {[len(o) for o in cells_oams[L['cell0'] - 1:]]}")
ntiles = len(tiledata) // 32
print(f'tiles {ntiles}/1024')
if not os.environ.get('SAB_DRY'): assert ntiles <= 1024, 'over the 32 KB OBJ VRAM of the intro'
H0 = LODS[0]['H0']
# ---------------------------------------------------------------- NCGR
hdr = bytearray(lz10_dec(gs[24])[:16 + 32])
rahc = 32 + len(tiledata)
struct.pack_into('<I', hdr, 8, 16 + rahc); struct.pack_into('<I', hdr, 16 + 4, rahc); struct.pack_into('<I', hdr, 16 + 24, len(tiledata))
ncgr = bytes(hdr) + bytes(tiledata)
# ---------------------------------------------------------------- NCER (cell 0 = sun, kept)
old = read_ncer(lz10_dec(gs[26]))
def oam(x, y, w, h, tile, palno=1):
    shp, sz = INV[(w, h)]
    return struct.pack('<HHH', (shp << 14) | (y & 255), (sz << 14) | (x & 511), (palno << 12) | tile)
cells = []
c0 = old['cells'][0]
if MOON:
    QT = {(-32, -32): 0, (0, -32): 16, (-32, 0): 32, (0, 0): 48}
    cells.append((c0['attr'], c0['bbox'], [struct.pack('<HHH', o['a0'], o['a1'] & ~0x3000, (o['a2'] & ~1023) | QT[(o['x'], o['y'])]) for o in c0['oams']]))
else:
    cells.append((c0['attr'], c0['bbox'], [struct.pack('<HHH', o['a0'], o['a1'], o['a2']) for o in c0['oams']]))
for ol in cells_oams:
    xs_ = []; ys_ = []; ob = []
    for (x, y, w, h, t) in ol:
        ob.append(oam(x, y, w, h, t)); xs_ += [x, x + w - 1]; ys_ += [y, y + h - 1]
    bb = (max(xs_), max(ys_), min(xs_), min(ys_))
    r = int(np.ceil(max(np.hypot(a, b) for a in (bb[0], bb[2]) for b in (bb[1], bb[3])) / 4))
    cells.append((0x900 | min(r, 0x3f), bb, ob))
kb = bytearray(b'KBEC' + b'\0' * 4 + struct.pack('<HHIIII', len(cells), 1, 0x18, 0, 0, 0) + b'\0' * 4)
table = bytearray(); oamb = bytearray()
for attr, bb, ob in cells:
    table += struct.pack('<HHI4h', len(ob), attr, len(oamb), *bb); oamb += b''.join(ob)
kb += table + oamb
while len(kb) % 4: kb += b'\0'
struct.pack_into('<I', kb, 4, len(kb))
_, _, osecs = sections(lz10_dec(gs[26]))
rest = osecs[b'LBAL'][1] + osecs[b'TXEU'][1]
ncer = b'RECN' + struct.pack('<HHIHH', 0xFEFF, 0x0100, 16 + len(kb) + len(rest), 16, 3) + bytes(kb) + rest
# ---------------------------------------------------------------- NANR: sun kept, new path for the ship
an = lz10_dec(gs[25]) if gs[25][0] == 0x10 else gs[25]
oldan = read_nanr(an)
HORIZON = 164            # first water row on the bottom screen
C_WL = float(os.environ.get('SAB_CWL', 0.22))   # waterline drop per px of height (low camera)
VPX = float(os.environ.get('SAB_VPX', 56)); XEND = float(os.environ.get('SAB_XEND', -8))
S0, S_FADE, T_FADE, S_MAX = 0.06, 0.88, 180, 2.4
R = math.log(S_FADE / S0) / T_FADE
STROKE = 32              # ticks per paddle cycle (4 frames x 8 ticks), about Ho-Oh's wingbeat speed
T_LEAP = int(os.environ.get('SAB_TLEAP', 146))   # he bursts out of the water just before the fade to white
STEP = 4
path = []
t = 0
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
while True:
    s0 = S0 * math.exp(R * t)
    leap = t >= T_LEAP
    AIR = os.environ.get('SAB_AIRLOOP') == '1'        # v12: keep moving through the fade, as Ho-Oh keeps flying
    grow = smooth((t - T_LEAP) / (170 if AIR else 56))
    s = min(S_MAX, LODS[0]['ppu'] / 30 * 1.96, s0 * (1 + 0.7 * grow))
    L = LODS[0] if leap else next(L for L in LODS if s >= L['smin'])
    if leap:
        dt = t - T_LEAP
        cell = L['cell0'] + (4 if dt < 14 else 5 if dt < 32 else 6)
        if os.environ.get('SAB_OVER') == '1':      # v13: frames 8 and 9 carry him up and over the viewer
            cell = L['cell0'] + (4 if dt < 14 else 5 if dt < 30 else 6 if dt < 50 else 7 if dt < 74 else 8)
            if os.environ.get('SAB_NOF5') == '1':      # frame 5 left out (tiles): the run's gather pose leads into frame 6
                cell = L['cell0'] + (4 if dt < 30 else 5 if dt < 50 else 6 if dt < 74 else 7)
        bob = 0.0; roll = 0.0
        if AIR and dt >= 32:                     # airborne: the paws pump between the last two leap frames, a gentle sway
            cell = L['cell0'] + (6 if ((dt - 32) // 12) % 2 == 0 else 5)
            bob = -0.06 * (dt - 32) * s - 1.0 * s * math.sin(2 * math.pi * (dt - 32) / 48)
            roll = 1.2 * math.sin(2 * math.pi * (dt - 32) / 96)
    else:
        nf = 4 if L is LODS[0] else len(L['frames'])
        cell = L['cell0'] + (t // (STROKE // nf)) % nf
        bob = 1.3 * s * math.sin(2 * math.pi * t / STROKE)
        roll = 1.5 * math.sin(2 * math.pi * t / STROKE + 1.3)
    yw = HORIZON + C_WL * H0 * s + bob
    ds = s * 30 / L['ppu']
    tx = 0                                       # straight at the camera, like Ho-Oh
    ty = int(round(yw - 96))
    rot = int(round(roll / 360 * 65536)) & 0xFFFF
    path.append(dict(cell=cell, rot=rot, sx=ds, sy=ds, tx=tx, ty=ty, dur=STEP, s=s))
    t += STEP
    if t > 330: break
path[-1]['dur'] = 1000
NCELL = len(cells_oams)
seqs = [oldan['seqs'][0], dict(nf=len(path), loop=0, el=1, at=1, pm=1, frames=path),
        dict(nf=4, loop=0, el=0, at=1, pm=2, frames=[dict(cell=1 + i, dur=8) for i in range(4)])]
data = bytearray(); ftab = bytearray(); stab = bytearray()
nfr = 0
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
arest = asecs[b'LBAL'][1] + asecs[b'TXEU'][1]
nanr = b'RNAN' + struct.pack('<HHIHH', 0xFEFF, 0x0100, 16 + len(knba) + len(arest), 16, 3) + knba + arest
chk = read_nanr(nanr)
assert chk['seqs'][1]['frames'][5]['cell'] == path[5]['cell'] and chk['seqs'][0]['frames'][3]['ty'] == oldan['seqs'][0]['frames'][3]['ty']
# ---------------------------------------------------------------- NCLR palette 1
cl = bytearray(lz10_dec(gs[23]) if gs[23][0] == 0x10 else gs[23])
_, _, ps = sections(bytes(cl)); po = ps[b'TTLP'][0]; base = po + 8 + struct.unpack_from('<I', cl, po + 20)[0]
for i, c in enumerate(PAL[1:16], 1):
    struct.pack_into('<H', cl, base + 2 * (16 + i), (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10)
if MOON:
    for i in range(1, 16):
        struct.pack_into('<H', cl, base + 2 * i, MOON_PAL[i - 1] if i <= len(MOON_PAL) else 0)
gs[23] = bytes(cl); gs[24] = lz10_enc(ncgr); gs[25] = lz10_enc(nanr); gs[26] = lz10_enc(ncer)
assert lz10_dec(gs[24]) == ncgr and lz10_dec(gs[26]) == ncer and lz10_dec(gs[25]) == nanr
open(OUTN, 'wb').write(pack(gs))
# per-scanline OBJ cost along the path (sun: 4 affine 32x32 at y 65..129 = 148 per line there)
worst = (0, None)
for e in path[:-1] + [path[-1]]:
    cost = np.zeros(192)
    cost[65:129] += 148
    for (x, y, w, h, tl) in cells_oams[e['cell'] - 1]:
        cy = 96 + e['ty'] + (y + h / 2) * e['sx']
        a_, b_ = int(math.floor(cy - h)), int(math.ceil(cy + h))
        cost[max(0, a_):max(0, min(192, b_))] += 10 + 4 * w
    if cost.max() > worst[0]: worst = (cost.max(), (round(e['s'], 2), e['cell']))
print(f'worst line along the path: {worst[0]:.0f}/2130 cycles at scale/cell {worst[1]}')
json.dump(dict(path=path, H0=H0, lods=[{k: v for k, v in L.items()} for L in LODS]), open(OUTN + '.json', 'w'))
print('ok', OUTN, 'path entries', len(path))
