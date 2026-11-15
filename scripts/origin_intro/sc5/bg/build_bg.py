"""Scene 5 night background into a/2/6/2 (Arvind 2026-11-15). Writes the two pictures from paint_night.py:
  night61.png -> screen 61 (top screen sky), map rows 0-44, charset 59, palette 39 banks 7-8 (free; bank 0 is shared with
                 the deer strips of scene 3). Tiles 1-511 except the ones screen 63 (the light trail, kept) uses.
  night64.png -> screen 64 (bottom screen sky, fjord, sea), map rows 12-51 (pixels 96-415), charset 60, palette 31 banks
                 0, 4, 5, 2, 6 (free or its own). Tiles 1-767 except Moosus' (screen 62: 2-30 and 444+).
Each 8x8 tile is deduped with flips; tiles are packed into palette banks of 15 colours (greedy, most colours first).
python sc5/bg/build_bg.py IN.narc OUT.narc [MOOSUS_EXTRA=16]"""
import sys, os, struct, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..'))
from g2d import lz10_dec, sections
from lz import lz10_enc
from narc import unpack, pack
SRC, DST = sys.argv[1:3]; MX = int(sys.argv[3]) if len(sys.argv) > 3 else 16
F = unpack(open(SRC, 'rb').read())
dec = lambda i: lz10_dec(F[i]) if F[i][:1] == b'\x10' else F[i]
def put(i, d): F[i] = lz10_enc(bytes(d)) if F[i][:1] == b'\x10' else bytes(d)
def scr_entries(i):
    d = bytearray(dec(i)); mg, v, s = sections(bytes(d)); o, sc = s[b'NRCS']; sz = struct.unpack_from('<I', sc, 16)[0]
    return d, o + 20, np.array(struct.unpack_from(f'<{sz // 2}H', sc, 20)).reshape(-1, 32)
def bgr(c): r, g, b = (int(round(x / 255 * 31)) for x in c); return r | g << 5 | b << 10
def write(pic, scr, chr_, pal, banks, row0, slots):
    a = np.asarray(Image.open(os.path.join(HERE, pic)).convert('RGB')).astype(int); H, W = a.shape[:2]
    cols, inv = np.unique(a.reshape(-1, 3), axis=0, return_inverse=True); idx = inv.reshape(H, W)
    T = idx.reshape(H // 8, 8, W // 8, 8).swapaxes(1, 2)
    # palette banks: greedy packing of the tiles' colour sets
    sets = sorted({tuple(np.unique(T[y, x])) for y in range(H // 8) for x in range(W // 8)}, key=len, reverse=True)
    B = []
    for st in sets:
        st = set(st); best = None
        for k, b in enumerate(B):
            if st <= b: best = (0, k); break
            if len(b | st) <= 15 and (best is None or len(st - b) < best[0]): best = (len(st - b), k)
        if best is None: B.append(set(st))
        else: B[best[1]] |= st
    if len(B) > len(banks): raise SystemExit(f'{pic}: needs {len(B)} banks, have {len(banks)}')
    B = [sorted(b) for b in B]
    # tiles
    d, eo, e = scr_entries(scr); seen = {}; new = []
    for cy in range(H // 8):
        for cx in range(W // 8):
            t = T[cy, cx]; cs = set(np.unique(t).tolist()); k = next(j for j, b in enumerate(B) if cs <= set(b))
            loc = np.zeros_like(t)
            for n_, c in enumerate(B[k]): loc[t == c] = n_ + 1
            ent = None
            for hf in (0, 1):
                for vf in (0, 1):
                    tt = loc[:, ::-1] if hf else loc; tt = tt[::-1] if vf else tt
                    if (k, tt.tobytes()) in seen: ent = (seen[(k, tt.tobytes())], hf, vf); break
                if ent: break
            if not ent:
                if len(new) >= len(slots): raise SystemExit(f'{pic}: more than {len(slots)} tiles')
                seen[(k, loc.tobytes())] = slots[len(new)]; new.append((slots[len(new)], loc)); ent = (new[-1][0], 0, 0)
            e[row0 + cy, cx] = ent[0] | ent[1] << 10 | ent[2] << 11 | banks[k] << 12
    struct.pack_into(f'<{e.size}H', d, eo, *e.reshape(-1).tolist()); put(scr, d)
    g = bytearray(dec(chr_)); mg, v, s = sections(bytes(g)); o, sc = s[b'RAHC']; tb = o + 8 + struct.unpack_from('<I', sc, 28)[0]
    for slot, loc in new:
        f = loc.reshape(-1); g[tb + slot * 32: tb + slot * 32 + 32] = bytes((f[0::2] | (f[1::2] << 4)).astype(np.uint8))
    put(chr_, g)
    p = bytearray(dec(pal)); mg, v, s = sections(bytes(p)); o, sc = s[b'TTLP']; pb = o + 8 + struct.unpack_from('<I', sc, 20)[0]
    for k, b in enumerate(B):
        for n_ in range(15): struct.pack_into('<H', p, pb + 2 * (16 * banks[k] + 1 + n_), bgr(cols[b[n_]]) if n_ < len(b) else 0)
    put(pal, p)
    print(pic, 'tiles', len(new), 'of', len(slots), 'banks', [banks[k] for k in range(len(B))], 'colours', len(cols))
# screen 61: keep the light trail's tiles (screen 63)
_, _, e63 = scr_entries(63); keep = set((e63 & 1023).ravel().tolist())
write('night61.png', 61, 59, 39, [7, 8], 0, [t for t in range(1, 512) if t not in keep])
write('night64.png', 64, 60, 31, [0, 4, 5, 2, 6], 12, [t for t in range(1, 768) if not (2 <= t <= 30 or 444 <= t < 444 + MX)])
open(DST, 'wb').write(pack(F))
# the light trail / lens flare (screen 63, Arvind 2026-11-15: "the black and yellow thing in the sky doesn't fit now"):
# it draws with palette 39 bank 1 colours 10-14, but scene 3's Rockedeer strip owns bank 1 (deer/build_strips.py writes
# 1-15 there), which turned the flare's soft blues into black and gold. The flare moves to the free bank 9 with night colours:
# the original's five light blues re-tinted toward the aurora's mint and teal, same order of lightness.
F2 = unpack(open(DST, 'rb').read()); F = F2
d, eo, e = scr_entries(63)
on = (e & 1023) != 0; e[on] = (e[on] & 0x0FFF) | (9 << 12)
struct.pack_into(f'<{e.size}H', d, eo, *e.reshape(-1).tolist()); put(63, d)
FLARE = [(41, 98, 123), (57, 148, 148), (115, 172, 172), (98, 197, 164), (164, 230, 205)]   # colours 10-14
p = bytearray(dec(39)); mg, v, s = sections(bytes(p)); o, sc = s[b'TTLP']; pb = o + 8 + struct.unpack_from('<I', sc, 20)[0]
for k, c in enumerate(FLARE): struct.pack_into('<H', p, pb + 2 * (16 * 9 + 10 + k), bgr(c))
put(39, p)
open(DST, 'wb').write(pack(F))
print('flare: screen 63 -> palette 39 bank 9, colours 10-14 night')
