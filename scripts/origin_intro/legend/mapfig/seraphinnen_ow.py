"""Shiny Seraphinnen in the red Gyarados's place at the Lake of Rage (a/0/8/1 183 rgyaradosu; Arvind 2026-11-17: "the red
Gyarados becomes a shiny Seraphinnen"). The member holds 8 frames of 32x32 with Lapras's layout (0 up A, 5 up B, 6 down A,
7 down B, 2 left A, 1 left B, 3 right A, 4 right B). Seraphinnen has no DS sprites yet, so its map figure is drawn here
after its pixel concept art (assets/concept-art/seraphinnen/977.png, by BUST):
  - a golden halo seen from above at an angle, its ring of eyes on the front arc, the small cross floating in its middle
    (behind the ring from the back, so not drawn when it faces up)
  - four white wings, each three long feathers fanning out from the halo, a big pair up and out, a smaller pair down
    and out; the wings beat: on the second step the feathers swing toward the halo (the upper pair down, the lower up)
  - it hovers over the lake: a ring of ripples on the water below it, spreading on the second step, and it bobs a pixel
SHINY picks the colours: normal (the concept's gold and white) or one of the shiny proposals; the battle sprites' shiny
palette must later match the one Arvind picks.
python seraphinnen_ow.py A081_IN A081_OUT PREVIEW.png     env SHINY (normal|silver|dark|rose)"""
import sys, os, math
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from scipy import ndimage
from narc import unpack
import btx
IN, OUT, PREV = sys.argv[1:4]
PALS = {   # OUTL, WING_S (feather lines), WING_D (root shade), WING, HALO_D, HALO, HALO_L, EYE, CROSS, CROSS_D, RIP, RIP_D
    'normal': [(48, 40, 56), (176, 172, 192), (136, 128, 152), (248, 248, 248), (144, 88, 16), (232, 168, 32), (252, 228, 112),
               (32, 24, 40), (240, 240, 248), (152, 152, 168), (232, 244, 252), (152, 200, 240)],
    'silver': [(40, 40, 64), (160, 176, 216), (112, 128, 176), (240, 244, 255), (96, 104, 128), (176, 184, 208), (240, 244, 252),
               (24, 96, 216), (208, 236, 255), (96, 144, 200), (232, 244, 252), (152, 200, 240)],
    'dark':   [(16, 8, 16), (40, 32, 52), (24, 16, 32), (104, 96, 124), (96, 8, 16), (192, 24, 40), (248, 104, 88),
               (248, 232, 96), (88, 80, 104), (24, 16, 32), (232, 244, 252), (152, 200, 240)],
    'rose':   [(64, 24, 40), (216, 160, 188), (176, 112, 144), (255, 236, 244), (136, 40, 48), (224, 104, 96), (252, 184, 160),
               (40, 16, 32), (255, 228, 238), (176, 120, 152), (232, 244, 252), (152, 200, 240)],
}
NAMES = ['OUTL', 'WING_S', 'WING_D', 'WING', 'HALO_D', 'HALO', 'HALO_L', 'EYE', 'CROSS', 'CROSS_D', 'RIP', 'RIP_D']
I = {n: k + 1 for k, n in enumerate(NAMES)}
HX, HY, HRX, HRY = 15.5, 13.0, 7.6, 3.2
SS = 4                                                           # supersampling for the feathers' shapes
def feathers(flap, bob):
    """Label image of the wing feathers (0 empty, k feather id), drawn back to front."""
    lab = np.zeros((32 * SS, 32 * SS), int); k = 0
    yy, xx = (np.mgrid[0:32 * SS, 0:32 * SS] + 0.5) / SS
    for side in (-1, 1):
        for pair, root_dy, angs, lens, wid in (('up', -1.0, (160, 136, 110), (9.0, 10.5, 9.5), 2.1),
                                                ('down', 1.6, (200, 222, 246), (7.0, 7.5, 6.5), 1.8)):
            sw = -14 if pair == 'up' else 14                          # the beat: up wings swing down, lower wings up
            rx_, ry_ = HX + side * (HRX - 1.5), HY + root_dy - bob
            for a, L in zip(angs, lens):
                a = math.radians(a + (sw if flap else 0))
                dx, dy = math.cos(a) * side * -1, -math.sin(a)          # angles measured for the left wing, mirrored
                cx, cy = rx_ + dx * L / 2, ry_ + dy * L / 2
                u = (xx - cx) * dx + (yy - cy) * dy; v = -(xx - cx) * dy + (yy - cy) * dx
                inside = (u / (L / 2)) ** 2 + (v / wid) ** 2 <= 1
                k += 1; lab[inside] = k
    # down to 32 px: each pixel takes the feather that covers most of it, if the feathers cover half of it
    blk = lab.reshape(32, SS, 32, SS).transpose(0, 2, 1, 3).reshape(32, 32, SS * SS)
    out = np.zeros((32, 32), int)
    for y in range(32):
        for x in range(32):
            v = blk[y, x]; v = v[v > 0]
            if len(v) >= SS * SS // 2: out[y, x] = np.bincount(v).argmax()
    return out
def frame(step, facing):
    bob = 1 if step else 0
    lab = feathers(step, bob)
    f = np.zeros((32, 32), int); m = lab > 0
    f[m] = I['WING']
    # the line between two feathers: a feather's pixel next to a different feather drawn in front of it
    for y in range(32):
        for x in range(32):
            if lab[y, x] and any(0 <= y + dy < 32 and 0 <= x + dx < 32 and lab[y + dy, x + dx] > lab[y, x]
                                 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                f[y, x] = I['WING_S']
    yy, xx = np.mgrid[0:32, 0:32]
    root = m & (np.abs(xx - HX) < HRX + 2.5) & (np.abs(yy - (HY - bob)) < 3)
    f[root] = I['WING_D']                                         # the shade where the wings meet the halo
    f[ndimage.binary_dilation(m) & ~m] = I['OUTL']
    # the halo
    cy = HY - bob
    eo = ((xx - HX) / HRX) ** 2 + ((yy - cy) / HRY) ** 2; ei = ((xx - HX) / (HRX - 2.2)) ** 2 + ((yy - cy) / (HRY - 1.5)) ** 2
    ring = (eo <= 1.0) & (ei > 1.0)
    f[ring & (yy < cy)] = I['HALO_L']; f[ring & (yy >= cy)] = I['HALO']
    rim = ring & ~ndimage.binary_erosion(ring); f[rim & (yy >= cy - 0.5)] = I['HALO_D']
    hole = (ei <= 1.0); f[hole & (f != 0)] = 0                    # see through the ring's middle
    f[(ndimage.binary_dilation(ring) & ~ring) & ~hole] = I['OUTL']
    if facing != 'up':
        sh = {'left': -1, 'right': 1}.get(facing, 0)
        for ex in (-4.5, -1.5, 1.5, 4.5):                              # the ring of eyes on its front arc
            x = int(round(HX + ex + sh)); y = int(round(cy + HRY * math.sqrt(max(0, 1 - ((x - HX) / HRX) ** 2)) - 0.8))
            f[y, x] = I['EYE']
        cx, cy2 = int(round(HX)), int(round(cy - 1))                  # the small cross floating in its middle
        for x, y in ((cx, cy2 - 2), (cx, cy2 - 1), (cx - 1, cy2 - 1), (cx + 1, cy2 - 1), (cx, cy2)): f[y, x] = I['CROSS']
        for x, y in ((cx, cy2 - 3), (cx - 1, cy2 - 2), (cx + 1, cy2 - 2), (cx - 2, cy2 - 1), (cx + 2, cy2 - 1), (cx - 1, cy2), (cx + 1, cy2)):
            if f[y, x] == 0: f[y, x] = I['CROSS_D']
    rx = 10.5 if step else 9.0                                      # ripples on the lake below it
    r = ((xx - HX) / rx) ** 2 + ((yy - 28.5) / 1.9) ** 2
    rip = (r <= 1.0) & (r > 0.5) & (f == 0)
    f[rip & (yy >= 28)] = I['RIP']; f[rip & (yy < 28)] = I['RIP_D']
    if facing == 'right': f = f[:, ::-1]
    return f
order = {0: ('up', 0), 5: ('up', 1), 6: ('down', 0), 7: ('down', 1), 2: ('left', 0), 1: ('left', 1), 3: ('right', 0), 4: ('right', 1)}
frames = [frame(order[k][1], order[k][0]) for k in range(8)]
pal = [(0, 0, 0)] + PALS[os.environ.get('SHINY', 'dark')] + [(0, 0, 0)] * (15 - len(NAMES))
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[183]
img, nf = btx.decode(d); assert nf == 8, nf
new = btx.encode(d, np.vstack(frames).astype(np.uint8), pal); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
P = np.array(pal, np.uint8); BG = np.array([72, 128, 200], np.uint8); orig = np.asarray(img)
seq = [6, 7, 0, 5, 2, 1, 3, 4]
top = np.hstack([np.where(orig[k * 32:(k + 1) * 32][..., 3:4] > 0, orig[k * 32:(k + 1) * 32][..., :3], BG) for k in seq])
bot = np.hstack([np.where(frames[k][..., None] > 0, P[frames[k]], BG) for k in seq])
z = np.vstack([top, np.full((3, top.shape[1], 3), 255, np.uint8), bot])
Image.fromarray(z).resize((z.shape[1] * 5, z.shape[0] * 5), Image.NEAREST).save(PREV); print('ok', OUT)
