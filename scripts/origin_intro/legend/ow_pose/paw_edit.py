"""Sabertann's roar puppet: only the raised paw is redrawn by Qwen-Image-Edit (scripts/ds_pixel.edit with an area: outside the
area the puppet stays pixel for pixel, so roar v2's face, mouth and sails are kept; Qwen's full redraws made his whole head
one mouth). The result goes back to the approved palette (nearest colour in Lab).
python paw_edit.py ROAR_idx.npy PAL.npy OUTDIR SEED...   (env AREA 'x0,y0,x1,y1' in sprite pixels)"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import ds_pixel
RF, PF, OD = sys.argv[1:4]; SEEDS = [int(s) for s in sys.argv[4:]] or [31, 32, 33]; os.makedirs(OD, exist_ok=True)
idx = np.load(RF).astype(int); PAL = np.load(PF).astype(float)
P = np.vstack([[0, 0, 0], PAL]).round().astype(np.uint8)
rgba = np.zeros((64, 64, 4), np.uint8); rgba[..., :3] = P[idx]; rgba[..., 3] = np.where(idx > 0, 255, 0)
x0, y0, x1, y1 = (int(v) for v in os.environ.get('AREA', '8,37,28,56').split(','))
area = dict(x0=x0 / 64, y0=y0 / 64, x1=x1 / 64, y1=y1 / 64)
CHANGE = ("make the front paw on the left of the picture one clean raised paw: the black furred front leg lifted up beside "
          "his open-mouthed face, the big paw turned toward the viewer with a gold band at the wrist and four gold-tipped claws "
          "spread out, drawn in the same pixel style and colors as the rest of the sprite")
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
PL = lab(PAL)
for s in SEEDS:
    sp = ds_pixel.edit(Image.fromarray(rgba), CHANGE, Path(OD) / ('work_%d' % s), area=area, seeds=(s,))
    a = np.asarray(sp.convert('RGBA')).astype(float); m = a[..., 3] > 0
    out = np.zeros((64, 64), int); out[m] = ((lab(a[..., :3])[m][:, None] - PL[None]) ** 2).sum(-1).argmin(1) + 1
    np.save(os.path.join(OD, 'paw_%d_idx.npy' % s), out.astype(np.uint8))
    BG = np.array([40, 44, 60]); Image.fromarray(np.where(out[..., None] > 0, P[out], BG).astype(np.uint8)).resize((512, 512), Image.NEAREST).save(os.path.join(OD, 'paw_%d_8x.png' % s))
    print('paw', s, flush=True)
