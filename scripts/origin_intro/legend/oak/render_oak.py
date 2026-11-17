"""Render every cell of a/1/2/0 sets 59-62 and 63-66, plus the raw tile sheet and the palettes, enlarged."""
import sys; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
from narc import unpack
from g2d import read_ncer, read_ncgr, read_nclr
import numpy as np
from PIL import Image
import os
SRC = '/Users/arvind/sigma-origin/rc8/x_rc8/files/a/1/2/0'
def rgb(c): return ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
def tiles(g):
    d = np.frombuffer(g['data'], np.uint8); px = np.stack([d & 15, d >> 4], -1).reshape(-1, 8, 8); return px
def cell_img(cell, T, pal):
    xs = [o['x'] for o in cell['oams']] + [o['x'] + o['w'] for o in cell['oams']]
    ys = [o['y'] for o in cell['oams']] + [o['y'] + o['h'] for o in cell['oams']]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    im = np.zeros((y1 - y0, x1 - x0, 4), np.uint8); idx = np.zeros((y1 - y0, x1 - x0), np.int16) - 1
    for o in reversed(cell['oams']):
        tw, th = o['w'] // 8, o['h'] // 8
        for ty in range(th):
            for tx in range(tw):
                t = T[o['tile'] + ty * tw + tx]
                for yy in range(8):
                    for xx in range(8):
                        v = t[yy, xx]
                        if v == 0: continue
                        X = o['x'] - x0 + tx * 8 + xx; Y = o['y'] - y0 + ty * 8 + yy
                        im[Y, X] = (*rgb(pal[o['pal'] * 16 + v]), 255); idx[Y, X] = o['pal'] * 16 + v
    return im, idx, (x0, y0)
if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    OUT = sys.argv[2] if len(sys.argv) > 2 else '/Users/arvind/sigma-origin/title3d/legend/oak/orig'
    os.makedirs(OUT, exist_ok=True); fs = unpack(open(src, 'rb').read())
    for (pl, cg, ce) in [(59, 60, 61), (63, 64, 65)]:
        g = read_ncgr(fs[cg]); pal, _ = read_nclr(fs[pl]); c = read_ncer(fs[ce]); T = tiles(g)
        for i, cell in enumerate(c['cells']):
            im, idx, org = cell_img(cell, T, pal)
            Image.fromarray(im).resize((im.shape[1] * 4, im.shape[0] * 4), Image.NEAREST).save(f'{OUT}/set{pl}_cell{i}.png')
            print(pl, i, im.shape, 'origin', org, 'colours used', sorted(set(idx[idx >= 0].tolist())))
        # tile sheet, 16 tiles per row, palette 0 and 1
        n = len(T); rows = (n + 15) // 16
        for p in (0, 1):
            sh = np.zeros((rows * 8, 128, 3), np.uint8) + 40
            for k in range(n):
                r, q = divmod(k, 16)
                for yy in range(8):
                    for xx in range(8):
                        v = T[k, yy, xx]
                        sh[r * 8 + yy, q * 8 + xx] = rgb(pal[p * 16 + v]) if v else (40, 40, 40)
            Image.fromarray(sh).resize((128 * 4, rows * 32), Image.NEAREST).save(f'{OUT}/set{pl}_tiles_pal{p}.png')
        P = np.array([rgb(x) for x in pal], np.uint8).reshape(16, 16, 3)
        Image.fromarray(P).resize((16 * 16, 16 * 16), Image.NEAREST).save(f'{OUT}/set{pl}_palette.png')
        print('palette rows 0-2:', [[hex(x) for x in pal[r*16:(r+1)*16]] for r in range(3)])
