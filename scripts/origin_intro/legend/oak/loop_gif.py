"""Stand/hop loop in the Oak scene as the game plays it (sequence 2: hop cell 12 frames, stand 60; the 30 fps game shows
each picture twice, so 6 + 30 GIF frames of 33 ms), Marill's real frames first, then each variant.
python loop_gif.py OUT.gif OUT.png NAME=CELLDIR ...  (each CELLDIR has cell0.png and cell1.png)"""
import sys
from PIL import Image, ImageDraw, ImageFont
E = '/Users/arvind/sigma-origin/title3d/legend/oak/emu/'
AX, AY = 116, 150; box = (70, 60, 190, 150); k = 2
try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
except Exception: font = ImageFont.load_default()
out_gif, out_png = sys.argv[1:3]; vars_ = [a.split('=', 1) for a in sys.argv[3:]]
def ours(d, cell):
    sc = Image.open(E + 'scene_empty.png').convert('RGBA').crop((0, 0, 256, 192))
    c = Image.open('%s/cell%d.png' % (d, cell)).convert('RGBA'); off = (24, 48) if cell == 0 else (40, 72)
    sc.alpha_composite(c, (AX - off[0], AY - off[1])); return sc
panels = [('Origin: Marill', Image.open(E + 'scene_1000.png').convert('RGBA').crop((0, 0, 256, 192)), Image.open(E + 'scene_980.png').convert('RGBA').crop((0, 0, 256, 192)))]
panels += [(n, ours(d, 0), ours(d, 1)) for n, d in vars_]
W = (box[2] - box[0]) * k; H = (box[3] - box[1]) * k
def frame(which):
    im = Image.new('RGB', (len(panels) * (W + 8), H + 26), 'white'); dr = ImageDraw.Draw(im)
    for i, (n, s, h) in enumerate(panels):
        im.paste((h if which else s).crop(box).resize((W, H), Image.NEAREST), (i * (W + 8), 26)); dr.text((i * (W + 8) + 4, 3), n, fill='black', font=font)
    return im
st, hp = frame(0), frame(1)
frames = [hp.quantize(colors=128), st.quantize(colors=128)]
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=[200, 1000], loop=0)
sheet = Image.new('RGB', (st.width, st.height * 2 + 6), 'white'); sheet.paste(st, (0, 0)); sheet.paste(hp, (0, st.height + 6)); sheet.save(out_png)
print(out_gif, out_png)
