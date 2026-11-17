"""Enlarge a small sprite with a pixel grid and coordinates (for hand fixes)."""
import sys, numpy as np
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 14
s = Image.open(src).convert('RGBA'); w, h = s.size
bg = Image.new('RGBA', s.size, (247, 214, 140, 255)); bg.alpha_composite(s)
im = bg.resize((w * k, h * k), Image.NEAREST); im2 = Image.new('RGBA', (w * k + 24, h * k + 24), 'white'); im2.paste(im, (24, 24))
d = ImageDraw.Draw(im2)
for x in range(w + 1): d.line([(24 + x * k, 24), (24 + x * k, 24 + h * k)], fill=(120, 120, 120, 255) if x % 5 else (0, 0, 255, 255))
for y in range(h + 1): d.line([(24, 24 + y * k), (24 + w * k, 24 + y * k)], fill=(120, 120, 120, 255) if y % 5 else (0, 0, 255, 255))
for x in range(0, w, 5): d.text((24 + x * k + 2, 4), str(x), fill='black')
for y in range(0, h, 5): d.text((2, 24 + y * k + 2), str(y), fill='black')
im2.save(out)
