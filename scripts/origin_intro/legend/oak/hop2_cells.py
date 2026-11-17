"""Hop v2 for cell 1: a puppet pose (hop_pose.py) shrunk like the stand, then the stand's face copied back pixel for pixel
(muzzle, nose, tongue, blaze: the downscale of a turned head can make two muzzle pixels read as eyes), the tongue one row
longer (mouth open), loose bits/holes cleaned, outline closed, lowest pixel on row -19 (11 px of air, as Marill).
python hop2_cells.py VARIANT OUTDIR"""
import sys, os, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lapper_small2 import down, despeckle, outline, rgba
from make_cells import stand, drop_islands, fill_holes, place, SCALE, find
from hop_pose import pose
FACE = (5, 17, 9, 19)            # rows/cols of the stand's face block (blaze tip, muzzle, nose, tongue, chest top)
HEAD = (0, 17, 5, 25)            # the head area used to find where the face goes
def shrink(hi):
    h, w = hi.shape; return outline(fill_holes(drop_islands(despeckle(down(hi, round(w * SCALE), round(h * SCALE), phase=(0.35, 0.35))))))
def to_small(x, y, w, h):
    """a point of the full-size picture (w x h) -> the shrunk grid (down() with phase 0.35)"""
    sx, sy = w / round(w * SCALE), h / round(h * SCALE); return (x - 0.35) / sx, (y - 0.35) / sy
def transplant(o, st, nose_hi, hi_shape, st_shape=(42, 64)):
    """the stand's face block, moved by where the nose went (nose_hi in the puppet, crop (16, 11) in the stand)"""
    px, py = to_small(*nose_hi, hi_shape[1], hi_shape[0]); qx, qy = to_small(16, 11, st_shape[1], st_shape[0])
    dx, dy = int(round(px - qx)), int(round(py - qy)); f0, f1, g0, g1 = FACE; o = o.copy()
    blk = st[f0:f1, g0:g1]; tgt = o[f0 + dy:f1 + dy, g0 + dx:g1 + dx]
    o[f0 + dy:f1 + dy, g0 + dx:g1 + dx] = np.where(blk > 0, blk, tgt)
    return o, (dy, dx)
def open_mouth(o, pal):
    A, G, Hh = find(pal, (0, 0, 0)), find(pal, (197, 60, 68)), find(pal, (234, 91, 84))
    red = (o == G) | (o == Hh); ys, xs = np.nonzero(red); yb = ys.max(); cols = sorted(xs[ys == yb]); o = o.copy()
    for x in cols:
        o[yb + 1, x] = o[yb, x]
        if o[yb + 2, x] != 0: o[yb + 2, x] = A
    return o
def make(v):
    st, pal, _ = stand(); hi, _, _ = pose(v)
    o = shrink(hi); o, off = transplant(o, st, pose.nose, hi.shape); o = open_mouth(o, pal); o = outline(o, find(pal, (0, 0, 0)))
    ys, xs = np.nonzero(o > 0); o = o[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # the body's middle stays where the stand has it (he hops in place): x of the tilt pivot, stand vs hop
    bx = to_small(*pose.pivot, hi.shape[1], hi.shape[0])[0] - xs.min(); sx0 = to_small(34, 22, 64, 42)[0]
    make.left = -(st.shape[1] // 2) + int(round(sx0 - bx))
    return o, pal, off
if __name__ == '__main__':
    v, od = sys.argv[1], sys.argv[2]; os.makedirs(od, exist_ok=True)
    o, pal, off = make(v)
    c1 = place(o, 80, 80, 40, 72, -19, make.left)
    Image.fromarray(rgba(o, pal)).save(od + '/hop.png'); Image.fromarray(rgba(c1, pal)).save(od + '/cell1.png')
    import shutil; shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v1/cell0.png'), od + '/cell0.png')
    print(v, 'hop', o.shape, 'face moved', off)
