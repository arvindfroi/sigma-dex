import sys, glob
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]; step = int(sys.argv[3]) if len(sys.argv) > 3 else 1; sc = int(sys.argv[4]) if len(sys.argv) > 4 else 4
fs = sorted(glob.glob(d + '/*.png'))[::step]; cols = 16; w, h = 256 // sc, 384 // sc
rows = (len(fs) + cols - 1) // cols; sh = Image.new('RGB', (cols * w, rows * (h + 10)), 'white'); dr = ImageDraw.Draw(sh)
for i, f in enumerate(fs):
    x, y = i % cols * w, i // cols * (h + 10); sh.paste(Image.open(f).resize((w, h)), (x, y)); dr.text((x + 2, y + h), f[-9:-4], fill='black')
sh.save(out)
