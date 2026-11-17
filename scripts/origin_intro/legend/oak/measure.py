"""Numbers: Oak-intro Marill (original a/1/2/0) vs Lapper (built file), per cell."""
import sys; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d/legend/oak'); sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
import numpy as np
from narc import unpack; from g2d import read_ncer, read_ncgr, read_nclr
import render_oak as R
BG = np.array([247, 214, 140])        # the intro wall behind the Pokemon (sampled from the capture)
def stats(binp):
    fs = unpack(open(binp, 'rb').read()); g = read_ncgr(fs[64]); pal, _ = read_nclr(fs[63]); c = read_ncer(fs[65]); T = R.tiles(g)
    out = []
    for ci in (0, 1):
        im, idx, org = R.cell_img(c['cells'][ci], T, pal)
        m = im[..., 3] > 0; ys, xs = np.nonzero(m)
        rgb = im[..., :3].astype(float); lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
        e = np.zeros_like(m); e[1:] |= ~m[:-1]; e[:-1] |= ~m[1:]; e[:, 1:] |= ~m[:, :-1]; e[:, :-1] |= ~m[:, 1:]
        e[0] |= True; e[-1] |= True; e[:, 0] |= True; e[:, -1] |= True; edge = m & e
        dark = lum < 40
        # single pixels with no same-colour 4-neighbour
        lone = 0
        for y, x in zip(ys, xs):
            v = idx[y, x]; nb = [idx[yy, xx] for yy, xx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)) if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1]]
            if v not in nb: lone += 1
        out.append(dict(cell=ci, x=(xs.min() + org[0], xs.max() + org[0]), y=(ys.min() + org[1], ys.max() + org[1]),
                        w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1), px=int(m.sum()),
                        colours=len(set(idx[m].tolist())), outline=round(float(dark[edge].mean()), 3),
                        luma=round(float(lum[m].mean()), 1), contrast=round(float(np.abs(rgb[m] - BG).sum(-1).mean() / 3), 1),
                        lone=round(lone / m.sum(), 3)))
    return out
if __name__ == '__main__':
    for name, p in (('Marill', R.SRC), ('Lapper', sys.argv[1])):
        for s in stats(p): print(name, s)
