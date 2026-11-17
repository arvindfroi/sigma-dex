"""Original vs ours in the Oak scene, both cells: frames 1000 (stand) and 980 (hop) of the capture vs cell0/cell1 pasted
at Marill's anchor (116,150). python scene_cells.py CELLDIR OUT [K]"""
import sys
from PIL import Image, ImageDraw
E = '/Users/arvind/sigma-origin/title3d/legend/oak/emu/'
AX, AY = 116, 150
d = sys.argv[1]; out = sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 3
def ours(cell):
    sc = Image.open(E + 'scene_empty.png').convert('RGBA').crop((0, 0, 256, 192))
    c = Image.open('%s/cell%d.png' % (d, cell)).convert('RGBA')
    off = (24, 48) if cell == 0 else (40, 72)
    sc.alpha_composite(c, (AX - off[0], AY - off[1])); return sc
box = (70, 40, 200, 150)
tiles = [('Origin stand', Image.open(E + 'scene_1000.png').convert('RGBA').crop((0, 0, 256, 192))), ('Lapper stand', ours(0)),
         ('Origin hop', Image.open(E + 'scene_980.png').convert('RGBA').crop((0, 0, 256, 192))), ('Lapper hop', ours(1))]
W = (box[2] - box[0]) * k; H = (box[3] - box[1]) * k
sh = Image.new('RGBA', (W * 2 + 10, H * 2 + 40), 'white'); dr = ImageDraw.Draw(sh)
for i, (name, im) in enumerate(tiles):
    x, y = (i % 2) * (W + 10), (i // 2) * (H + 20)
    sh.paste(im.crop(box).resize((W, H), Image.NEAREST), (x, y)); dr.text((x + 4, y + H + 3), name, fill='black')
sh.save(out)
