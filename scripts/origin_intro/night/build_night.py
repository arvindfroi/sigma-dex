"""Put the tropical night backgrounds into gs_opening (a/2/6/2) for opening scene 1.
python night/build_night.py IN.narc OUT.narc
Replaces: 0 (sub BG palette), 1 (main BG palette), 6 (sub BG3 tiles), 7 (main BG1-3 tiles, shared),
15 (sub BG3 map), 16/17/18 (main BG1/BG2/BG3 maps). Palette 2 stays (the logo layer uses it) and so does
sub palette 0 (copyright text). Checks: <= 15 colours per tile, palettes fit, tiles <= 1024, exact round trip."""
import sys, os, struct
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from g2d import *
from lz import lz10_enc
from narc import unpack, pack
IN, OUT = sys.argv[1], sys.argv[2]
ART = os.path.join(HERE, 'art')
gs = unpack(open(IN, 'rb').read())

def load(name):
    im = np.asarray(Image.open(os.path.join(ART, name)).convert('RGBA'))
    c5 = (im[..., :3] >> 3).astype(np.int32)
    key = c5[..., 0] | c5[..., 1] << 5 | c5[..., 2] << 10          # BGR555 value
    key = np.where(im[..., 3] > 127, key, -1)                        # -1 = transparent
    full = np.full((256, 256), -1, np.int32); full[:192] = key
    return full

def pack_palettes(layers, slots):
    """layers: list of (name, key image). Returns per-layer per-cell palette slot and the palettes."""
    cellsets = []
    for name, k in layers:
        for ty in range(32):
            for tx in range(32):
                s = frozenset(int(v) for v in np.unique(k[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]) if v >= 0)
                if len(s) > 15: raise SystemExit(f'{name} tile {tx},{ty} has {len(s)} colours')
                cellsets.append(s)
    uniq = sorted(set(s for s in cellsets if s), key=lambda s: -len(s))
    pals = []
    where = {}
    for s in uniq:
        best = None
        for i, p in enumerate(pals):
            if s <= p: best = (0, i); break
            add = len(s - p)
            if len(p | s) <= 15 and (best is None or add < best[0]): best = (add, i)
        if best is None:
            pals.append(set(s)); where[s] = len(pals) - 1
        else:
            pals[best[1]] |= s; where[s] = best[1]
    if len(pals) > len(slots): raise SystemExit(f'needs {len(pals)} palettes, only {len(slots)} free')
    # every set must be inside its palette (later merges only grow palettes)
    order = [sorted(p) for p in pals]
    return where, order

def build(layers, slots, tiles0=None):
    where, order = pack_palettes(layers, slots)
    tiles = [np.zeros((8, 8), np.uint8)]                     # tile 0: empty
    lookup = {tiles[0].tobytes(): (0, 0)}
    maps = []
    for name, k in layers:
        ent = np.zeros(1024, np.uint16)
        for ty in range(32):
            for tx in range(32):
                blk = k[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                s = frozenset(int(v) for v in np.unique(blk) if v >= 0)
                if not s: ent[ty * 32 + tx] = 0; continue
                pi = where[s]; pal = order[pi]
                idx = np.zeros((8, 8), np.uint8)
                for ci, col in enumerate(pal, 1): idx[blk == col] = ci
                hit = None
                for fl, v in ((0, idx), (1, idx[:, ::-1]), (2, idx[::-1]), (3, idx[::-1, ::-1])):
                    if v.tobytes() in lookup: hit = (lookup[v.tobytes()][0], fl); break
                if hit is None:
                    tiles.append(idx); lookup[idx.tobytes()] = (len(tiles) - 1, 0); hit = (len(tiles) - 1, 0)
                ent[ty * 32 + tx] = hit[0] | hit[1] << 10 | slots[pi] << 12
        maps.append(ent)
    return tiles, maps, order

def ncgr(old_raw, tiles):
    d = lz10_dec(old_raw); mg, ver, secs = sections(d)
    n = len(tiles); n32 = (n + 31) // 32 * 32
    data = bytearray()
    for i in range(n32):
        t = tiles[i] if i < n else np.zeros((8, 8), np.uint8)
        for row in t:
            for x in range(0, 8, 2): data.append(int(row[x]) | int(row[x + 1]) << 4)
    o, s = secs[b'RAHC']
    rahc = bytearray(s[:32]); struct.pack_into('<HH', rahc, 8, n32 // 32, 32); struct.pack_into('<I', rahc, 8 + 16, len(data))
    rahc += data; struct.pack_into('<I', rahc, 4, len(rahc))
    o2, sopc = secs[b'SOPC']; sopc = bytearray(sopc)
    struct.pack_into('<HH', sopc, 12, 32, n32 // 32)
    body = bytes(rahc) + bytes(sopc)
    return lz10_enc(d[:8] + struct.pack('<IHH', 16 + len(body), 16, 2) + body), n

def nscr(old_raw, ent):
    d = bytearray(lz10_dec(old_raw)); mg, ver, secs = sections(bytes(d))
    o, s = secs[b'NRCS']
    struct.pack_into('<1024H', d, o + 20, *[int(v) for v in ent])
    return lz10_enc(bytes(d))

def nclr(old_raw, order, slots):
    d = bytearray(old_raw); mg, ver, secs = sections(bytes(d))
    o, s = secs[b'TTLP']; base = o + 8 + struct.unpack_from('<I', d, o + 20)[0]
    for pal, sl in zip(order, slots):
        for ci in range(16):
            v = pal[ci - 1] if 1 <= ci <= len(pal) else 0
            struct.pack_into('<H', d, base + 2 * (16 * sl + ci), v)
    return bytes(d)

# ---------------- main screen: BG3 sky/sea, BG2 far palms, BG1 near palms (shared tiles)
main_layers = [('BG3', load('bottom.png')), ('BG2', load('far.png')), ('BG1', load('near.png'))]
MAIN_SLOTS = [0, 1, 3, 4, 5, 6, 7, 8, 9]
mt, mmaps, morder = build(main_layers, MAIN_SLOTS)
gs[7], nmain = ncgr(gs[7], mt)
for member, ent in zip((18, 17, 16), mmaps): gs[member] = nscr(gs[member], ent)
gs[1] = nclr(gs[1], morder, MAIN_SLOTS[:len(morder)])
# ---------------- sub screen: BG3 sky
SUB_SLOTS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
st, smaps, sorder = build([('SUB3', load('top.png'))], SUB_SLOTS)
gs[6], nsub = ncgr(gs[6], st)
gs[15] = nscr(gs[15], smaps[0])
gs[0] = nclr(gs[0], sorder, SUB_SLOTS[:len(sorder)])
print(f'main tiles {nmain}/1024, palettes {len(morder)} {[len(p) for p in morder]}; sub tiles {nsub}/1024, palettes {len(sorder)}')
assert nmain <= 1024 and nsub <= 1024

# ---------------- round trip: decode what we wrote and compare with the art
def decode(chr_m, scr_m, pal_m):
    c = read_ncgr(lz10_dec(gs[chr_m])); b = np.frombuffer(c['data'], np.uint8)
    T = np.stack([b & 15, b >> 4], 1).reshape(-1, 8, 8)
    p, _ = read_nclr(gs[pal_m]); P = np.array(p, np.int32)
    mg, ver, secs = sections(lz10_dec(gs[scr_m])); o, s = secs[b'NRCS']
    e = np.array(struct.unpack_from('<1024H', s, 20))
    out = np.full((256, 256), -1, np.int32)
    for k, v in enumerate(e):
        t = T[v & 1023]
        if v & 0x400: t = t[:, ::-1]
        if v & 0x800: t = t[::-1]
        out[(k // 32) * 8:(k // 32) * 8 + 8, (k % 32) * 8:(k % 32) * 8 + 8] = np.where(t > 0, P[(v >> 12) * 16 + t], -1)
    return out
for (name, k), m in zip(main_layers, (18, 17, 16)):
    assert (decode(7, m, 1)[:192] == k[:192]).all(), name
assert (decode(6, 15, 0)[:192] == load('top.png')[:192]).all()
open(OUT, 'wb').write(pack(gs))
print('round trip exact; wrote', OUT)
