"""Clean skull-and-crossbones pictures for the sails, the flag and the hat, in the exact key colours the pixel step
reads (white cloth, gold emblem, ink holes). The Hunyuan mesh only has bumpy relief there; a texture stays crisp.
python h3d/emblem.py OUTDIR"""
import sys, os, math
from PIL import Image, ImageDraw
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
WHITE, GOLD, INK, HAT = (216, 220, 232), (224, 176, 48), (12, 12, 16), (30, 30, 38)

def bone(d, a, b, w, col):
    d.line([a, b], fill=col, width=w)
    ux, uy = b[0] - a[0], b[1] - a[1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
    px, py = -uy, ux
    for (cx, cy), s in ((a, -1), (b, 1)):            # two knobs at each end
        for k in (-1, 1):
            r = w * 0.62
            ox, oy = cx + px * k * w * 0.5 + ux * s * w * 0.15, cy + py * k * w * 0.5 + uy * s * w * 0.15
            d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=col)

def skull(d, cx, cy, s, col, hole, bones=True, tilt=0):
    if bones:
        bw = int(0.2 * s)
        bone(d, (cx - 1.0 * s, cy + 0.62 * s), (cx + 1.0 * s, cy + 1.62 * s), bw, col)   # they cross under the jaw
        bone(d, (cx + 1.0 * s, cy + 0.62 * s), (cx - 1.0 * s, cy + 1.62 * s), bw, col)
    d.ellipse([cx - 0.62 * s, cy - 0.62 * s, cx + 0.62 * s, cy + 0.5 * s], fill=col)          # cranium
    d.rounded_rectangle([cx - 0.36 * s, cy + 0.2 * s, cx + 0.36 * s, cy + 0.78 * s], radius=0.12 * s, fill=col)  # jaw
    for k in (-1, 1):                                                                       # eye holes
        ex = cx + k * 0.25 * s
        d.ellipse([ex - 0.17 * s, cy - 0.06 * s, ex + 0.17 * s, cy + 0.26 * s], fill=hole)
    d.polygon([(cx, cy + 0.3 * s), (cx - 0.07 * s, cy + 0.44 * s), (cx + 0.07 * s, cy + 0.44 * s)], fill=hole)  # nose
    for k in (-1, 0, 1):                                                                    # teeth gaps
        tx = cx + k * 0.13 * s
        d.line([(tx, cy + 0.56 * s), (tx, cy + 0.78 * s)], fill=hole, width=max(2, int(0.05 * s)))

S = 512
im = Image.new('RGB', (S, S), WHITE); d = ImageDraw.Draw(im)
skull(d, S * 0.5, S * 0.27, S * 0.27, GOLD, INK)
im.save(os.path.join(OUT, 'sail.png'))
im = Image.new('RGB', (S, S), WHITE); d = ImageDraw.Draw(im)
skull(d, S * 0.5, S * 0.38, S * 0.24, GOLD, INK, bones=False)
im.save(os.path.join(OUT, 'sail2.png'))
im = Image.new('RGB', (S, S), WHITE); d = ImageDraw.Draw(im)
skull(d, S * 0.5, S * 0.42, S * 0.42, GOLD, INK, bones=False)
im.save(os.path.join(OUT, 'flag.png'))
print('ok')
# hat: gold skull and crossbones on a transparent ground (holes transparent too), projected onto the crown's front
im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
skull(d, S * 0.5, S * 0.33, S * 0.25, GOLD + (255,), (0, 0, 0, 0))
im.save(os.path.join(OUT, 'hat.png'))
