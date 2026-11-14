"""Asset-to-asset numbers for scene 3 strips (Arvind 2026-11-14: compare asset to asset, not only by eye).
python deer/measure.py   -> the originals (inv/bg047-049 bands) and ours (strips_preview.png) side by side"""
import numpy as np, colorsys, os, sys
from PIL import Image
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__))
def band(n, r0):
    a = np.asarray(Image.open(os.path.join(HERE, '..', 'inv', f'bg{n:03d}.png')).convert('RGB')).astype(int)
    return a[r0 * 8:r0 * 8 + 64]
def stats(a, name):
    v = a.max(-1); mn = a.min(-1); sat = (v - mn) / np.maximum(v, 1)
    hue = np.array([[colorsys.rgb_to_hsv(*(p / 255))[0] * 360 for p in row] for row in a])
    live = v > 24
    eye = (v > 170) & (sat > 0.45) & (hue > 30) & (hue < 65)      # bright gold
    lab, n = nd.label(eye); sizes = sorted(nd.sum(eye, lab, range(1, n + 1)).astype(int).tolist(), reverse=True) if n else []
    ec = a[eye].mean(0).astype(int).tolist() if eye.any() else None
    # inner line art: thin near-black pixels with lit pixels on both sides (left/right or up/down), per lit pixel
    lum = 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]
    blk = lum < 20; lit = lum >= 20
    p = np.pad(lit, 2)
    lr = (p[2:-2, :-4] | p[2:-2, 1:-3]) & (p[2:-2, 3:-1] | p[2:-2, 4:])
    ud = (p[:-4, 2:-2] | p[1:-3, 2:-2]) & (p[3:-1, 2:-2] | p[4:, 2:-2])
    line = blk & (lr | ud)
    L = (0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2])[live]
    print(f'{name:10s} cover {live.mean():.2f}  colours {len(np.unique(a.reshape(-1, 3), axis=0)):3d}  body luma mean {L.mean():5.1f} p90 {np.percentile(L, 90):5.1f}'
          f'  inner lines {line.sum() / max(lit.sum(), 1):.3f} ({int(line.sum())} px)'
          f'  eye px {int(eye.sum()):3d} blobs {sizes[:4]} colour {ec}  eye/body luma {((0.3*a[eye][:,0]+0.59*a[eye][:,1]+0.11*a[eye][:,2]).mean() / L.mean() if eye.any() else 0):.2f}')
for n, r0, nm in ((48, 0, 'Entei'), (47, 8, 'Suicune'), (49, 16, 'Raikou')): stats(band(n, r0), nm)
if os.path.exists(os.environ.get('PREVIEW', os.path.join(HERE, 'strips_preview.png'))):
    p = np.asarray(Image.open(os.environ.get('PREVIEW', os.path.join(HERE, 'strips_preview.png'))).convert('RGB')).astype(int)
    for k, nm in enumerate(('Rockedeer', 'Moosus', 'Felk')): stats(p[k * 64:(k + 1) * 64], nm)
