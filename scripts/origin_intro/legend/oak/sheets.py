"""Arvind's pictures: comparison sheet (both cells enlarged + in-game stand/hop) and a GIF of the real game sequence,
original above Lapper. python sheets.py BIN FILM_ORIG FILM_NEW OUT_PNG OUT_GIF"""
import sys; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d/legend/oak'); sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from narc import unpack; from g2d import read_ncer, read_ncgr, read_nclr
import render_oak as R
binp, fo, fn, out_png, out_gif = sys.argv[1:6]
WALL = (247, 214, 140, 255)
try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22); small = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
except Exception: font = small = ImageFont.load_default()
def cells(p):
    fs = unpack(open(p, 'rb').read()); g = read_ncgr(fs[64]); pal, _ = read_nclr(fs[63]); c = read_ncer(fs[65]); T = R.tiles(g)
    res = []
    for ci in (0, 1):
        im, idx, org = R.cell_img(c['cells'][ci], T, pal)
        # into a common 80x80 frame around the anchor (40, 72)
        can = Image.new('RGBA', (80, 80), WALL); can.alpha_composite(Image.fromarray(im), (40 + org[0], 72 + org[1])); res.append(can)
    return res
k = 4
mo, ml = cells(R.SRC), cells(binp)
F0, F1 = 7700, 7652                                     # stand, hop frames in the films
box = (70, 40, 200, 150); g = 2
def frame(d, f): return Image.open('%s/f%05d.png' % (d, f)).convert('RGBA').crop(box).resize(((box[2] - box[0]) * g, (box[3] - box[1]) * g), Image.NEAREST)
cw = 80 * k; gw = (box[2] - box[0]) * g; gh = (box[3] - box[1]) * g
W = 2 * cw + 2 * gw + 70; H = 2 * (max(cw, gh) + 40) + 60
sh = Image.new('RGBA', (W, H), 'white'); d = ImageDraw.Draw(sh)
d.text((10, 8), 'Oaks intro: Marill (Origin) mot Lapper   -   cellene 4x, i spillet 2x', fill='black', font=font)
for r, (name, cs, film) in enumerate((('Origin: Marill', mo, fo), ('Lapper v1', ml, fn))):
    y = 50 + r * (max(cw, gh) + 40)
    d.text((10, y), name, fill='black', font=font)
    x = 10
    for i, c in enumerate(cs):
        sh.paste(c.resize((cw, cw), Image.NEAREST), (x, y + 30)); d.text((x + 4, y + 34), ('står (celle 0)', 'hopper (celle 1)')[i], fill='black', font=small); x += cw + 10
    for i, f in enumerate((F0, F1)):
        sh.paste(frame(film, f), (x, y + 30)); d.text((x + 4, y + 34), ('i spillet: står', 'i spillet: hopp')[i], fill='black', font=small); x += gw + 10
sh.convert('RGB').save(out_png)
# GIF: real game frames, every 2nd (the game draws each picture twice), original above Lapper
gbox = (60, 30, 200, 150); s = 2
frames = []
for f in list(range(7500, 7744, 2)):
    a = Image.open('%s/f%05d.png' % (fo, f)).convert('RGB').crop(gbox); b = Image.open('%s/f%05d.png' % (fn, f)).convert('RGB').crop(gbox)
    w, h = a.size; im = Image.new('RGB', (w * s * 2 + 8, h * s), 'white')
    im.paste(a.resize((w * s, h * s), Image.NEAREST), (0, 0)); im.paste(b.resize((w * s, h * s), Image.NEAREST), (w * s + 8, 0))
    frames.append(im.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=33, loop=0, disposal=1)
print(out_png, sh.size, out_gif, len(frames), 'frames')
