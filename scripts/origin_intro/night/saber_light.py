"""Sabertann v16 lighting (Arvind 2026-11-14: "how Sabertann and Gravriel are lit does not match the scene; look at
how the others do it"). Ho-Oh and Lugia fly in front of their sun/moon: they are backlit, a little darker than the sky
behind them, in the scene's own hue, and only the edges facing up catch the light.
- the palette (shared by all three detail levels) is pulled toward the night blue and darkened; the sail, gold and
  sabres lose most of their brightness; the eyes keep their glow
- a moonlit rim: top edges of the figure (pixel above is empty, runs of 2+) turn into the pale moon colour (index 14,
  the eye glow, which is the moon's own cream)
python night/saber_light.py SRCDIR DSTDIR   (SRCDIR holds v5px, v5px14, v5px7 as from variants/v15)"""
import sys, os, json, shutil
import numpy as np
from PIL import Image
from scipy import ndimage as nd
SRC, DST = sys.argv[1], sys.argv[2]
NEW = {   # index: new colour (old in the comment)
    3: (36, 48, 78),     # (42, 56, 88)
    4: (58, 74, 108),    # (70, 88, 122)
    5: (56, 28, 52),     # (66, 30, 54)   hull reds
    6: (82, 38, 60),     # (98, 40, 62)
    7: (110, 54, 72),    # (132, 62, 78)
    8: (90, 80, 64),     # (112, 96, 64)  gold
    9: (128, 114, 86),   # (160, 138, 88)
    10: (164, 148, 106), # (204, 182, 114)
    11: (82, 100, 132),  # (98, 120, 150) sail and sabres
    12: (116, 134, 162), # (144, 164, 186)
    13: (150, 166, 192), # (190, 204, 218)
    15: (62, 52, 60),    # (78, 64, 64)
}
RIM = 14
for lod in ('v5px', 'v5px14', 'v5px7'):
    s, d = os.path.join(SRC, lod), os.path.join(DST, lod)
    if os.path.abspath(s) != os.path.abspath(d):
        shutil.rmtree(d, ignore_errors=True); shutil.copytree(s, d)
    pj = json.load(open(os.path.join(d, 'pal.json')))
    for i, c in NEW.items(): pj['palette'][i] = list(c)
    json.dump(pj, open(os.path.join(d, 'pal.json'), 'w'))
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith('f') and fn.endswith('.png')): continue
        im = Image.open(os.path.join(d, fn)); pal = im.getpalette()
        a = np.array(im)
        solid = a > 0
        up = np.zeros_like(solid); up[1:] = solid[:-1]
        top = solid & ~up
        run = nd.uniform_filter1d(top.astype(float), 3, axis=1) > 0.6
        light = np.isin(a, [11, 12, 13, 14, 10])        # already pale: leave it
        if os.environ.get('SAB_RIM', '0') == '1': a[top & run & ~light] = RIM   # v18: off, Ho-Oh/Lugia have no rim
        out = Image.fromarray(a.astype(np.uint8), 'P')
        p = sum((list(c) for c in pj['palette']), []); out.putpalette(p + [0] * (768 - len(p)))
        out.save(os.path.join(d, fn))
print('ok', DST)
