"""Sigmanian Sudowoodo painted over Origin's own Route 36 tree Sudowoodo (a/0/8/1 186 USOKKY; Arvind 2026-11-17: "the shape
is not the same; just paint over the original Sudowoodo"). Every pixel keeps its place in all 6 swaying frames; only
the colours change and a few details go on top:
  - the trunk's browns and the leaf balls' greens become Sigmanian Sudowoodo's yellows (highlight, body, shade from its DS
    front sprite), its outline the sprite's dark brown
  - green spines (light and dark green, as on the sprite) dot the balls and the trunk
  - the face of its sprite on the head (the stem between the balls): two dark eye pits and a mouth
python sudowoodo_paint.py A081_IN A081_OUT PREVIEW.png"""
import sys, os, struct
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from narc import unpack
import btx
IN, OUT, PREV = sys.argv[1:4]
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[186]
t, to, ts, po, ps = btx.parts(d)
px = np.frombuffer(d[to:to + ts], np.uint8); idx = np.empty(px.size * 2, np.uint8); idx[0::2] = px & 15; idx[1::2] = px >> 4
fr = idx.reshape(6, 32, 32).astype(int)
opal = [struct.unpack_from('<H', d, po + 2 * i)[0] for i in range(16)]
OP = np.array([[(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3] for c in opal], np.uint8)
HI, BODY, SHADE, EDGE, OUTL = (254, 250, 88), (252, 228, 67), (187, 158, 44), (78, 61, 34), (44, 40, 36)
SPINE, SPINE_D = (24, 177, 94), (27, 122, 78)
# new palette, same index meaning: 1 outline, 2 trunk edge, 3/5 highlight, 4/7 body, 6/8 shade; 9.. free for details
NEWP = {1: OUTL, 2: EDGE, 3: HI, 4: BODY, 5: HI, 6: SHADE, 7: BODY, 8: SHADE, 13: SPINE, 14: SPINE_D}
pal = [tuple(int(v) for v in OP[i]) for i in range(16)]
for k, v in NEWP.items(): pal[k] = v
BALL = (3, 4, 6); TRUNK = (5, 7, 8)
out = []
for f in fr:
    g = f.copy()
    # spines on the balls: every third light/body pixel in a checker, away from the outline
    ys, xs = np.nonzero(np.isin(f, BALL))
    for y, x in zip(ys, xs):
        if (x * 2 + y * 3) % 7 == 0 and f[y - 1, x] != 1 and f[y + 1, x] != 1: g[y, x] = 13 if (x + y) % 2 else 14
    # the face on the head (the stem between the balls, rows 13-18), following the frame's lean: eyes and a mouth dot
    xs15 = [x for x in range(9, 23) if f[15, x] in (5, 7, 8)]
    if xs15:
        cx = int(round((min(xs15) + max(xs15)) / 2))
        g[15, cx - 1] = 1; g[15, cx + 1] = 1                     # eye pits
        g[17, cx] = 2                                            # the mouth
    # a few spines on the lower trunk's sides (not on the feet)
    for y in (25, 26):
        xs_ = [x for x in range(32) if f[y, x] in (7, 8)]
        if len(xs_) >= 3: g[y, min(xs_)] = 14 if y == 25 else 13; g[y, max(xs_)] = 13 if y == 25 else 14
    out.append(g)
new = btx.encode(d, np.vstack(out).astype(np.uint8), pal); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
P = np.array(pal, np.uint8); BG = np.array([40, 44, 60], np.uint8)
a = np.hstack([np.where(f[..., None] > 0, OP[f], BG) for f in fr]); b = np.hstack([np.where(g[..., None] > 0, P[g], BG) for g in out])
sp = Image.open('/Users/arvind/Sigma pokemon pc port attempt/assets/sprites-ds/sigmanian-sudowoodo/front.png').convert('RGBA').resize((32, 32), Image.NEAREST)
z = np.vstack([a, np.full((3, a.shape[1], 3), 255, np.uint8), b])
Image.fromarray(z).resize((z.shape[1] * 6, z.shape[0] * 6), Image.NEAREST).save(PREV); print('ok', OUT)
