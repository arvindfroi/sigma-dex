"""Hop variants for Arvind: picture (hop cell enlarged + the hop in the game, per variant, Marill first) and a GIF of the
real game frames side by side. python sheets_hop.py OUT_PNG OUT_GIF NAME=CELLDIR=FILMDIR ...  (Marill: CELLDIR 'orig')"""
import sys; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d/legend/oak'); sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
from PIL import Image, ImageDraw, ImageFont
out_png, out_gif = sys.argv[1:3]; V = [a.split('=') for a in sys.argv[3:]]
try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20); small = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 15)
except Exception: font = small = ImageFont.load_default()
WALL = (247, 214, 140, 255); HOP = 7652; box = (70, 60, 190, 150); g = 2; k = 3
def cell1(d):
    c = Image.new('RGBA', (80, 80), WALL)
    c.alpha_composite(Image.open('hop2/marill_c1.png' if d == 'orig' else d + '/cell1.png').convert('RGBA'), (0, 0)); return c
def game(f, n): return Image.open('%s/f%05d.png' % (f, n)).convert('RGBA').crop(box).resize(((box[2] - box[0]) * g, (box[3] - box[1]) * g), Image.NEAREST)
cw = 80 * k; gw, gh = (box[2] - box[0]) * g, (box[3] - box[1]) * g; colw = max(cw, gw) + 10
sh = Image.new('RGBA', (len(V) * colw + 10, 40 + cw + gh + 60), 'white'); d = ImageDraw.Draw(sh)
d.text((10, 8), 'Hoppet: cellen 3x (øverst) og i spillet 2x (nederst)', fill='black', font=font)
for i, (n, cd, fd) in enumerate(V):
    x = 10 + i * colw; d.text((x, 40), n, fill='black', font=font)
    sh.paste(cell1(cd).resize((cw, cw), Image.NEAREST), (x, 66)); sh.paste(game(fd, HOP), (x, 76 + cw))
sh.convert('RGB').save(out_png)
frames = []
for f in range(7500, 7810, 2):
    im = Image.new('RGB', (len(V) * (gw + 6), gh + 26), 'white'); dr = ImageDraw.Draw(im)
    for i, (n, cd, fd) in enumerate(V):
        im.paste(game(fd, f).convert('RGB'), (i * (gw + 6), 26)); dr.text((i * (gw + 6) + 4, 3), n, fill='black', font=small)
    frames.append(im.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=33, loop=0)
print(out_png, sh.size, out_gif, len(frames))
