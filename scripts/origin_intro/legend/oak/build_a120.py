"""Write Lapper into a/1/2/0 in place of Oak's intro Marill: new tiles in the same slots of member 64 (cell 0 = tiles 0-35,
cell 1 = tiles 36-135; the Poke Ball tiles 136-139 untouched), palette row 0 of member 63 (row 1 = the ball, untouched).
Cells (65) and animation (66) are unchanged. Every member keeps its size; the NARC is rewritten in place.
python build_a120.py CELL0.png CELL1.png OUT.bin
CELL0.png is 48x48 (cell 0's box: x -24..23, y -48..-1 around the anchor), CELL1.png 80x80 (x -40..39, y -72..7).
Both RGBA, at most 15 colours together (alpha 0 = see-through)."""
import sys, struct, hashlib
sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
import numpy as np
from PIL import Image
from narc import unpack
from g2d import read_ncer, sections
SRC = '/Users/arvind/sigma-origin/rc8/x_rc8/files/a/1/2/0'
BOX = {0: (-24, -48, 48, 48), 1: (-40, -72, 80, 80)}

def to5(c): return tuple(int(round(int(v) * 31 / 255)) for v in c)
def from5(c): return tuple(v * 255 // 31 for v in c)

def build(cell_imgs, src=SRC):
    raw = open(src, 'rb').read(); fs = unpack(raw)
    ncer = read_ncer(fs[65])
    # one palette from both pictures (in 5-bit colour)
    cols = {}
    for im in cell_imgs.values():
        a = np.array(im.convert('RGBA'))
        for p in a[a[..., 3] > 0]: c5 = to5(p[:3]); cols[c5] = cols.get(c5, 0) + 1
    assert len(cols) <= 15, ('too many colours', len(cols))
    order = sorted(cols, key=lambda c: (sum(c), c))         # dark to light
    lut = {c: i + 1 for i, c in enumerate(order)}
    # tiles
    g = bytearray(fs[64]); mg, ver, secs = sections(bytes(g)); so, s = secs[b'RAHC']
    h, w, bd, mp, mt, sz, off = struct.unpack_from('<HHIIIII', s, 8)
    data_at = so + 8 + off
    tiles = np.frombuffer(bytes(g[data_at:data_at + sz]), np.uint8).copy()
    px = np.stack([tiles & 15, tiles >> 4], -1).reshape(-1, 8, 8)
    written = set()
    for ci, im in cell_imgs.items():
        x0, y0, W, H = BOX[ci]; a = np.array(im.convert('RGBA')); assert a.shape[:2] == (H, W), (ci, a.shape)
        idx = np.zeros((H, W), np.uint8)
        for y, x in zip(*np.nonzero(a[..., 3] > 0)): idx[y, x] = lut[to5(a[y, x, :3])]
        for o in ncer['cells'][ci]['oams']:
            tw, th = o['w'] // 8, o['h'] // 8
            for ty in range(th):
                for tx in range(tw):
                    t = o['tile'] + ty * tw + tx; assert t not in written and t < 136, t; written.add(t)
                    X = o['x'] - x0 + tx * 8; Y = o['y'] - y0 + ty * 8
                    px[t] = idx[Y:Y + 8, X:X + 8]
    assert written == set(range(136)), sorted(set(range(136)) - written)
    newt = (px.reshape(-1, 2)[:, 0] | (px.reshape(-1, 2)[:, 1] << 4)).astype(np.uint8).tobytes()
    assert newt[136 * 32:] == bytes(tiles[136 * 32:]), 'ball tiles changed'
    g[data_at:data_at + sz] = newt
    # palette row 0
    p = bytearray(fs[63]); mg, ver, secs = sections(bytes(p)); so, s = secs[b'TTLP']
    bd2, _, psz, poff = struct.unpack_from('<IIII', s, 8); pat = so + 8 + poff
    for c, i in lut.items():
        struct.pack_into('<H', p, pat + 2 * i, c[0] | c[1] << 5 | c[2] << 10)
    for i in range(len(lut) + 1, 16): struct.pack_into('<H', p, pat + 2 * i, 0)
    # in place
    out = bytearray(raw)
    off = 16; bsz, = struct.unpack_from('<I', raw, off + 4); n, = struct.unpack_from('<H', raw, off + 8)
    ents = [struct.unpack_from('<II', raw, off + 12 + 8 * i) for i in range(n)]
    off += bsz; bsz, = struct.unpack_from('<I', raw, off + 4); off += bsz; base = off + 8
    for i, new in ((63, bytes(p)), (64, bytes(g))):
        a0, b0 = ents[i]; assert len(new) == b0 - a0 == len(fs[i]), (i, len(new), b0 - a0)
        out[base + a0:base + b0] = new
    out = bytes(out); assert len(out) == len(raw)
    fs2 = unpack(out)
    changed = [i for i in range(len(fs)) if fs2[i] != fs[i]]
    assert set(changed) <= {63, 64}, changed
    return out, changed, [from5(c) for c in order]

if __name__ == '__main__':
    c0, c1, outp = sys.argv[1:4]
    out, changed, pal = build({0: Image.open(c0), 1: Image.open(c1)})
    open(outp, 'wb').write(out)
    print('wrote', outp, len(out), 'bytes; changed members', changed, '; palette', len(pal), 'colours')
    print('sha256', hashlib.sha256(out).hexdigest())
