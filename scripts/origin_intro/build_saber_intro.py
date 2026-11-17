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
LODS = [dict(dir='saber3d/px', ppu=float(os.environ.get('SAB_PPU0', 26)), frames=list(range(1, 9)), lam=float(os.environ.get('SAB_LAMBDA', 3.0)), smin=float(os.environ.get('SAB_S0', 0.62))),
        dict(dir='saber3d/px18', ppu=18, frames=[int(x) for x in os.environ.get('SAB_F1', '1,5').split(',')], lam=float(os.environ.get('SAB_LAM1', 20.0)), smin=float(os.environ.get('SAB_S1', 0.24))),
        dict(dir='saber3d/px9', ppu=9, frames=[1], lam=80.0, smin=0.0)]
CELL = int(os.environ.get('SAB_CELL', 32))     # base layer: sprites of up to CELL px laid out with 1 px overlap (no seams)
PAL = json.load(open(os.path.join(HERE, LODS[0]['dir'] + '_base', 'pal.json')))['palette']
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
def base_oams(img, AX, AY):
    """static picture -> sprites on a grid with 1 px overlap, each shrunk to its content"""
    ys, xs = np.where(img > 0)
    x0, y0 = xs.min() - 1, ys.min() - 1
    P = np.pad(img, ((0, CELL + 64), (0, CELL + 64)))
    out = []
    for y in range(y0, ys.max() + 1, CELL - 1):
        for x in range(x0, xs.max() + 1, CELL - 1):
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
    meta = json.load(open(os.path.join(HERE, L['dir'] + '_base', 'pal.json')))
    AX, AY = int(round(meta['anchor'][0])), int(round(meta['anchor'][1]))
    base = np.array(Image.open(os.path.join(HERE, L['dir'] + '_base', 'f1.png')))
    frames = [np.array(Image.open(os.path.join(HERE, L['dir'] + '_anim', f'f{i}.png'))) for i in L['frames']]
    NF = len(frames)
    ys, xs = np.where(base > 0)
    L['H0'] = (AY - ys.min()) * 30 / L['ppu']           # height above the waterline in LOD0 px
    t0 = len(tiledata) // 32
    B = base_oams(base, AX, AY)
    # animated layer (flag, foam): quadtree on an 8 px grid, blocks shared between frames
    U = np.any([f > 0 for f in frames], 0); ys, xs = np.where(U)
    gx0 = AX + ((xs.min() - AX) // 8) * 8; gy0 = AY + ((ys.min() - AY) // 8) * 8
    gx1 = AX - ((AX - xs.max() - 1) // 8) * 8; gy1 = AY - ((AY - ys.max() - 1) // 8) * 8
    Wc = -(-(gx1 - gx0) // 64) * 64; Hc = -(-(gy1 - gy0) // 64) * 64
    F = []
    for f in frames:
        c = np.zeros((Hc, Wc), np.uint8)
        sub = f[max(gy0, 0):gy0 + Hc, max(gx0, 0):gx0 + Wc]
        c[max(0, -gy0):max(0, -gy0) + sub.shape[0], max(0, -gx0):max(0, -gx0) + sub.shape[1]] = sub
        F.append(c)
    OX, OY = AX - gx0, AY - gy0
    memo = {}
    def best(x, y, w, h):
        k = (x, y, w, h)
        if k in memo: return memo[k]
        cs = [f[y:y + h, x:x + w] for f in F]
        ne = [c for c in cs if c.any()]
        if not ne:
            memo[k] = (0.0, []); return memo[k]
        own = len({c.tobytes() for c in ne}) * (w * h // 64) + L['lam'] * len(ne) / NF
        opt = (own, [k])
        for parts in (((x, y, w // 2, h), (x + w // 2, y, w // 2, h)), ((x, y, w, h // 2), (x, y + h // 2, w, h // 2))):
            if all((p[2], p[3]) in VALID for p in parts):
                r = [best(*p) for p in parts]; c = sum(a for a, _ in r)
                if c < opt[0]: opt = (c, [q for _, l in r for q in l])
        memo[k] = opt; return opt
    regions = []
    for y in range(0, Hc, 64):
        for x in range(0, Wc, 64):
            regions += best(x, y, 64, 64)[1]
    L['cell0'] = len(cells_oams) + 1
    for f in F:
        ol = []
        for (x, y, w, h) in regions:
            b = f[y:y + h, x:x + w]
            if b.any(): ol.append((x - OX, y - OY, w, h, put(b)))
        cells_oams.append(ol + B)          # animated layer first = drawn on top
    print(f"LOD ppu {L['ppu']}: base sprites {len(B)}, anim frames {NF}, tiles {len(tiledata) // 32 - t0}, sprites/frame {[len(o) for o in cells_oams[L['cell0'] - 1:]]}")
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
S0, S_FADE, T_FADE, S_MAX = 0.06, 0.88, 180, 2.0
R = math.log(S_FADE / S0) / T_FADE
LOOP = 64                # ticks per swim loop (8 cells x 8 ticks)
STEP = 4
path = []
t = 0
while True:
    s = min(S_MAX, S0 * math.exp(R * t))
    k = (s - S0) / (1 - S0)
    bob = 1.3 * s * math.sin(2 * math.pi * t / LOOP)
    yw = HORIZON + C_WL * H0 * s + bob
    L = next(L for L in LODS if s >= L['smin'])
    nf = len(L['frames'])
    cell = L['cell0'] + (t // (LOOP // nf)) % nf
    ds = s * 30 / L['ppu']
    # he sails along his own heading: from the vanishing point of that line on the horizon (right of the moon,
    # by the harbour island) toward the lower left; screen x is linear in the scale for a straight course
    tx = int(round(VPX + (XEND - VPX) * min(s, S_FADE) / S_FADE))
    ty = int(round(yw - 96))
    rot = int(round(2.2 * math.sin(2 * math.pi * t / LOOP + 1.3) / 360 * 65536)) & 0xFFFF
    path.append(dict(cell=cell, rot=rot, sx=ds, sy=ds, tx=tx, ty=ty, dur=STEP, s=s))
    t += STEP
    if t > 330: break
path[-1]['dur'] = 1000
NCELL = len(cells_oams)
seqs = [oldan['seqs'][0], dict(nf=len(path), loop=0, el=1, at=1, pm=1, frames=path),
        dict(nf=8, loop=0, el=0, at=1, pm=2, frames=[dict(cell=1 + i, dur=8) for i in range(8)])]
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
