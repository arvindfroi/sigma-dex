"""Render cells 0/1 back out of a built a/1/2/0 and compare with the source pictures (5-bit colour)."""
import sys; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d/legend/oak'); sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
import numpy as np; from PIL import Image
from narc import unpack; from g2d import read_ncer, read_ncgr, read_nclr
import render_oak as R
binp, c0, c1 = sys.argv[1:4]
fs = unpack(open(binp, 'rb').read()); orig = unpack(open(R.SRC, 'rb').read())
g = read_ncgr(fs[64]); pal, _ = read_nclr(fs[63]); c = read_ncer(fs[65]); T = R.tiles(g)
ok = True
for ci, fn, box in ((0, c0, (-24, -48)), (1, c1, (-40, -72))):
    im, idx, org = R.cell_img(c['cells'][ci], T, pal)
    want = np.array(Image.open(fn).convert('RGBA'))
    full = np.zeros_like(want); oy, ox = org[1] - box[1], org[0] - box[0]; full[oy:oy + im.shape[0], ox:ox + im.shape[1]] = im
    a = full[..., 3] > 0; b = want[..., 3] > 0
    d = int(np.abs(full[a & b, :3].astype(int) - want[a & b, :3].astype(int)).max())
    print('cell', ci, 'same shape', bool((a == b).all()), 'max colour diff', d, '(5-bit rounding is up to 4)'); ok &= bool((a == b).all()) and d <= 4
ball = R.cell_img(c['cells'][2], T, pal)[0]; ball0 = R.cell_img(read_ncer(orig[65])['cells'][2], R.tiles(read_ncgr(orig[64])), read_nclr(orig[63])[0])[0]
print('ball identical', bool((ball == ball0).all())); ok &= bool((ball == ball0).all())
print('sizes', [len(x) for x in fs[59:67]] == [len(x) for x in orig[59:67]], 'members changed', [i for i in range(len(fs)) if fs[i] != orig[i]])
print('OK' if ok else 'FAIL')
