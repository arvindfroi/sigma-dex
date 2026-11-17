"""Scene 5 v4: comparison sheet. python sc5/m3d/sheet.py OUT.png LABEL=FILE.png ...  (48x64 RGBA crops, x6, on the scene's sky blue)"""
import sys, numpy as np
from PIL import Image, ImageDraw
OUT = sys.argv[1]; items = [a.split('=', 1) for a in sys.argv[2:]]
S = 6; tw, th = 48 * S, 64 * S; cols = min(4, len(items)); rows = (len(items) + cols - 1) // cols
W = Image.new('RGB', (cols * (tw + 12) + 12, rows * (th + 34) + 8), (20, 20, 24)); dr = ImageDraw.Draw(W)
for k, (lab, p) in enumerate(items):
    im = Image.open(p).convert('RGBA'); bg = Image.new('RGBA', im.size, (57, 140, 215, 255)) if 'natt' not in lab.lower() else Image.open(__import__('os').path.join(__import__('os').path.dirname(__file__), 'night_bg.png')).convert('RGBA')
    bg.alpha_composite(im); x = 12 + (k % cols) * (tw + 12); y = 8 + (k // cols) * (th + 34)
    dr.text((x, y), lab, fill=(235, 235, 235)); W.paste(bg.convert('RGB').resize((tw, th), Image.NEAREST), (x, y + 22))
W.save(OUT)
