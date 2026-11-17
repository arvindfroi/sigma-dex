"""Arvind's own compositions for the two fossil puzzles (2026-11-17, sketched in the chat), traced here as smooth shapes on
his sketch's own canvas (about 650 x 600, his coordinates read off the sketch), so the puzzle keeps his layout:
  tortoplasm: a big rounded-square rock shell filling the frame, four pointed jelly flippers at its corners, the turtle's
    head in profile (facing left) coming out over the middle of the shell's lower edge, its neck running down past it
  ambuger: the big round amber body on the right, its head on the left with one big eye, the long proboscis rolled into
    a spiral at the lower left, a long wing and a short wing at the upper left, a big wing rising to the upper right, the
    legs folded across the body and a few thin legs sticking out to the right
Writes the line tracing (to check against the sketch) and the stencil: the shapes white, the field black, every shape's
outline and the inner lines cut black, for alph_puzzle.py STENCIL=1.
python fossil_sketch.py tortoplasm|ambuger OUT_PREFIX"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw
WHICH, OUT = sys.argv[1:3]
def cr(points, closed=True, n=16):
    """Catmull-Rom spline through the points."""
    p = list(points); out = []
    if closed: p = [p[-1]] + p + [p[0], p[1]]
    else: p = [p[0]] + p + [p[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
                                    (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    if not closed: out.append(tuple(p[-2]))
    return out
def ell(cx, cy, rx, ry, ang=0, n=64):
    a = math.radians(ang)
    return [(cx + rx * math.cos(t) * math.cos(a) - ry * math.sin(t) * math.sin(a),
             cy + rx * math.cos(t) * math.sin(a) + ry * math.sin(t) * math.cos(a)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]
def spiral(cx, cy, r0, r1, turns, a0=0, n=200):
    return [(cx + (r0 + (r1 - r0) * t) * math.cos(a0 + 2 * math.pi * turns * t), cy + (r0 + (r1 - r0) * t) * math.sin(a0 + 2 * math.pi * turns * t))
            for t in np.linspace(0, 1, n)]
W, H = 660, 600
if WHICH == 'tortoplasm':
    shapes = [  # drawn back to front: each shape's outline is cut, so the front one's edge separates it
        cr([(105, 110), (310, 66), (515, 72), (524, 260), (530, 445), (340, 488), (148, 494), (118, 300)]),         # the shell
        cr([(66, 88), (50, 140), (46, 200), (72, 232), (106, 226), (114, 170), (98, 122)]),                       # flippers, over its corners
        cr([(532, 28), (556, 72), (566, 130), (548, 172), (506, 178), (510, 110)]),
        cr([(92, 318), (72, 380), (62, 465), (88, 510), (132, 515), (170, 478), (184, 425), (150, 405), (118, 380)]),
        cr([(571, 318), (582, 380), (580, 432), (532, 446), (490, 432), (470, 390), (536, 378)]),
        cr([(300, 248), (355, 272), (385, 350), (400, 440), (395, 520), (355, 560), (300, 556), (268, 515), (265, 470),
            (270, 400), (235, 385), (210, 348), (214, 300), (250, 262)]),                                         # the head and neck
    ]
    lines = [cr([(280, 290), (300, 293), (326, 282)], False), cr([(212, 346), (268, 346), (286, 330)], False),
             cr([(240, 392), (300, 394)], False), cr([(296, 396), (296, 470)], False)]
    dots = []; legs = []
else:
    prob = spiral(120, 352, 18, 98, 1.75, a0=math.pi * 0.1)
    shapes = [
        ell(522, 128, 145, 52, -56),                                                                              # the big wing behind
        ell(222, 118, 78, 24, 45),                                                                                # the short wing
        ell(122, 186, 92, 27, 3),                                                                                 # the long wing
        ell(430, 272, 125, 140),                                                                                  # the body
        cr([(205, 300), (245, 288), (318, 292), (334, 322), (322, 366), (300, 396), (226, 402), (204, 362)]),      # the head
    ]
    lines = [cr([(390, 290), (412, 350), (446, 406)], False), cr([(426, 258), (482, 330), (540, 412)], False)]     # folded legs
    legs = [[(548, 245), (616, 240)], [(545, 285), (606, 285)], [(528, 320), (560, 327)], [(306, 434), (442, 434)]]  # thin legs out
    dots = [(285, 345, 15)]                                                                                       # the eye
SW = int(__import__('os').environ.get('SW', 12))                                                                                                          # line width on this canvas (2 px at 128)
from scipy import ndimage
def mask_poly(pts):
    im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).polygon(pts, fill=255); return np.asarray(im) > 0
def mask_line(pts, w):
    im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).line(pts, fill=255, width=2); m = np.asarray(im) > 0
    r = w // 2; yy, xx = np.mgrid[-r:r + 1, -r:r + 1]; return ndimage.binary_dilation(m, structure=(xx ** 2 + yy ** 2) <= r * r)
disk = lambda r: (lambda yy, xx: (xx ** 2 + yy ** 2) <= r * r)(*np.mgrid[-r:r + 1, -r:r + 1])
trace = Image.new('L', (W, H), 255); dt = ImageDraw.Draw(trace)
canvas = np.zeros((H, W), bool)
for sh in shapes:
    m = mask_poly(sh); canvas[m] = True
    canvas[m & ~ndimage.binary_erosion(m, structure=disk(SW // 2))] = False                      # its outline cut
    dt.line(sh + [sh[0]], fill=0, width=6, joint='curve')
if WHICH == 'ambuger':                                                                                            # the proboscis: a light tube rolled up
    tube = prob + [(205, 330)]
    canvas[mask_line(tube, SW + 34)] = False; canvas[mask_line(tube, 30)] = True
    dt.line(tube, fill=0, width=6, joint='curve')
for ln in lines:
    canvas[mask_line(ln, SW)] = False; dt.line(ln, fill=0, width=6, joint='curve')
for ln in legs:
    canvas[mask_line(ln, 14)] = True; dt.line(ln, fill=0, width=6)
for x, y, r in dots:
    yy, xx = np.mgrid[0:H, 0:W]; canvas[(xx - x) ** 2 + (yy - y) ** 2 <= r * r] = False; dt.ellipse((x - r, y - r, x + r, y + r), fill=0)
sten = Image.fromarray((canvas * 255).astype(np.uint8))
trace.save(OUT + '_trace.png'); sten.save(OUT + '_stencil.png'); print('ok', OUT)
