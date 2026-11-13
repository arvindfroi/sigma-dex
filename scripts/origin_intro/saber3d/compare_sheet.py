"""Arvind's drawing next to the model (same angle) and the game sprites: sabertann_v4_sammenligning.png"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json
OUT = '/Users/arvind/Sigma pokemon pc port attempt/sabertann_v4_sammenligning.png'
try: F = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 24)
except Exception: F = ImageFont.load_default()
H = 460
def fit(im, h=H): return im.resize((int(im.width * h / im.height), h))
c = fit(Image.open('/Users/arvind/Sigma pokemon pc port attempt/assets/concept-art/sabertann/624.webp').convert('RGB'))
v = fit(Image.open('prev/view_concept.png').convert('RGB'))
s = fit(Image.open('prev/view_stern.png').convert('RGB')); hd = fit(Image.open('prev/view_head.png').convert('RGB'))
P = np.array(json.load(open('px_base/pal.json'))['palette'], np.uint8)
base = np.array(Image.open('px_base/f1.png')); an = np.array(Image.open('px_anim/f1.png')); comp = np.where(an > 0, an, base)
rgb = P[comp]; rgb[comp == 0] = (28, 40, 84); spr = Image.fromarray(rgb)
spr = spr.resize((spr.width * 3, spr.height * 3), Image.NEAREST); spr = fit(spr)
rows = [('Din tegning   |   3D-modellen fra samme vinkel   |   hodet   |   gullskallen bak', [c, v, hd, s]),
        ('Slik blir han i spillet (15 nattfarger, vinkelen han seiler mot deg i)', [spr])]
W = max(sum(i.width for i in r) + 10 * (len(r) - 1) for _, r in rows) + 20
out = Image.new('RGB', (W, sum(H + 50 for _ in rows)), (24, 22, 30)); d = ImageDraw.Draw(out); y = 0
for t, r in rows:
    d.rectangle((0, y, W, y + 42), fill=(60, 50, 90)); d.text((12, y + 8), t, fill=(255, 255, 255), font=F); y += 50
    x = 10
    for im in r: out.paste(im, (x, y)); x += im.width + 10
    y += H
out.save(OUT); print(out.size)
