"""Qwen-Image-Edit redraws a rough hop puppet (hop_pose.py) as one clean sprite in the approved front's design: the
ow_pose/qwen_clean.py recipe on a 96 grid (Lapper's front is 64x42 and the hop needs room). Two pictures on a dark page:
<image1> the puppet, <image2> the approved front. Qwen's figure is fitted onto the puppet's box and read cell by cell in
the front's palette. python qwen_clean_hop.py PUPPET.npy OUTDIR NAME SEED...   (env POSE: the pose in words)"""
import sys, os, time
import numpy as np
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy
from lapper_small2 import load_front, to_index
G = 96; C = 10                                   # 96 cells of 10 px (960), shown at 1024
PF, OD, NAME = sys.argv[1:4]; SEEDS = [int(s) for s in sys.argv[4:]] or [1, 2]; os.makedirs(OD, exist_ok=True)
fb = load_front(); des, palL = to_index(fb); PAL = np.array(palL[1:], float); NP = len(PAL)
pup = np.load(PF).astype(int)
PAGE = np.array([40, 44, 60.0])
def on96(idx):
    can = np.zeros((G, G), int); h, w = idx.shape; y0, x0 = (G - h) // 2, (G - w) // 2; can[y0:y0 + h, x0:x0 + w] = idx; return can
def canvas(idx, path):
    P = np.vstack([PAGE, PAL]); Image.fromarray(P[np.clip(idx, 0, NP)].astype(np.uint8)).resize((1024, 1024), Image.NEAREST).save(path); return path
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
CL = lab(np.vstack([PAGE, PAL]))
def fit(a, pup96):
    import cv2
    page = np.sqrt(((lab(a) - CL[0]) ** 2).sum(-1)) < 9
    n, lbl = cv2.connectedComponents(page.astype(np.uint8), connectivity=4)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    fig = ~(np.isin(lbl, list(border)) & page)
    ys, xs = np.nonzero(fig); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    py, px = np.nonzero(pup96 > 0); Y0, Y1, X0, X1 = py.min() * C, (py.max() + 1) * C, px.min() * C, (px.max() + 1) * C
    crop = Image.fromarray(np.where(fig[..., None], a, PAGE).astype(np.uint8)[y0:y1, x0:x1])
    out = np.zeros_like(a); out[...] = PAGE; out[Y0:Y1, X0:X1] = np.asarray(crop.resize((X1 - X0, Y1 - Y0), Image.NEAREST)).astype(float)
    print('fit: figure %dx%d -> %dx%d' % (x1 - x0, y1 - y0, X1 - X0, Y1 - Y0)); return out
def read(path, pup96):
    a = np.asarray(Image.open(path).convert('RGB').resize((G * C, G * C))).astype(float); a = fit(a, pup96)
    q = ((lab(a)[..., None, :] - CL[None, None]) ** 2).sum(-1).argmin(-1)
    cells = q.reshape(G, C, G, C).transpose(0, 2, 1, 3).reshape(G, G, C * C)
    out = np.zeros((G, G), int)
    for y in range(G):
        for x in range(G): out[y, x] = np.bincount(cells[y, x], minlength=NP + 1).argmax()
    return out
STYLE = ("an official Pokemon battle sprite from Pokemon Diamond, Pearl and HeartGold on the Nintendo DS: pixel art on a coarse "
         "grid of big square pixels, crisp squares, no anti-aliasing, no blur, no dithering, at most 15 colors, flat color areas "
         "with one shadow tone and small highlights, a one-pixel black outline")
PROMPT = ("<image1> is a rough cut-and-paste pose of the creature in <image2>, made by moving pieces of its sprite; the joins "
          "are broken and some pieces are turned. Redraw <image1> as one clean finished sprite, %s, exactly in the pose, size, "
          "place and outline of <image1>, on the same grid of big pixels. Use the creature's design, colors and pixel style from "
          "<image2>: a brown puppy with huge long fluffy ears, a white blaze on its head, a cream chest and cream paws, a pink "
          "tongue. Its eyes are always hidden under its fringe and ears: no eyes visible. The pose: %s Mend the joins so the body "
          "is whole and natural. Plain dark blue-grey background, nothing else.") % (STYLE, os.environ['POSE'])
p96 = on96(pup)
c1 = canvas(p96, os.path.join(OD, NAME + '_puppet_1024.png')); c2 = canvas(on96(des), os.path.join(OD, NAME + '_design_1024.png'))
for s in SEEDS:
    pic = os.path.join(OD, '%s_qwen_%d.png' % (NAME, s))
    for attempt in range(8):
        if os.path.exists(pic): break
        try: comfy.generate(PROMPT, pic, [c1, c2], seed=s, quiet=True)
        except Exception as e: print('ComfyUI away, waiting (%s)' % str(e)[:60], flush=True); time.sleep(60)
    if not os.path.exists(pic): continue
    r = read(pic, p96); np.save(os.path.join(OD, '%s_%d_idx.npy' % (NAME, s)), r.astype(np.uint8))
    P = np.vstack([PAGE, PAL]); Image.fromarray(P[r].astype(np.uint8)).resize((G * 6, G * 6), Image.NEAREST).save(os.path.join(OD, '%s_%d_6x.png' % (NAME, s)))
    print(NAME, s, flush=True)
