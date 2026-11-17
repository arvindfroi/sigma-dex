"""Lapper's two intro cells for a/1/2/0, in Marill's footprint.
cell 0 (stand, 48x48 box, anchor at (24,48)): the approved front sprite (64x42) shrunk to 47 px (index-space downscale,
  lapper_small2), feet on row -8 like Marill's, centred.
cell 1 (hop, 80x80 box, anchor at (40,72)): like Marill's hop (the same figure lifted 11 px, tilted, mouth open), made
  on the finished stand in whole pixels so the face stays pixel for pixel (hop_small); feet on row -19.
  Tried and dropped (2026-11-17): Qwen-Image-Edit hop poses (qwen_hop.py: a flying leap with the ears flipped up, no
  longer the approved Lapper), and the same edits on the 64-px front before shrinking (the downscale resampled the face
  so two muzzle pixels read as eyes).
python make_cells.py OUTDIR"""
import sys, os, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lapper_small2 import load_front, to_index, down, despeckle, outline, rgba
W0 = 47
SCALE = W0 / 64
def find(pal, rgb): return pal.index(rgb, 1)          # index 0 is see-through (also listed as black)
def shrink(idx, scale=SCALE):
    h, w = idx.shape; W, H = round(w * scale), round(h * scale)
    return outline(despeckle(down(idx, W, H, phase=(0.35, 0.35))))
def stand():
    fb = load_front(); idx, pal = to_index(fb); return shrink(idx), pal, idx
def drop_islands(o, keep=12):
    """Remove loose bits (connected groups of fewer than `keep` pixels) left by the shifts."""
    from scipy import ndimage
    lbl, n = ndimage.label(o > 0, structure=np.ones((3, 3)))
    sizes = ndimage.sum(o > 0, lbl, range(1, n + 1)); o = o.copy()
    for i, sz in enumerate(sizes):
        if sz < keep: o[lbl == i + 1] = 0
    return o
def hop_small(o, pal):
    """The hop made on the finished 47-px stand in whole pixels, so the face and fur stay pixel for pixel:
    the front ear's lower part swung out 1-2 px, the front half (head, ear, chest, front paws) one pixel higher than the
    back (nose-up tilt), the legs one row longer (dangling), the tongue one row longer (mouth open)."""
    A, C, G, Hh = find(pal, (0, 0, 0)), find(pal, (51, 25, 14)), find(pal, (197, 60, 68)), find(pal, (234, 91, 84))
    h, w = o.shape; pad = 3
    e = np.zeros((h + 4, w + pad), o.dtype); e[2:2 + h, pad:] = o; Y0, X0 = 2, pad
    # tongue: one row longer, as wide as its bottom row
    red = (e == G) | (e == Hh); ys, xs = np.nonzero(red); yb = ys.max(); cols = sorted(xs[ys == yb])
    for x in cols:
        e[yb + 1, x] = e[yb, x]
        if e[yb + 2, x] != 0: e[yb + 2, x] = A
    # front ear: rows from 14 down, columns left of the face, shifted left (1 px from row 14, 2 px from row 19)
    for y in range(Y0 + 14, Y0 + h):
        s = 1 if y < Y0 + 19 else 2
        row = e[y].copy(); n = 11
        seg = row[X0:X0 + n].copy()
        if not (seg > 0).any(): continue
        new = row.copy(); new[X0:X0 + n] = 0
        new[X0 - s:X0 - s + n] = np.where(seg > 0, seg, new[X0 - s:X0 - s + n])
        for x in range(X0 + n - s, X0 + n):
            if new[x] == 0 and row[x] > 0: new[x] = C
        e[y] = new
    # legs one row longer: repeat the top leg row (row 25 of the stand)
    r = Y0 + 25; e = np.vstack([e[:r + 1], e[r:r + 1], e[r + 1:-1]])
    # front half one pixel up: head/ear/chest columns (x < 26) above the legs, front paws (x < 21) in the leg rows
    yy, xx = np.mgrid[:e.shape[0], :e.shape[1]]
    front = (e > 0) & (((yy < Y0 + 20) & (xx < X0 + 26)) | ((yy >= Y0 + 20) & (xx < X0 + 21)))
    moved = np.zeros_like(e); moved[:-1][front[1:]] = e[1:][front[1:]]
    e = np.where(front, 0, e); e = np.where(moved > 0, moved, e)
    e = outline(fill_holes(drop_islands(e)), A)
    ys, xs = np.nonzero(e > 0)
    return e[ys.min():ys.max() + 1, xs.min():xs.max() + 1], xs.min() - X0
def fill_holes(o):
    """See-through pixels closed in by the sprite (left by the shifts) take the colour below them (else above)."""
    from scipy import ndimage
    m = o > 0; holes = ndimage.binary_fill_holes(m) & ~m; o = o.copy()
    for _ in range(4):
        for y, x in zip(*np.nonzero(holes)):
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = o[y + dy, x + dx]
                if v > 0 and v != 1: o[y, x] = v; break
        holes = holes & (o == 0)
    return o
def place(o, box_w, box_h, ax, ay, foot, left):
    can = np.zeros((box_h, box_w), o.dtype); h, w = o.shape
    y0 = ay + foot - h + 1; x0 = ax + left
    assert y0 >= 0 and x0 >= 0 and x0 + w <= box_w and y0 + h <= box_h, (x0, y0, w, h)
    can[y0:y0 + h, x0:x0 + w] = o; return can
def build(out):
    os.makedirs(out, exist_ok=True)
    s, pal, idx = stand(); h, w = s.shape
    c0 = place(s, 48, 48, 24, 48, -8, -(w // 2))            # x -23..23, feet on -8
    hp, dx = hop_small(s, pal)
    c1 = place(hp, 80, 80, 40, 72, -19, -(w // 2) + dx)
    Image.fromarray(rgba(c0, pal)).save(out + '/cell0.png'); Image.fromarray(rgba(c1, pal)).save(out + '/cell1.png')
    Image.fromarray(rgba(s, pal)).save(out + '/stand.png'); Image.fromarray(rgba(hp, pal)).save(out + '/hop.png')
    print('stand', s.shape, 'hop', hp.shape, 'colours', len(set(np.unique(c0)) | set(np.unique(c1))) - 1)
if __name__ == '__main__':
    build(sys.argv[1])
