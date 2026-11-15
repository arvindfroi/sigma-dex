"""Scene 5: Moosus on the rock in the sea, in place of Suicune (Arvind 2026-11-15).
a/2/6/2: screen 62 (BG, 256x256, the creature at cells x 0-4, y 17-23), charset 60 (shared with screen 64; screen 62 alone
uses tiles 2-30), palette 31 bank 3 (only screen 62 uses it). The picture is Qwen's swap (sc5/gen_sc5.py) shrunk from 8x:
magenta keyed at full size, each 8x8 block -> one pixel (mean of its non-magenta pixels, transparent when mostly magenta),
15 colours by k-means, tiles deduped with flips into slots 2-30 (more slots only if FREE_EXTRA allows).
python sc5/build_sc5.py IN.narc OUT.narc PICTURE.png"""
import sys, os, struct, numpy as np
from PIL import Image
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from g2d import lz10_dec, sections
from lz import lz10_enc
from narc import unpack, pack
SRC, DST, PIC = sys.argv[1:4]
X0, Y0, W, H = 0, 128, 48, 64          # the crop given to Qwen: screen pixels x 0-47, y 128-191 (cells 0-5, 16-23)
SCR, CHR, PAL, BANK = 62, 60, 31, 3
SLOTS = list(range(2, 31)) + list(range(444, 444 + int(os.environ.get('SC5_EXTRA', 0))))   # 444-767: never-used tiles of charset 60 (it holds 768)
NCOL = 15
F = unpack(open(SRC, 'rb').read())
def dec(i): return lz10_dec(F[i]) if F[i][:1] == b'\x10' else F[i]
def put(i, d): F[i] = lz10_enc(bytes(d)) if F[i][:1] == b'\x10' else bytes(d)
def to_lab(c):
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def kmeans(X, k, it=20, seed=0):
    rng = np.random.default_rng(seed); C = X[rng.choice(len(X), min(k, len(X)), replace=False)]
    for _ in range(it):
        a = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([X[a == j].mean(0) if (a == j).any() else C[j] for j in range(len(C))])
    return C
# 1. shrink: Qwen's picture is the 8x crop, 384x512
src = np.asarray(Image.open(PIC).convert('RGB').resize((W * 8, H * 8), Image.NEAREST)).astype(np.float32)
mag = (src[..., 0] > 200) & (src[..., 2] > 200) & (src[..., 1] < 80) & (np.abs(src[..., 0] - src[..., 2]) < 45)   # tight: the violet crown tips are close to magenta
blk = lambda a: a.reshape(H, 8, W, 8, *a.shape[2:]).swapaxes(1, 2).reshape(H, W, 64, *a.shape[2:])
mb = blk(mag); sb = blk(src)
opaque = mb.mean(-1) < 0.5
rgb = np.zeros((H, W, 3), np.float32)
for y in range(H):
    for x in range(W):
        if opaque[y, x]:
            px = sb[y, x][~mb[y, x]]
            # the most common colour of the block (pixel art: a block is mostly one colour), not a blend
            q = (px // 8).astype(int); key = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
            v, c = np.unique(key, return_counts=True); rgb[y, x] = px[key == v[c.argmax()]].mean(0)
# 2. palette: 15 colours
uq = np.unique(np.round(rgb[opaque]).astype(int), axis=0)
if len(uq) <= NCOL: C = to_lab(uq.astype(np.float32))          # a finished sprite (v4): its own colours exactly
else: C = None
X = to_lab(rgb[opaque])
if C is None: C = kmeans(X, NCOL, seed=1)
lab = to_lab(rgb); idx = ((lab[..., None, :] - C[None, None]) ** 2).sum(-1).argmin(-1) + 1
idx[~opaque] = 0
pal = np.array([rgb[opaque][((X - c) ** 2).sum(-1).argmin()] for c in C])
pal = np.round(np.clip(pal, 0, 255) / 255 * 31) * 255 / 31
# 3. tiles into the slots
d62 = bytearray(dec(SCR)); mg, v, s = sections(bytes(d62)); o, sc = s[b'NRCS']; sz = struct.unpack_from('<I', sc, 16)[0]
eoff = o + 20; e = np.array(struct.unpack_from(f'<{sz // 2}H', sc, 20)).reshape(32, 32)
tiles = {}; new = []; ent = {}
for cy in range(H // 8):
    for cx in range(W // 8):
        t = idx[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8]
        if not t.any(): ent[(cy, cx)] = 0; continue
        key = None
        for hf in (0, 1):
            for vf in (0, 1):
                tt = t[:, ::-1] if hf else t; tt = tt[::-1] if vf else tt
                if tt.tobytes() in tiles: key = (tiles[tt.tobytes()], hf, vf); break
            if key: break
        if not key: tiles[t.tobytes()] = len(new); new.append(t); key = (len(new) - 1, 0, 0)
        ent[(cy, cx)] = SLOTS[key[0]] | key[1] << 10 | key[2] << 11 | BANK << 12 if key[0] < len(SLOTS) else None
if len(new) > len(SLOTS): raise SystemExit(f'{len(new)} tiles, only {len(SLOTS)} slots')
g = bytearray(dec(CHR)); mg, v, s = sections(bytes(g)); o, sc = s[b'RAHC']; tbase = o + 8 + struct.unpack_from('<I', sc, 28)[0]
for k, t in enumerate(new):
    f = t.reshape(-1); g[tbase + SLOTS[k] * 32: tbase + SLOTS[k] * 32 + 32] = bytes((f[0::2] | (f[1::2] << 4)).astype(np.uint8))
for k in range(len(new), len(SLOTS)): g[tbase + SLOTS[k] * 32: tbase + SLOTS[k] * 32 + 32] = bytes(32)
e[(Y0 // 8):(Y0 + H) // 8, (X0 // 8):(X0 + W) // 8] = 0
for (cy, cx), val in ent.items(): e[Y0 // 8 + cy, X0 // 8 + cx] = val
struct.pack_into(f'<{e.size}H', d62, eoff, *e.reshape(-1).tolist())
put(SCR, d62); put(CHR, g)
p = bytearray(dec(PAL)); mg, v, s = sections(bytes(p)); o, sc = s[b'TTLP']; pbase = o + 8 + struct.unpack_from('<I', sc, 20)[0]
def bgr(c): r, gg, b = (int(round(x / 255 * 31)) for x in c); return r | gg << 5 | b << 10
old0 = struct.unpack_from('<H', p, pbase + 2 * 16 * BANK)[0]
for c in range(1, 16): struct.pack_into('<H', p, pbase + 2 * (16 * BANK + c), bgr(pal[c - 1]) if c <= len(pal) else 0)
put(PAL, p)
open(DST, 'wb').write(pack(F))
prev = np.zeros((H, W, 4), np.uint8); prev[..., :3] = np.vstack([[0, 0, 0], pal])[idx].astype(np.uint8); prev[..., 3] = (idx > 0) * 255
Image.fromarray(prev).save(os.path.join(HERE, 'preview.png'))
print('tiles', len(new), 'of', len(SLOTS), 'colours', len(pal))
